"""
features/environment.py
-----------------------
Copy to features/environment.py in your project.
Configure the three variables marked CONFIGURE below.

Set ALUMNIUM_MODEL before running:
    export ALUMNIUM_MODEL=ollama/mistral-small3.1:24b   # local Ollama
    export ALUMNIUM_MODEL=openai/gpt-4o                 # OpenAI
    export ALUMNIUM_MODEL=anthropic/claude-3-5-sonnet-20241022  # Anthropic

Run the examples:
    ALUMNIUM_MODEL=ollama/mistral-small3.1:24b \\
        behave examples/ --no-capture
"""

import os

from alumniumcucumber import AlumniumGherkinAdapter
from alumniumcucumber.reporting import AlumniumReporter
from playwright.sync_api import sync_playwright

from alumnium import Alumni
from alumnium.tools import NavigateToUrlTool

# ── CONFIGURE ──────────────────────────────────────────────
_reporter = AlumniumReporter(
    output_dir="reports",               # Where to write run folders
    enable_ai=True,                     # False to skip all LLM calls in reports
    report_title="My App Tests",        # Shown in the report header
    screenshot_mode="every_step",        # "on_failure" | "every_step" | "off"
)
# ───────────────────────────────────────────────────────────


def before_all(context):
    context._pw = sync_playwright().start()
    headless = os.environ.get("HEADLESS", "true").lower() != "false"
    context._browser = context._pw.chromium.launch(headless=headless)


def after_all(context):
    context._browser.close()
    context._pw.stop()
    _reporter.generate_report()  # Writes reports/report_XXXXXXXX.html + .json


def before_feature(context, feature):
    _reporter.before_feature(context, feature)


def after_feature(context, feature):
    _reporter.after_feature(context, feature)


def before_scenario(context, scenario):
    _reporter.before_scenario(context, scenario)
    context.page = context._browser.new_page()
    context.al = Alumni(context.page, extra_tools=[NavigateToUrlTool])
    _reporter.set_model_identity(context.al)
    context.adapter = AlumniumGherkinAdapter(
        context.al,
        include_doc_string=True,
        include_data_table=True,
    )


def after_scenario(context, scenario):
    _reporter.after_scenario(context, scenario)
    if scenario.status == "passed":
        try:
            context.al.cache.save()
        except FileNotFoundError:
            # filelock removes the lockfile on release; the manual unlink in
            # FilesystemCache.save() may then raise FileNotFoundError on some
            # platforms. The cache data (response.json) is written correctly
            # before this point, so the error is safe to suppress.
            pass
    else:
        context.al.cache.discard()

    print(f"\n[stats] {context.al.stats}")
    context.al.quit()


def before_step(context, step):
    _reporter.before_step(context, step)


def after_step(context, step):
    _reporter.after_step(context, step)
    # Screenshot evidence — Playwright
    if hasattr(context, "page"):
        try:
            _reporter.attach_screenshot(context.page.screenshot())
        except Exception:  # noqa: BLE001
            pass  # never let screenshot failure affect the test result
    # For Selenium: context.driver.get_screenshot_as_png()
