"""Tests for alumniumcucumber.reporting.generator."""

import json
from pathlib import Path

import pytest

from alumniumcucumber.reporting.cli import _dict_to_run_data
from alumniumcucumber.reporting.generator import ReportGenerator, generate_html, generate_json
from alumniumcucumber.reporting.models import (
    AiAnalysis,
    FeatureData,
    Narrative,
    RunData,
    RunSummary,
    ScenarioData,
    StepData,
)

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_step(
    keyword="Given",
    text="navigate",
    step_type="given",
    alumnium_type="do",
    status="passed",
    duration=1.0,
):
    return StepData(
        keyword=keyword,
        text=text,
        step_type=step_type,
        alumnium_type=alumnium_type,
        status=status,
        duration=duration,
        error_message=None,
        doc_string=None,
        data_table=None,
    )


def _make_scenario(name="Test scenario", status="passed", steps=None, ai_analysis=None, sc_id="ABCD1234"):
    return ScenarioData(
        id=sc_id,
        name=name,
        tags=[],
        status=status,
        duration=sum(s.duration for s in (steps or [])),
        started_at="2026-04-02T12:00:00+00:00",
        steps=steps or [_make_step()],
        ai_analysis=ai_analysis,
    )


def _make_run_data(features=None, narrative=None):
    feats = features or []
    total = sum(len(f.scenarios) for f in feats)
    passed = sum(1 for f in feats for s in f.scenarios if s.status == "passed")
    failed = sum(1 for f in feats for s in f.scenarios if s.status == "failed")
    skipped = total - passed - failed
    summary = RunSummary(
        total_features=len(feats),
        total_scenarios=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        total_duration=10.0,
        pass_rate=round(passed / total * 100, 1) if total else 0.0,
    )
    return RunData(
        run_id="ABCD1234",
        title="Test Report",
        started_at="2026-04-02T12:00:00+00:00",
        finished_at="2026-04-02T12:01:00+00:00",
        alumnium_model="anthropic",
        summary=summary,
        features=feats,
        narrative=narrative,
    )


class TestGenerateJson:
    def test_returns_valid_json(self):
        run = _make_run_data()
        result = generate_json(run)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_contains_all_run_data_keys(self):
        run = _make_run_data()
        parsed = json.loads(generate_json(run))
        assert "run_id" in parsed
        assert "title" in parsed
        assert "started_at" in parsed
        assert "finished_at" in parsed
        assert "alumnium_model" in parsed
        assert "summary" in parsed
        assert "features" in parsed
        assert "narrative" in parsed

    def test_features_serialised(self):
        feat = FeatureData(
            name="My Feature", file="f.feature", description="desc",
            tags=[], scenarios=[_make_scenario()],
        )
        run = _make_run_data(features=[feat])
        parsed = json.loads(generate_json(run))
        assert len(parsed["features"]) == 1
        assert parsed["features"][0]["name"] == "My Feature"


class TestGenerateHtml:
    def test_starts_with_doctype(self):
        run = _make_run_data()
        html = generate_html(run)
        assert html.startswith("<!DOCTYPE html>")

    def test_contains_report_data_variable(self):
        run = _make_run_data()
        html = generate_html(run)
        assert "const REPORT_DATA" in html

    def test_scenario_ids_appear_in_html(self):
        """Scenario IDs are embedded in REPORT_DATA JSON and used by JS to render id="sc-..."."""
        sc = _make_scenario(sc_id="TESTID01")
        feat = FeatureData(name="F", file="f.feature", description="", tags=[], scenarios=[sc])
        run = _make_run_data(features=[feat])
        html = generate_html(run)
        # The scenario ID is embedded in the JSON data and used by the JS template
        assert "TESTID01" in html
        # The JS template renders sc-{id} elements — check the template code is present
        assert '"sc-"' in html or "sc-" in html

    def test_dark_and_light_theme_tokens(self):
        run = _make_run_data()
        html = generate_html(run)
        assert 'data-theme="dark"' in html
        assert 'data-theme="light"' in html

    def test_chat_panel_present(self):
        run = _make_run_data()
        html = generate_html(run)
        # API key input area
        assert "chat-api-key-input" in html
        # Messages area
        assert "messagesArea" in html

    def test_narrative_panel_present(self):
        run = _make_run_data()
        html = generate_html(run)
        assert "narrativePanel" in html

    def test_feature_summary_table_present(self):
        run = _make_run_data()
        html = generate_html(run)
        assert "featureTableContainer" in html

    def test_empty_run_generates_without_error(self):
        run = _make_run_data(features=[])
        html = generate_html(run)
        assert html.startswith("<!DOCTYPE html>")
        assert len(html) > 1000

    def test_run_with_ai_analysis_generates_without_error(self):
        ai = AiAnalysis(
            summary="Login failed",
            root_cause="Session cookie missing",
            suggestion="Clear session before test",
            severity="high",
            provider="anthropic",
            error=None,
        )
        sc = _make_scenario(
            status="failed",
            ai_analysis=ai,
            steps=[_make_step(keyword="Then", step_type="then", alumnium_type="check", status="failed")],
        )
        feat = FeatureData(name="Auth", file="auth.feature", description="", tags=[], scenarios=[sc])
        run = _make_run_data(features=[feat])
        html = generate_html(run)
        assert "AI Failure Analysis" in html

    def test_run_with_narrative_none_generates_without_error(self):
        run = _make_run_data(narrative=None)
        html = generate_html(run)
        assert html.startswith("<!DOCTYPE html>")

    def test_run_with_narrative_generates_without_error(self):
        narrative = Narrative(
            headline="5 of 8 passed",
            body="Most tests passed.\n\nTwo failures noted.",
            risk_level="amber",
            provider="anthropic",
            error=None,
        )
        run = _make_run_data(narrative=narrative)
        html = generate_html(run)
        assert "5 of 8 passed" in html


