"""AI Failure Analyser for the Alumnium reporter.

Generates per-scenario failure analysis using the configured LLM provider.
"""

from __future__ import annotations

import json
import re

from .bridge import LlmProviderBridge, LlmBridgeError
from .models import AiAnalysis, ScenarioData

_SYSTEM_PROMPT = (
    "You are a senior QA engineer reviewing a failed BDD test scenario.\n"
    "Tests use alumnium-cucumber: plain-English Gherkin steps are forwarded to an LLM\n"
    "which drives a browser. \"do\" steps perform actions; \"check\" steps assert conditions.\n"
    "Explain failures clearly for engineers and product teams.\n"
    "Reply ONLY with a valid JSON object. No markdown, no preamble, no trailing text."
)

_VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def _strip_fences(text: str) -> str:
    """Strip markdown code fences from a JSON response."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _build_transcript(scenario: ScenarioData) -> str:
    """Build a human-readable step transcript for the LLM prompt."""
    lines = []
    for step in scenario.steps:
        status_label = step.status.upper()
        duration_str = f"{step.duration:.2f}s"
        line = (
            f"  [{step.keyword}] {step.text}"
            f"  \u2192  {status_label} ({duration_str})  [{step.alumnium_type}]"
        )
        lines.append(line)
        if step.status == "failed" and step.error_message:
            lines.append(f"  Error: {step.error_message}")
    return "\n".join(lines)


class AiAnalyser:
    """Generates AI-powered failure analysis for failed BDD scenarios."""

    def __init__(self, bridge: LlmProviderBridge) -> None:
        """Initialise the analyser with an LLM provider bridge."""
        self._bridge = bridge

    def analyse(self, scenario: ScenarioData) -> AiAnalysis:
        """Analyse a failed scenario and return an AiAnalysis.

        Returns an AiAnalysis with error set if analysis fails —
        never raises.
        """
        try:
            return self._do_analyse(scenario)
        except Exception as e:
            return AiAnalysis(
                summary="AI analysis unavailable.",
                root_cause=str(e),
                suggestion="Check LLM provider configuration.",
                severity="unknown",
                provider=self._bridge.provider_name,
                error=str(e),
            )

    def _do_analyse(self, scenario: ScenarioData) -> AiAnalysis:
        """Internal: perform the analysis, may raise."""
        failed_steps = [s for s in scenario.steps if s.status == "failed"]
        if not failed_steps:
            return AiAnalysis(
                summary="AI analysis unavailable.",
                root_cause="No failed step found in scenario.",
                suggestion="Check LLM provider configuration.",
                severity="unknown",
                provider=self._bridge.provider_name,
                error="No failed step found",
            )

        transcript = _build_transcript(scenario)
        user_message = (
            f'Failed scenario: "{scenario.name}"\n\n'
            f"Steps:\n{transcript}\n\n"
            "Return JSON with exactly these fields:\n"
            "{\n"
            '  "summary":    "<one sentence, max 25 words>",\n'
            '  "root_cause": "<2-4 sentences, technical explanation>",\n'
            '  "suggestion": "<1-3 sentences, how to fix or investigate>",\n'
            '  "severity":   "<critical|high|medium|low>"\n'
            "}"
        )

        try:
            raw = self._bridge.complete(_SYSTEM_PROMPT, user_message, max_tokens=600)
        except LlmBridgeError as e:
            return AiAnalysis(
                summary="AI analysis unavailable.",
                root_cause=str(e),
                suggestion="Check LLM provider configuration.",
                severity="unknown",
                provider=self._bridge.provider_name,
                error=str(e),
            )

        cleaned = _strip_fences(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            return AiAnalysis(
                summary="AI analysis unavailable.",
                root_cause=f"Failed to parse JSON response: {e}",
                suggestion="Check LLM provider configuration.",
                severity="unknown",
                provider=self._bridge.provider_name,
                error=f"JSON parse error: {e}",
            )

        # Validate required fields
        required = {"summary", "root_cause", "suggestion", "severity"}
        missing = required - set(data.keys())
        if missing:
            return AiAnalysis(
                summary="AI analysis unavailable.",
                root_cause=f"Missing fields in response: {missing}",
                suggestion="Check LLM provider configuration.",
                severity="unknown",
                provider=self._bridge.provider_name,
                error=f"Missing fields: {missing}",
            )

        severity = str(data["severity"]).lower()
        if severity not in _VALID_SEVERITIES:
            severity = "unknown"

        return AiAnalysis(
            summary=str(data["summary"]),
            root_cause=str(data["root_cause"]),
            suggestion=str(data["suggestion"]),
            severity=severity,
            provider=self._bridge.provider_name,
            error=None,
        )
