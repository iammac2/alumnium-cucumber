"""Alumnium Reporter submodule.

Provides a drop-in reporting integration for behave-based alumnium-cucumber test suites.
"""

from .reporter import AlumniumReporter
from .models import (
    RunData,
    FeatureData,
    ScenarioData,
    StepData,
    AiAnalysis,
    Narrative,
    RunSummary,
)
from .generator import generate_html, generate_json

__all__ = [
    "AlumniumReporter",
    "RunData",
    "FeatureData",
    "ScenarioData",
    "StepData",
    "AiAnalysis",
    "Narrative",
    "RunSummary",
    "generate_html",
    "generate_json",
]
