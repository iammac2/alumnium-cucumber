"""Tests for alumniumcucumber.reporting.narrative."""

import json
from unittest.mock import MagicMock

import pytest

from alumniumcucumber.reporting.bridge import LlmBridgeError, LlmProviderBridge
from alumniumcucumber.reporting.models import (
    FeatureData,
    Narrative,
    RunData,
    RunSummary,
    ScenarioData,
    StepData,
)
from alumniumcucumber.reporting.narrative import NarrativeGenerator


def _make_run_data(features=None, passed=3, failed=0, skipped=0):
    total = passed + failed + skipped
    summary = RunSummary(
        total_features=len(features) if features else 0,
        total_scenarios=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        total_duration=10.0,
        pass_rate=round(passed / total * 100, 1) if total else 0.0,
    )
    return RunData(
        run_id="ABCD1234",
        title="Test Run",
        started_at="2026-04-02T12:00:00+00:00",
        finished_at="2026-04-02T12:01:00+00:00",
        alumnium_model="anthropic",
        summary=summary,
        features=features or [],
        narrative=None,
    )


def _make_bridge(provider="anthropic"):
    bridge = MagicMock(spec=LlmProviderBridge)
    bridge.provider_name = provider
    return bridge


class TestNarrativeGeneratorErrors:
    def test_returns_narrative_with_error_when_bridge_raises(self):
        bridge = _make_bridge()
        bridge.complete.side_effect = LlmBridgeError("provider error")
        gen = NarrativeGenerator(bridge)
        run = _make_run_data()
        result = gen.generate(run)
        assert isinstance(result, Narrative)
        assert result.error is not None
        assert result.headline == "Narrative unavailable."
        assert result.risk_level == "amber"

    def test_returns_narrative_with_error_on_malformed_json(self):
        bridge = _make_bridge()
        bridge.complete.return_value = "{ bad json }"
        gen = NarrativeGenerator(bridge)
        run = _make_run_data()
        result = gen.generate(run)
        assert result.error is not None


class TestRiskLevels:
    def test_green_risk_level(self):
        bridge = _make_bridge()
        bridge.complete.return_value = json.dumps({
            "headline": "All tests passed successfully",
            "body": "Everything is working well.",
            "risk_level": "green",
        })
        gen = NarrativeGenerator(bridge)
        run = _make_run_data(passed=5)
        result = gen.generate(run)
        assert result.risk_level == "green"
        assert result.error is None

    def test_amber_risk_level(self):
        bridge = _make_bridge()
        bridge.complete.return_value = json.dumps({
            "headline": "Some failures detected",
            "body": "Some tests failed.",
            "risk_level": "amber",
        })
        gen = NarrativeGenerator(bridge)
        run = _make_run_data(passed=4, failed=1)
        result = gen.generate(run)
        assert result.risk_level == "amber"

    def test_red_risk_level(self):
        bridge = _make_bridge()
        bridge.complete.return_value = json.dumps({
            "headline": "Critical failures",
            "body": "Critical tests failed.",
            "risk_level": "red",
        })
        gen = NarrativeGenerator(bridge)
        run = _make_run_data(passed=1, failed=4)
        result = gen.generate(run)
        assert result.risk_level == "red"

    def test_invalid_risk_level_defaults_to_amber(self):
        bridge = _make_bridge()
        bridge.complete.return_value = json.dumps({
            "headline": "Something happened",
            "body": "Results unclear.",
            "risk_level": "purple",
        })
        gen = NarrativeGenerator(bridge)
        run = _make_run_data()
        result = gen.generate(run)
        assert result.risk_level == "amber"


class TestInputConstruction:
    def test_empty_features_handled(self):
        bridge = _make_bridge()
        bridge.complete.return_value = json.dumps({
            "headline": "No tests ran",
            "body": "Nothing was executed.",
            "risk_level": "green",
        })
        gen = NarrativeGenerator(bridge)
        run = _make_run_data(features=[], passed=0, failed=0, skipped=0)
        result = gen.generate(run)
        assert result.error is None

    def test_provider_set_in_result(self):
        bridge = _make_bridge("openai")
        bridge.complete.return_value = json.dumps({
            "headline": "Passed",
            "body": "All good.",
            "risk_level": "green",
        })
        gen = NarrativeGenerator(bridge)
        run = _make_run_data(passed=3)
        result = gen.generate(run)
        assert result.provider == "openai"

    def test_strips_markdown_fences(self):
        bridge = _make_bridge()
        bridge.complete.return_value = "```json\n" + json.dumps({
            "headline": "Done",
            "body": "All passed.",
            "risk_level": "green",
        }) + "\n```"
        gen = NarrativeGenerator(bridge)
        run = _make_run_data(passed=2)
        result = gen.generate(run)
        assert result.error is None
        assert result.headline == "Done"
