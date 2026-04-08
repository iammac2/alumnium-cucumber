from alumniumcucumber import GherkinStep
from behave import given, step, then, use_step_matcher, when

use_step_matcher("re")

_MATCH_ALL = r"(?P<text>.+)"


def _step_args(context):
    """Extract doc string and data table from the current behave step context."""
    doc_string = context.text
    data_table = [[str(cell) for cell in row] for row in context.table] if context.table else None
    return doc_string, data_table


@given(_MATCH_ALL)
def step_given(context, text):
    doc, table = _step_args(context)
    context.adapter.dispatch(GherkinStep("Given", text, doc_string=doc, data_table=table))


@when(r"the page finishes loading")
def step_wait_for_load(context):
    """Wait for navigation to the inventory page — bypasses Alumnium, handles slow pages."""
    context.page.wait_for_selector(".inventory_list", timeout=30_000)


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
    """Catch-all for the * (asterisk) keyword — inherits the preceding primary keyword."""
    doc, table = _step_args(context)
    context.adapter.dispatch(GherkinStep("*", text, doc_string=doc, data_table=table))
