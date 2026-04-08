"""Regression Narrative Generator for the Alumnium reporter.

Generates a plain-English stakeholder summary of the entire test run.
"""

from __future__ import annotations

import json
import re

from .bridge import LlmProviderBridge, LlmBridgeError
from .models import Narrative, RunData

_SYSTEM_PROMPT = (
    "You are writing a test results summary for a non-technical product stakeholder.\n"
    "Do not use testing jargon (no \"assertions\", \"fixtures\", \"step definitions\").\n"
    "Do not mention specific error messages, stack traces, or line numbers.\n"
    "Write in plain English as if briefing a product manager.\n"
    "Reply ONLY with a valid JSON object. No markdown, no preamble."
)

_VALID_RISK_LEVELS = {"green", "amber", "red"}


def _strip_fences(text: str) -> str:
    """Strip markdown code fences from a JSON response."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _build_run_summary_text(run_data: RunData) -> str:
    """Build the run summary text for the LLM prompt (§9.3)."""
    s = run_data.summary
    lines = [
        f'Test run: "{run_data.title}"',
        f"Executed: {s.total_scenarios} scenarios across {s.total_features} features",
        f"Passed: {s.passed}  Failed: {s.failed}  Skipped: {s.skipped}",
        f"Total duration: {s.total_duration:.2f}s",
        f"LLM model: {run_data.alumnium_model}",
        "",
        "Failed scenarios:",
    ]

    found_any = False
    for feature in run_data.features:
        for scenario in feature.scenarios:
            if scenario.status == "failed":
                found_any = True
                if scenario.ai_analysis and scenario.ai_analysis.summary and not scenario.ai_analysis.error:
                    analysis_text = scenario.ai_analysis.summary
                else:
                    # Use first failed step error truncated to 200 chars
                    failed_steps = [st for st in scenario.steps if st.status == "failed"]
                    if failed_steps and failed_steps[0].error_message:
                        analysis_text = failed_steps[0].error_message[:200]
                    else:
                        analysis_text = "No error detail available"
                lines.append(f"  Feature: {feature.name}")
                lines.append(f"  Scenario: {scenario.name}")
                lines.append(f"  AI analysis: {analysis_text}")
                lines.append("")

    if not found_any:
        lines.append("  (none)")

    return "\n".join(lines)


class NarrativeGenerator:
    """Generates AI-powered stakeholder narrative for a test run."""

    def __init__(self, bridge: LlmProviderBridge) -> None:
        """Initialise the generator with an LLM provider bridge."""
        self._bridge = bridge

    def generate(self, run_data: RunData) -> Narrative:
        """Generate a Narrative for the test run.

        Returns a Narrative with error set if generation fails —
        never raises.
        """
        try:
            return self._do_generate(run_data)
        except Exception as e:
            return Narrative(
                headline="Narrative unavailable.",
                body="",
                risk_level="amber",
                provider=self._bridge.provider_name,
                error=str(e),
            )

    def _do_generate(self, run_data: RunData) -> Narrative:
        """Internal: perform generation, may raise."""
        run_summary_text = _build_run_summary_text(run_data)
        user_message = (
            f"{run_summary_text}\n\n"
            "Return JSON with exactly these fields:\n"
            "{\n"
            '  "headline":    "<max 15 words, the most important thing to know about this run>",\n'
            '  "body":        "<2-4 paragraphs separated by \\n\\n. Plain English. '
            'What worked, what didn\'t, impact, recommended action.>",\n'
            '  "risk_level":  "<green|amber|red>"\n'
            "}\n\n"
            "Risk level guide:\n"
            "  green = all passed or only minor skips\n"
            "  amber = some failures but core flows passed\n"
            "  red   = critical path failures or >30% fail rate"
        )

        try:
            raw = self._bridge.complete(_SYSTEM_PROMPT, user_message, max_tokens=800)
        except LlmBridgeError as e:
            return Narrative(
                headline="Narrative unavailable.",
                body="",
                risk_level="amber",
                provider=self._bridge.provider_name,
                error=str(e),
            )

        cleaned = _strip_fences(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            return Narrative(
                headline="Narrative unavailable.",
                body="",
                risk_level="amber",
                provider=self._bridge.provider_name,
                error=f"JSON parse error: {e}",
            )

        required = {"headline", "body", "risk_level"}
        missing = required - set(data.keys())
        if missing:
            return Narrative(
                headline="Narrative unavailable.",
                body="",
                risk_level="amber",
                provider=self._bridge.provider_name,
                error=f"Missing fields: {missing}",
            )

        risk_level = str(data["risk_level"]).lower()
        if risk_level not in _VALID_RISK_LEVELS:
            risk_level = "amber"

        return Narrative(
            headline=str(data["headline"]),
            body=str(data["body"]),
            risk_level=risk_level,
            provider=self._bridge.provider_name,
            error=None,
        )
