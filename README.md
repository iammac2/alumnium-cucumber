# alumnium-cucumber

A [behave](https://behave.readthedocs.io/) integration that lets you write plain-English Gherkin feature files and drive [Alumnium](https://github.com/alumnium-hq/alumnium) with **no hand-coded step definitions per scenario**.

Step text is forwarded verbatim to the LLM. The model interprets the instruction, plans browser actions, and executes them — or asserts the stated condition is true. You write the feature file; the model drives the browser.

---

## How it works

```
Feature file → behave → AlumniumGherkinAdapter → Alumni.do() / Alumni.check()
                                                        ↓
                                               LLM (Planner + Actor)
                                                        ↓
                                               Playwright / Chromium
```

### Keyword routing

| Keyword | Alumnium call | Notes |
|---|---|---|
| `Given` | `al.do(text)` | Setup / precondition |
| `When` | `al.do(text)` | User action |
| `Then` | `al.check(text)` | Assertion — raises `AssertionError` on failure |
| `And` / `But` | inherits previous | Same role as the preceding primary keyword |
| `*` | inherits previous | Bullet-point alternative to `And`/`But` |

### Navigation

Navigation is handled by the LLM via `NavigateToUrlTool`, enabled through
`Alumni(page, extra_tools=[NavigateToUrlTool])` in `environment.py`. Use a
standard Given step — no special step definition required:

```gherkin
Given navigate to "https://example.com"
```

---

## Installation

```bash
pip install alumniumcucumber
playwright install chromium
```

Configure your AI model via the `ALUMNIUM_MODEL` environment variable
(see [Alumnium configuration](https://alumnium.ai/docs/getting-started/configuration/)):

```bash
export ALUMNIUM_MODEL=ollama/mistral-small3.1:24b   # local Ollama
export ALUMNIUM_MODEL=openai/gpt-4o                 # OpenAI
export ALUMNIUM_MODEL=anthropic/claude-3-5-sonnet-20241022  # Anthropic
```

---

## Quick start

1. Create `features/environment.py`:

```python
from alumniumcucumber import AlumniumGherkinAdapter
from playwright.sync_api import sync_playwright
from alumnium import Alumni
from alumnium.tools import NavigateToUrlTool

def before_all(context):
    context._pw = sync_playwright().start()
    context._browser = context._pw.chromium.launch(headless=True)

def before_scenario(context, scenario):
    page = context._browser.new_page()
    context.al = Alumni(page, extra_tools=[NavigateToUrlTool])
    context.adapter = AlumniumGherkinAdapter(
        context.al, include_doc_string=True, include_data_table=True,
    )

def after_scenario(context, scenario):
    context.al.quit()

def after_all(context):
    context._browser.close()
    context._pw.stop()
```

2. Create `features/steps/alumnium_steps.py`:

```python
from alumniumcucumber import GherkinStep
from behave import given, step, then, use_step_matcher, when

use_step_matcher("re")
_MATCH_ALL = r"(?P<text>.+)"

def _step_args(context):
    doc_string = context.text
    data_table = [[str(cell) for cell in row] for row in context.table] if context.table else None
    return doc_string, data_table

@given(_MATCH_ALL)
def step_given(context, text):
    doc, table = _step_args(context)
    context.adapter.dispatch(GherkinStep("Given", text, doc_string=doc, data_table=table))

@when(_MATCH_ALL)
def step_when(context, text):
    doc, table = _step_args(context)
    context.adapter.dispatch(GherkinStep("When", text, doc_string=doc, data_table=table))

@then(_MATCH_ALL)
def step_then(context, text):
    doc, table = _step_args(context)
    context.adapter.dispatch(GherkinStep("Then", text, doc_string=doc, data_table=table))

@step(_MATCH_ALL)
def step_star(context, text):
    doc, table = _step_args(context)
    context.adapter.dispatch(GherkinStep("*", text, doc_string=doc, data_table=table))
```

3. Write your feature files and run:

```bash
behave features/ --no-capture
```

---

## Running the included examples

```bash
git clone https://github.com/iammac2/alumnium-cucumber
cd alumnium-cucumber
pip install -e .

# With a local Ollama model
ALUMNIUM_MODEL=ollama/mistral-small3.1:24b behave examples/ --no-capture

# With OpenAI
ALUMNIUM_MODEL=openai/gpt-4o behave examples/ --no-capture

# With Anthropic
ALUMNIUM_MODEL=anthropic/claude-3-5-sonnet-20241022 behave examples/ --no-capture

# Dry-run — step matching only, no browser or LLM
behave examples/ --dry-run

# Single feature file
ALUMNIUM_MODEL=ollama/mistral-small3.1:24b behave examples/saucedemo.feature --no-capture

# Scenarios matching a name pattern
ALUMNIUM_MODEL=ollama/mistral-small3.1:24b behave examples/ --name "Standard user"
```

---

## Writing feature files

Place `.feature` files in your `features/` directory. All Gherkin constructs are supported.

### Basic scenario

```gherkin
Feature: SauceDemo login

  Scenario: Standard user can log in and see inventory
    Given navigate to "https://www.saucedemo.com"
    When type "standard_user" into the username field
    And type "secret_sauce" into the password field
    And click the login button
    Then the page shows an inventory of products
```

Write step text as you would describe the action to a human. No regex, no glue code, no per-scenario step definition files to maintain.

### Doc Strings

Attach a triple-quoted block to give the LLM richer context:

```gherkin
Then the page shows a product catalogue
  """
  Expect at least 6 products, each with a name, price, and Add to cart button.
  """
```

### Data Tables

Attach a pipe-delimited table to supply structured input:

```gherkin
When fill in the login form with:
  | field    | value         |
  | username | standard_user |
  | password | secret_sauce  |
```

### Scenario Outline

Behave substitutes `<placeholder>` values before step functions are called — no adapter changes needed:

```gherkin
Scenario Outline: Multiple user types can log in
  Given navigate to "https://www.saucedemo.com"
  When type "<username>" into the username field
  And type "secret_sauce" into the password field
  And click the login button
  Then the page shows an inventory of products

  Examples: valid users
    | username      |
    | standard_user |
    | problem_user  |
```

### Background

`Background:` steps are transparently prepended to each scenario by behave — no special handling required:

```gherkin
Feature: Shopping cart

  Background:
    Given navigate to "https://www.saucedemo.com"
    When type "standard_user" into the username field
    And type "secret_sauce" into the password field
    And click the login button

  Scenario: Can add an item to the cart
    When click Add to cart on the first product
    Then the cart badge shows 1 item
```

---

## API reference

### `GherkinStep`

Immutable dataclass carrying step data:

| Field | Type | Purpose |
|---|---|---|
| `keyword` | `str` | `Given` / `When` / `Then` / `And` / `But` / `*` |
| `text` | `str` | Step text after the keyword |
| `doc_string` | `str \| None` | Triple-quoted block content |
| `data_table` | `Sequence[Sequence[str]] \| None` | Table rows as list-of-lists |
| `location` | `str \| None` | `"file:line"` for diagnostics |

### `AlumniumGherkinAdapter`

Routes steps to `Alumni`:

```python
from alumniumcucumber import AlumniumGherkinAdapter, GherkinStep

adapter = AlumniumGherkinAdapter(
    al,
    include_doc_string=True,   # append doc string to LLM payload when present
    include_data_table=True,   # append table to LLM payload when present
)
adapter.dispatch(step)
```

---

## Contributor

[neuno.ai](https://neuno.ai)
