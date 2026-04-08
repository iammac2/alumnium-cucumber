"""Data models for the Alumnium reporter.

All models are Python dataclasses. All fields are typed.
All are JSON-serialisable via dataclasses.asdict().
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StepData:
    """Represents a single BDD step with its execution result."""

    keyword: str
    """Raw keyword: 'Given' | 'When' | 'Then' | 'And' | 'But' | '*'"""
    text: str
    """Step text after the keyword (step.name)."""
    step_type: str
    """Resolved: 'given' | 'when' | 'then' | 'step'"""
    alumnium_type: str
    """'do' | 'check'"""
    status: str
    """'passed' | 'failed' | 'skipped' | 'untested' | 'undefined'"""
    duration: float
    """Seconds, 3dp."""
    error_message: str | None
    """Truncated to 4000 chars; None if passed."""
    doc_string: str | None
    data_table: list[list[str]] | None
    """Header row first."""
    screenshot_path: str | None = None
    """Relative path from run dir e.g. 'screenshots/ABCD1234_step3.png'. None if not captured."""
    exception_type: str | None = None
    """Exception class name for 'error' status steps (e.g. 'RuntimeError'). None otherwise."""


@dataclass
class AiAnalysis:
    """AI-generated failure analysis for a scenario."""

    summary: str
    """<= 25 words. What failed and why."""
    root_cause: str
    """2-4 sentences. Technical explanation."""
    suggestion: str
    """1-3 sentences. How to fix or investigate."""
    severity: str
    """'critical' | 'high' | 'medium' | 'low' | 'unknown'"""
    provider: str
    """LLM provider used, e.g. 'anthropic', 'openai'."""
    error: str | None
    """Set if the API call failed; None on success."""


@dataclass
class ScenarioData:
    """Represents a single BDD scenario with its steps and analysis."""

    id: str
    """UUID4 first 8 chars, uppercase."""
    name: str
    tags: list[str]
    status: str
    """'passed' | 'failed' | 'skipped' | 'untested'"""
    duration: float
    """Sum of step durations, 3dp."""
    started_at: str
    """ISO 8601."""
    steps: list[StepData]
    ai_analysis: AiAnalysis | None
    """None unless status == 'failed' and AI enabled."""


@dataclass
class FeatureData:
    """Represents a BDD feature file with its scenarios."""

    name: str
    file: str
    """Relative path preferred."""
    description: str
    """' '.join(feature.description), may be ''."""
    tags: list[str]
    scenarios: list[ScenarioData]


@dataclass
class RunSummary:
    """Aggregated counts for an entire test run."""

    total_features: int
    total_scenarios: int
    passed: int
    failed: int
    skipped: int
    """Includes untested and undefined."""
    total_duration: float
    """Seconds, 2dp."""
    pass_rate: float
    """0.0-100.0, 1dp."""


@dataclass
class Narrative:
    """AI-generated stakeholder narrative for a test run."""

    headline: str
    """<= 15 words. Overall run headline for stakeholders."""
    body: str
    """2-4 paragraph stakeholder summary (plain English, no jargon)."""
    risk_level: str
    """'green' | 'amber' | 'red'"""
    provider: str
    """LLM provider used."""
    error: str | None


@dataclass
class RunData:
    """Complete data for a single test run."""

    run_id: str
    """8-char uppercase hex."""
    title: str
    """User-configured."""
    started_at: str
    """ISO 8601."""
    finished_at: str
    """ISO 8601."""
    alumnium_model: str
    """Value of ALUMNIUM_MODEL env var, or 'unset'."""
    summary: RunSummary
    features: list[FeatureData]
    narrative: Narrative | None
    """None if AI disabled or generation failed."""
    screenshot_mode: str = "on_failure"
    """'on_failure' | 'every_step' | 'off'"""
