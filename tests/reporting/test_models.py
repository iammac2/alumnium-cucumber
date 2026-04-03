"""Tests for alumniumcucumber.reporting.models."""

import dataclasses
import pytest

from alumniumcucumber.reporting.models import (
    AiAnalysis,
    FeatureData,
    Narrative,
    RunData,
    RunSummary,
    ScenarioData,
    StepData,
)
from alumniumcucumber.reporting.reporter import _derive_alumnium_type


class TestStepData:
    def test_basic_instantiation(self):
        step = StepData(
            keyword="Given",
            text="I am on the homepage",
            step_type="given",
            alumnium_type="do",
            status="passed",
            duration=0.123,
            error_message=None,
            doc_string=None,
            data_table=None,
        )
        assert step.keyword == "Given"
        assert step.text == "I am on the homepage"
        assert step.alumnium_type == "do"
        assert step.status == "passed"
        assert step.duration == 0.123

    def test_with_error_message(self):
        step = StepData(
            keyword="Then",
            text="the page shows success",
            step_type="then",
            alumnium_type="check",
            status="failed",
            duration=2.5,
            error_message="AssertionError: page did not show success",
            doc_string=None,
            data_table=None,
        )
        assert step.status == "failed"
        assert step.error_message == "AssertionError: page did not show success"

    def test_with_doc_string(self):
        step = StepData(
            keyword="Given",
            text="the following document",
            step_type="given",
            alumnium_type="do",
            status="passed",
            duration=0.5,
            error_message=None,
            doc_string="line1\nline2",
            data_table=None,
        )
        assert step.doc_string == "line1\nline2"

    def test_with_data_table(self):
        step = StepData(
            keyword="Given",
            text="the following users",
            step_type="given",
            alumnium_type="do",
            status="passed",
            duration=0.1,
            error_message=None,
            doc_string=None,
            data_table=[["name", "email"], ["Alice", "alice@example.com"]],
        )
        assert step.data_table[0] == ["name", "email"]
        assert step.data_table[1][0] == "Alice"

    def test_json_serialisable(self):
        step = StepData(
            keyword="When",
            text="I click submit",
            step_type="when",
            alumnium_type="do",
            status="passed",
            duration=0.8,
            error_message=None,
            doc_string=None,
            data_table=None,
        )
        d = dataclasses.asdict(step)
        assert d["keyword"] == "When"
        assert d["alumnium_type"] == "do"


class TestAlumniumTypeDerivation:
    """Test alumnium_type derivation from step_type."""

    def test_given_maps_to_do(self):
        assert _derive_alumnium_type("given", None) == "do"

    def test_when_maps_to_do(self):
        assert _derive_alumnium_type("when", None) == "do"

    def test_then_maps_to_check(self):
        assert _derive_alumnium_type("then", None) == "check"

    def test_step_inherits_do_from_given(self):
        assert _derive_alumnium_type("step", "given") == "do"

    def test_step_inherits_do_from_when(self):
        assert _derive_alumnium_type("step", "when") == "do"

    def test_step_inherits_check_from_then(self):
        assert _derive_alumnium_type("step", "then") == "check"

    def test_step_defaults_to_do_when_no_prev(self):
        assert _derive_alumnium_type("step", None) == "do"


class TestRunSummaryPassRate:
    def test_pass_rate_100(self):
        s = RunSummary(
            total_features=1,
            total_scenarios=5,
            passed=5,
            failed=0,
            skipped=0,
            total_duration=10.0,
            pass_rate=100.0,
        )
        assert s.pass_rate == 100.0

    def test_pass_rate_0(self):
        s = RunSummary(
            total_features=1,
            total_scenarios=3,
            passed=0,
            failed=3,
            skipped=0,
            total_duration=5.0,
            pass_rate=0.0,
        )
        assert s.pass_rate == 0.0

    def test_pass_rate_50(self):
        s = RunSummary(
            total_features=1,
            total_scenarios=4,
            passed=2,
            failed=2,
            skipped=0,
            total_duration=8.0,
            pass_rate=50.0,
        )
        assert s.pass_rate == 50.0

    def test_pass_rate_fractional(self):
        # 1 of 3 = 33.3%
        s = RunSummary(
            total_features=1,
            total_scenarios=3,
            passed=1,
            failed=2,
            skipped=0,
            total_duration=6.0,
            pass_rate=round(1 / 3 * 100, 1),
        )
        assert s.pass_rate == pytest.approx(33.3, abs=0.1)


class TestScenarioData:
    def test_basic(self):
        sc = ScenarioData(
            id="ABCD1234",
            name="Login as admin",
            tags=["@auth"],
            status="passed",
            duration=3.14,
            started_at="2026-04-02T12:00:00+00:00",
            steps=[],
            ai_analysis=None,
        )
        assert sc.id == "ABCD1234"
        assert sc.tags == ["@auth"]
        assert sc.ai_analysis is None

    def test_json_serialisable(self):
        sc = ScenarioData(
            id="ABCD1234",
            name="Test",
            tags=[],
            status="passed",
            duration=1.0,
            started_at="2026-04-02T12:00:00+00:00",
            steps=[],
            ai_analysis=None,
        )
        d = dataclasses.asdict(sc)
        assert "id" in d
        assert d["ai_analysis"] is None


class TestRunData:
    def test_basic(self):
        summary = RunSummary(1, 2, 1, 1, 0, 5.0, 50.0)
        rd = RunData(
            run_id="ABCD1234",
            title="My Tests",
            started_at="2026-04-02T12:00:00+00:00",
            finished_at="2026-04-02T12:01:00+00:00",
            alumnium_model="anthropic",
            summary=summary,
            features=[],
            narrative=None,
        )
        assert rd.run_id == "ABCD1234"
        assert rd.narrative is None

    def test_json_serialisable(self):
        summary = RunSummary(1, 1, 1, 0, 0, 1.0, 100.0)
        rd = RunData(
            run_id="ABCD1234",
            title="My Tests",
            started_at="2026-04-02T12:00:00+00:00",
            finished_at="2026-04-02T12:01:00+00:00",
            alumnium_model="anthropic",
            summary=summary,
            features=[],
            narrative=None,
        )
        d = dataclasses.asdict(rd)
        assert "run_id" in d
        assert "summary" in d
        assert "features" in d
