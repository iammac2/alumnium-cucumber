"""Behave lifecycle hooks for the alumniumcucumber examples.

Set ALUMNIUM_MODEL before running:
    export ALUMNIUM_MODEL=ollama/mistral-small3.1:24b   # local Ollama
    export ALUMNIUM_MODEL=openai/gpt-4o                 # OpenAI
    export ALUMNIUM_MODEL=anthropic/claude-3-5-sonnet-20241022  # Anthropic

Run the examples:
    ALUMNIUM_MODEL=ollama/mistral-small3.1:24b \\
        behave examples/ --no-capture
"""

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
        context.al,
        include_doc_string=True,
        include_data_table=True,
    )


def after_scenario(context, scenario):
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


def after_all(context):
    context._browser.close()
    context._pw.stop()
