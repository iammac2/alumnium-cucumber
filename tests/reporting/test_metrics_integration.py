"""Tests for consuming Alumnium's `al.metrics`/artifacts contract (issue #8)."""

from types import SimpleNamespace

from alumnium.metrics import Artifact, SessionMetrics, StepMetrics, TokenUsage

from alumniumcucumber.reporting.models import (
    FeatureData,
    RunData,
    RunSummary,
    ScenarioData,
    StepData,
)
from alumniumcucumber.reporting.reporter import AlumniumReporter, _aggregate_tokens


def _step_metrics(kind="do", outcome="passed", tokens=None, artifacts=None):
    return StepMetrics(
        kind=kind,
        label="a step",
        outcome=outcome,
        started_at=1.0,
        finished_at=1.5,
        duration=0.5,
        tokens=tokens or TokenUsage(input_tokens=10, output_tokens=2, total_tokens=12),
        artifacts=artifacts or [],
    )


def _step_data(status="passed"):
    return StepData(
        keyword="When",
        text="do a thing",
        step_type="when",
        alumnium_type="do",
        status=status,
        duration=0.5,
        error_message=None,
        doc_string=None,
        data_table=None,
    )


def _scenario():
    return ScenarioData(
        id="ABCD1234",
        name="scenario",
        tags=[],
        status="running",
        duration=0.0,
        started_at="",
        steps=[],
        ai_analysis=None,
    )


def _reporter(tmp_path, **kwargs):
    return AlumniumReporter(output_dir=str(tmp_path), enable_ai=False, **kwargs)


def _context(metrics, artifacts_dir):
    al = SimpleNamespace(metrics=metrics, artifacts_dir=artifacts_dir)
    return SimpleNamespace(al=al)


def test_enrich_populates_tokens_duration_outcome_and_artifacts(tmp_path):
    reporter = _reporter(tmp_path, screenshot_mode="every_step")
    reporter._current_scenario = _scenario()

    shot = tmp_path / "src.png"
    shot.write_bytes(b"fake-png-bytes")
    ms = _step_metrics(artifacts=[Artifact(path=shot, kind="screenshot", mime="image/png")])
    ctx = _context(SessionMetrics(started_at=0, finished_at=2, duration=2, steps=[ms]), tmp_path)

    step_data = _step_data()
    reporter._current_scenario.steps.append(step_data)
    reporter._enrich_from_metrics(ctx, step_data)

    assert step_data.tokens["input_tokens"] == 10
    assert step_data.tokens["total_tokens"] == 12
    assert step_data.alumnium_duration == 0.5
    assert step_data.alumnium_outcome == "passed"
    assert step_data.artifacts == [{"path": str(shot), "kind": "screenshot", "mime": "image/png"}]
    # Screenshot copied into the report dir with the conventional name.
    assert step_data.screenshot_path == "screenshots/ABCD1234_step1.png"
    assert (reporter._screenshots_dir / "ABCD1234_step1.png").exists()


def test_screenshot_mode_on_failure_skips_passed_step(tmp_path):
    reporter = _reporter(tmp_path, screenshot_mode="on_failure")
    reporter._current_scenario = _scenario()

    shot = tmp_path / "src.png"
    shot.write_bytes(b"fake-png-bytes")
    ms = _step_metrics(artifacts=[Artifact(path=shot, kind="screenshot", mime="image/png")])
    ctx = _context(SessionMetrics(started_at=0, finished_at=2, duration=2, steps=[ms]), tmp_path)

    step_data = _step_data(status="passed")
    reporter._current_scenario.steps.append(step_data)
    reporter._enrich_from_metrics(ctx, step_data)

    # Metadata still attached, but no screenshot copied for a passed step.
    assert step_data.alumnium_outcome == "passed"
    assert step_data.screenshot_path is None


def test_positional_correlation_skips_non_dispatching_step(tmp_path):
    reporter = _reporter(tmp_path)
    reporter._current_scenario = _scenario()

    metrics = SessionMetrics(started_at=0, finished_at=2, duration=2, steps=[_step_metrics()])
    ctx = _context(metrics, tmp_path)

    # First step dispatched to Alumnium -> consumes the single metrics entry.
    s1 = _step_data()
    reporter._current_scenario.steps.append(s1)
    reporter._enrich_from_metrics(ctx, s1)
    assert s1.alumnium_outcome == "passed"
    assert reporter._consumed == 1

    # Second step did not dispatch (metrics unchanged) -> no misalignment, no data attached.
    s2 = _step_data()
    reporter._current_scenario.steps.append(s2)
    reporter._enrich_from_metrics(ctx, s2)
    assert s2.tokens is None
    assert reporter._consumed == 1


def test_enrich_degrades_gracefully_without_metrics(tmp_path):
    reporter = _reporter(tmp_path)
    reporter._current_scenario = _scenario()
    step_data = _step_data()
    reporter._current_scenario.steps.append(step_data)

    # al present but without a metrics property (older Alumnium).
    reporter._enrich_from_metrics(SimpleNamespace(al=object()), step_data)
    assert step_data.tokens is None
    # No al on the context at all.
    reporter._enrich_from_metrics(SimpleNamespace(), step_data)
    assert step_data.tokens is None


def test_aggregate_tokens_sums_across_steps_or_none():
    def run_with(step_tokens_list):
        steps = []
        for tokens in step_tokens_list:
            step = _step_data()
            step.tokens = tokens
            steps.append(step)
        scenario = _scenario()
        scenario.steps = steps
        return RunData(
            run_id="R",
            title="t",
            started_at="",
            finished_at="",
            alumnium_model="ollama/x",
            summary=RunSummary(0, 0, 0, 0, 0, 0.0, 0.0),
            features=[FeatureData(name="f", file="f.feature", description="", tags=[], scenarios=[scenario])],
            narrative=None,
        )

    aggregated = _aggregate_tokens(
        run_with([{"input_tokens": 5, "total_tokens": 5}, {"input_tokens": 3, "total_tokens": 4}])
    )
    assert aggregated["input_tokens"] == 8
    assert aggregated["total_tokens"] == 9

    assert _aggregate_tokens(run_with([None, None])) is None
