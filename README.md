# alumnium-cucumber

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Behave](https://img.shields.io/badge/Behave-Latest-green.svg)](https://behave.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/iammac2/alumnium-cucumber/pulls)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-report-blue.svg)](https://iammac2.github.io/alumnium-cucumber/report.html)

**[View latest CI run report →](https://iammac2.github.io/alumnium-cucumber/report.html)**

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
`environment.py` and step dispatcher — everything is already set up, including the
reporter. An HTML report opens automatically in your browser after each run.

```bash
# Dry-run — step matching only, no browser or LLM
behave examples/ --dry-run

# Single feature file
behave examples/saucedemo.feature --no-capture

# Watch the browser live
HEADLESS=false behave examples/saucedemo.feature --no-capture

# Scenarios matching a name pattern
behave examples/ --name "Standard user" --no-capture
```

### Option B: Use in your own project

1. Install the package (see [Installation](#installation) above)
2. Copy `examples/environment.py` into your project as `features/environment.py`.
   The reporter is pre-configured — edit the three variables at the top of the file
   to set your output directory, report title, and screenshot mode.
3. Copy `examples/steps/alumnium_steps.py` into your project as `features/steps/alumnium_steps.py`
4. Write your `.feature` files in `features/`
5. Run:

```bash
behave features/ --no-capture

# Watch the browser live
HEADLESS=false behave features/ --no-capture
```

No further step definitions are needed — the adapter forwards every step to the LLM.

---

## Reporting

After each run `AlumniumReporter` generates a self-contained HTML report and a JSON
data file, written to a per-run subfolder of your output directory. The HTML report
opens automatically in your browser. When AI is enabled it also provides per-failure
root-cause analysis and a plain-English stakeholder narrative summarising the run.

### Configuration

```python
from alumniumcucumber.reporting import AlumniumReporter

_reporter = AlumniumReporter(
    output_dir="reports",          # parent folder — each run creates run_{ID}/ inside
    enable_ai=True,                # False to skip all LLM calls in reports
    report_title="My App Tests",   # shown in the report header
    screenshot_mode="on_failure",  # "on_failure" | "every_step" | "off"
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `output_dir` | `str` | `"reports"` | Parent directory. Each run creates a `run_{ID}/` subfolder. |
| `enable_ai` | `bool` | `True` | Master AI switch. When `False`, skips failure analysis and narrative. |
| `report_title` | `str` | `"Alumnium Test Report"` | Title shown in the HTML report header. |
| `screenshot_mode` | `str` | `"on_failure"` | `"on_failure"` captures only failed steps · `"every_step"` captures all steps · `"off"` disables screenshots. |

### Wiring into `environment.py`

```python
from alumniumcucumber.reporting import AlumniumReporter

_reporter = AlumniumReporter(output_dir="reports", enable_ai=True)

def before_feature(context, feature):
    _reporter.before_feature(context, feature)

def after_feature(context, feature):
    _reporter.after_feature(context, feature)

def before_scenario(context, scenario):
    _reporter.before_scenario(context, scenario)
    # ... create page, al, adapter ...
    _reporter.set_model_identity(context.al)   # enriches model name in the report

def after_scenario(context, scenario):
    _reporter.after_scenario(context, scenario)

def before_step(context, step):
    _reporter.before_step(context, step)

def after_step(context, step):
    _reporter.after_step(context, step)
    # Attach a screenshot for this step (respects screenshot_mode)
    if hasattr(context, "page"):
        try:
            _reporter.attach_screenshot(context.page.screenshot())
        except Exception:
            pass

def after_all(context):
    # ... close browser ...
    _reporter.generate_report()   # writes the HTML + JSON and opens the browser
```

See `examples/environment.py` for the complete, ready-to-copy version.

### Output layout

```
reports/
└── run_A1B2C3D4/
    ├── report.html      ← interactive HTML report (opens automatically)
    ├── report.json      ← raw run data
    └── screenshots/     ← PNG evidence files (when screenshot_mode ≠ "off")
```

### Regenerating the HTML from JSON

If you need to re-render the HTML from a saved JSON file (e.g. after a template update):

```bash
alumnium-report reports/run_A1B2C3D4/report.json
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

### `AlumniumReporter`

Collects behave lifecycle events and generates the HTML/JSON report.

```python
from alumniumcucumber.reporting import AlumniumReporter

reporter = AlumniumReporter(
    output_dir="reports",
    enable_ai=True,
    report_title="My App Tests",
    screenshot_mode="on_failure",
)
```

| Method | When to call | Description |
|---|---|---|
| `before_feature(context, feature)` | `before_feature` hook | Starts feature timing |
| `after_feature(context, feature)` | `after_feature` hook | Closes feature timing |
| `before_scenario(context, scenario)` | `before_scenario` hook | Starts scenario timing |
| `after_scenario(context, scenario)` | `after_scenario` hook | Closes scenario, triggers AI analysis on failure |
| `before_step(context, step)` | `before_step` hook | Starts step timing |
| `after_step(context, step)` | `after_step` hook | Records step result |
| `set_model_identity(al)` | after `Alumni` is created | Enriches the model name shown in the report |
| `attach_screenshot(png_bytes)` | `after_step` hook | Saves a PNG screenshot for the current step (respects `screenshot_mode`) |
| `generate_report()` | `after_all` hook | Writes `report.html` + `report.json`, opens the browser |

---

## Contributor

[neuno.ai](https://neuno.ai)
