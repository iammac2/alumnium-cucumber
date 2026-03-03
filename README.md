# alumnium-cucumber

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Behave](https://img.shields.io/badge/Behave-Latest-green.svg)](https://behave.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/iammac2/alumnium-cucumber/pulls)

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

## Prerequisites

- **[Alumnium](https://github.com/alumnium-hq/alumnium)** — the core AI browser automation framework. See the [installation guide](https://alumnium.ai/docs/getting-started/installation/) for system requirements. Installed automatically as a dependency of this package.
- **Python 3.10+**
- **A supported LLM provider** — see [Alumnium configuration](https://alumnium.ai/docs/getting-started/configuration/) for the full list and required API keys:
  - **Ollama** (local, free): install from [ollama.ai](https://ollama.ai), then `ollama pull mistral-small3.1`
  - **OpenAI**: set `OPENAI_API_KEY`
  - **Anthropic**: set `ANTHROPIC_API_KEY`
  - Other providers: Google, MistralAI, DeepSeek, AWS, xAI — see [Alumnium docs](https://alumnium.ai/docs/getting-started/configuration/)

---

## Installation

> **PyPI coming soon** — install directly from GitHub in the meantime:

```bash
python -m venv .venv && source .venv/bin/activate   # recommended
pip install git+https://github.com/iammac2/alumnium-cucumber.git
playwright install chromium
```

Configure your AI model via the `ALUMNIUM_MODEL` environment variable:

```bash
export ALUMNIUM_MODEL=ollama       # local Ollama (uses default model)
export ALUMNIUM_MODEL=openai       # OpenAI (uses default model)
export ALUMNIUM_MODEL=anthropic    # Anthropic (uses default model)
```

See [Alumnium configuration](https://alumnium.ai/docs/getting-started/configuration/) for the full list of providers and how to select a specific model.

---

## Quick start

### Option A: Run the included examples

The fastest way to see it working — no files to create:

```bash
git clone https://github.com/iammac2/alumnium-cucumber
cd alumnium-cucumber
python -m venv .venv && source .venv/bin/activate
pip install .
playwright install chromium
export ALUMNIUM_MODEL=ollama   # or openai / anthropic etc.
behave examples/ --no-capture
```

The `examples/` directory contains ready-to-run feature files with a pre-configured
`environment.py` and step dispatcher — everything is already set up.

```bash
# Dry-run — step matching only, no browser or LLM
behave examples/ --dry-run

# Single feature file
behave examples/saucedemo.feature --no-capture

# Scenarios matching a name pattern
behave examples/ --name "Standard user" --no-capture
```

### Option B: Use in your own project

1. Install the package (see [Installation](#installation) above)
2. Copy `examples/environment.py` into your project as `features/environment.py`
3. Copy `examples/steps/alumnium_steps.py` into your project as `features/steps/alumnium_steps.py`
4. Write your `.feature` files in `features/`
5. Run:

```bash
behave features/ --no-capture
```

No further step definitions are needed — the adapter forwards every step to the LLM.

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
