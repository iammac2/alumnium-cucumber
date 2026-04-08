"""Tests for alumniumcucumber.reporting.analyser."""

import json
from unittest.mock import MagicMock

import pytest

from alumniumcucumber.reporting.analyser import AiAnalyser, _build_transcript
from alumniumcucumber.reporting.bridge import LlmBridgeError, LlmProviderBridge
from alumniumcucumber.reporting.models import AiAnalysis, ScenarioData, StepData


def _make_step(
    keyword="Given",
    text="navigate to homepage",
    step_type="given",
    alumnium_type="do",
    status="passed",
    duration=1.0,
    error_message=None,
):
    return StepData(
        keyword=keyword,
        text=text,
        step_type=step_type,
        alumnium_type=alumnium_type,
        status=status,
        duration=duration,
        error_message=error_message,
        doc_string=None,
        data_table=None,
    )


def _make_scenario(steps=None, name="Test scenario", status="failed"):
    return ScenarioData(
        id="ABCD1234",
        name=name,
        tags=[],
        status=status,
        duration=sum(s.duration for s in (steps or [])),
        started_at="2026-04-02T12:00:00+00:00",
        steps=steps or [],
        ai_analysis=None,
    )


def _make_bridge(provider="anthropic"):
    bridge = MagicMock(spec=LlmProviderBridge)
    bridge.provider_name = provider
    return bridge


class TestAnalyserBridgeError:
    def test_returns_error_when_bridge_raises(self):
        bridge = _make_bridge()
        bridge.complete.side_effect = LlmBridgeError("no model configured")
        analyser = AiAnalyser(bridge)
        scenario = _make_scenario(
            steps=[_make_step(keyword="Then", step_type="then", alumnium_type="check", status="failed", error_message="AssertionError")]
        )
        result = analyser.analyse(scenario)
        assert isinstance(result, AiAnalysis)
        assert result.error is not None
        assert result.severity == "unknown"
        assert result.summary == "AI analysis unavailable."

    def test_returns_error_when_model_unset(self, monkeypatch):
        monkeypatch.delenv("ALUMNIUM_MODEL", raising=False)
        bridge = _make_bridge("unset")
        bridge.complete.side_effect = LlmBridgeError("ALUMNIUM_MODEL is not set")
        analyser = AiAnalyser(bridge)
        scenario = _make_scenario(
            steps=[_make_step(keyword="Then", step_type="then", alumnium_type="check", status="failed", error_message="Fail")]
        )
        result = analyser.analyse(scenario)
        assert result.error is not None


class TestMalformedResponse:
    def test_malformed_json_returns_error(self):
        bridge = _make_bridge()
        bridge.complete.return_value = "not valid json {{"
        analyser = AiAnalyser(bridge)
        scenario = _make_scenario(
            steps=[_make_step(keyword="Then", step_type="then", alumnium_type="check", status="failed", error_message="x")]
        )
        result = analyser.analyse(scenario)
        assert result.error is not None
        assert result.severity == "unknown"

    def test_missing_field_returns_error(self):
        bridge = _make_bridge()
        # Missing "suggestion" field
        bridge.complete.return_value = json.dumps({
            "summary": "it broke",
            "root_cause": "some cause",
            "severity": "high",
        })
        analyser = AiAnalyser(bridge)
        scenario = _make_scenario(
            steps=[_make_step(keyword="Then", step_type="then", alumnium_type="check", status="failed", error_message="x")]
        )
        result = analyser.analyse(scenario)
        assert result.error is not None


class TestSeverityNormalisation:
    def test_invalid_severity_normalised_to_unknown(self):
        bridge = _make_bridge()
        bridge.complete.return_value = json.dumps({
            "summary": "it broke",
            "root_cause": "some cause",
            "suggestion": "fix it",
            "severity": "catastrophic",  # invalid
        })
        analyser = AiAnalyser(bridge)
        scenario = _make_scenario(
            steps=[_make_step(keyword="Then", step_type="then", alumnium_type="check", status="failed", error_message="x")]
        )
        result = analyser.analyse(scenario)
        assert result.severity == "unknown"
        assert result.error is None

    def test_valid_severities_accepted(self):
        for sev in ["critical", "high", "medium", "low"]:
            bridge = _make_bridge()
            bridge.complete.return_value = json.dumps({
                "summary": "broke",
                "root_cause": "cause",
                "suggestion": "fix",
                "severity": sev,
            })
            analyser = AiAnalyser(bridge)
            scenario = _make_scenario(
                steps=[_make_step(keyword="Then", step_type="then", alumnium_type="check", status="failed", error_message="x")]
            )
            result = analyser.analyse(scenario)
            assert result.severity == sev
            assert result.error is None


class TestTranscriptFormat:
    def test_transcript_format_matches_spec(self):
        """Step transcript format snapshot test."""
        steps = [
            _make_step(
                keyword="Given",
                text='navigate to "https://example.com"',
                step_type="given",
                alumnium_type="do",
                status="passed",
                duration=0.82,
            ),
            _make_step(
                keyword="When",
                text='type "user@example.com" into the email field',
                step_type="when",
                alumnium_type="do",
                status="passed",
                duration=1.14,
            ),
            _make_step(
                keyword="Then",
                text="the dashboard is displayed",
                step_type="then",
                alumnium_type="check",
                status="failed",
                duration=8.31,
                error_message="AssertionError: al.check() failed.",
            ),
        ]
        scenario = _make_scenario(steps=steps)
        transcript = _build_transcript(scenario)
        assert '[Given]' in transcript
        assert '[When]' in transcript
        assert '[Then]' in transcript
        assert 'PASSED' in transcript
        assert 'FAILED' in transcript
        assert '[do]' in transcript
        assert '[check]' in transcript
        assert '0.82s' in transcript
        assert '8.31s' in transcript
        assert 'AssertionError' in transcript

    def test_no_failed_step_returns_error_analysis(self):
        bridge = _make_bridge()
        analyser = AiAnalyser(bridge)
        scenario = _make_scenario(
            steps=[_make_step(status="passed")],
            status="passed",
        )
        result = analyser.analyse(scenario)
        assert result.error == "No failed step found"


class TestSuccessPath:
    def test_successful_analysis_returns_correct_fields(self):
        bridge = _make_bridge("openai")
        bridge.complete.return_value = json.dumps({
            "summary": "Login failed due to missing redirect",
            "root_cause": "The page did not redirect after login. The session cookie was not set correctly.",
            "suggestion": "Check the auth service is returning the correct session token.",
            "severity": "high",
        })
        analyser = AiAnalyser(bridge)
        scenario = _make_scenario(
            steps=[_make_step(keyword="Then", step_type="then", alumnium_type="check", status="failed", error_message="no redirect")]
        )
        result = analyser.analyse(scenario)
        assert result.error is None
        assert result.severity == "high"
        assert result.provider == "openai"
        assert "Login failed" in result.summary

    def test_strips_markdown_fences(self):
        bridge = _make_bridge()
        bridge.complete.return_value = "```json\n" + json.dumps({
            "summary": "broke",
            "root_cause": "cause",
            "suggestion": "fix",
            "severity": "low",
        }) + "\n```"
        analyser = AiAnalyser(bridge)
        scenario = _make_scenario(
            steps=[_make_step(keyword="Then", step_type="then", alumnium_type="check", status="failed", error_message="x")]
        )
        result = analyser.analyse(scenario)
        assert result.error is None
        assert result.severity == "low"