class TestReportGeneratorWrite:
    def test_writes_html_and_json_files(self, tmp_path):
        run = _make_run_data()
        gen = ReportGenerator(tmp_path)
        run_dir, html_path, json_path = gen.write(run)
        assert html_path.exists()
        assert json_path.exists()
        assert html_path.suffix == ".html"
        assert json_path.suffix == ".json"

    def test_creates_output_dir_if_missing(self, tmp_path):
        outdir = tmp_path / "nested" / "reports"
        run = _make_run_data()
        gen = ReportGenerator(outdir)
        run_dir, html_path, json_path = gen.write(run)
        assert html_path.exists()

    def test_run_id_in_run_dir_name(self, tmp_path):
        run = _make_run_data()
        gen = ReportGenerator(tmp_path)
        run_dir, html_path, json_path = gen.write(run)
        assert "ABCD1234" in run_dir.name
        assert html_path.name == "report.html"
        assert json_path.name == "report.json"
        assert html_path.parent == run_dir
        assert json_path.parent == run_dir


class TestFixtureRun:
    def test_loads_fixture_and_generates_html(self):
        fixture_path = _FIXTURES / "sample_run.json"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        run = _dict_to_run_data(data)
        html = generate_html(run)
        assert len(html) > 10_000
        assert html.startswith("<!DOCTYPE html>")
        # Check key elements are present
        assert "REPORT_DATA" in html
        assert "Sample Alumnium Test Run" in html

    def test_fixture_has_expected_structure(self):
        fixture_path = _FIXTURES / "sample_run.json"
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert data["summary"]["total_features"] == 3
        assert data["summary"]["total_scenarios"] == 8
        assert data["summary"]["passed"] == 5
        assert data["summary"]["failed"] == 2
        assert data["summary"]["skipped"] == 1
        assert data["alumnium_model"] == "anthropic"
        assert data["narrative"] is not None
        # Check at least one scenario has ai_analysis
        has_ai = any(
            sc["ai_analysis"] is not None
            for feat in data["features"]
            for sc in feat["scenarios"]
        )
        assert has_ai

    def test_fixture_has_doc_string(self):
        fixture_path = _FIXTURES / "sample_run.json"
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        has_doc = any(
            step["doc_string"] is not None
            for feat in data["features"]
            for sc in feat["scenarios"]
            for step in sc["steps"]
        )
        assert has_doc

    def test_fixture_has_data_table(self):
        fixture_path = _FIXTURES / "sample_run.json"
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        has_table = any(
            step["data_table"] is not None
            for feat in data["features"]
            for sc in feat["scenarios"]
            for step in sc["steps"]
        )
        assert has_table

    def test_fixture_has_both_alumnium_types(self):
        fixture_path = _FIXTURES / "sample_run.json"
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        types = {
            step["alumnium_type"]
            for feat in data["features"]
            for sc in feat["scenarios"]
            for step in sc["steps"]
        }
        assert "do" in types
        assert "check" in types
