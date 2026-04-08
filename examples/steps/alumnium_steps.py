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


@when(r"wait (?P<seconds>\d+(?:\.\d+)?) seconds?")
def step_wait(context, seconds):
    """Pause execution for a defined number of seconds. Thread-safe via time.sleep."""
    import time
    time.sleep(float(seconds))


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
