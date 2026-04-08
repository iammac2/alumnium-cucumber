"""CLI entry point for regenerating an Alumnium HTML report from JSON data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import AiAnalysis, FeatureData, Narrative, RunData, RunSummary, ScenarioData, StepData
from .generator import ReportGenerator


def _dict_to_step(d: dict) -> StepData:
    """Reconstruct a StepData from a dict."""
    return StepData(
        keyword=d["keyword"],
        text=d["text"],
        step_type=d["step_type"],
        alumnium_type=d["alumnium_type"],
        status=d["status"],
        duration=d["duration"],
        error_message=d.get("error_message"),
        doc_string=d.get("doc_string"),
        data_table=d.get("data_table"),
        screenshot_path=d.get("screenshot_path"),
        exception_type=d.get("exception_type"),
    )


def _dict_to_ai_analysis(d: dict | None) -> AiAnalysis | None:
    """Reconstruct an AiAnalysis from a dict or return None."""
    if d is None:
        return None
    return AiAnalysis(
        summary=d["summary"],
        root_cause=d["root_cause"],
        suggestion=d["suggestion"],
        severity=d["severity"],
        provider=d["provider"],
        error=d.get("error"),
    )


def _dict_to_scenario(d: dict) -> ScenarioData:
    """Reconstruct a ScenarioData from a dict."""
    return ScenarioData(
        id=d["id"],
        name=d["name"],
        tags=d.get("tags", []),
        status=d["status"],
        duration=d["duration"],
        started_at=d["started_at"],
        steps=[_dict_to_step(s) for s in d.get("steps", [])],
        ai_analysis=_dict_to_ai_analysis(d.get("ai_analysis")),
    )


def _dict_to_feature(d: dict) -> FeatureData:
    """Reconstruct a FeatureData from a dict."""
    return FeatureData(
        name=d["name"],
        file=d["file"],
        description=d.get("description", ""),
        tags=d.get("tags", []),
        scenarios=[_dict_to_scenario(s) for s in d.get("scenarios", [])],
    )


def _dict_to_narrative(d: dict | None) -> Narrative | None:
    """Reconstruct a Narrative from a dict or return None."""
    if d is None:
        return None
    return Narrative(
        headline=d["headline"],
        body=d["body"],
        risk_level=d["risk_level"],
        provider=d["provider"],
        error=d.get("error"),
    )


def _dict_to_run_summary(d: dict) -> RunSummary:
    """Reconstruct a RunSummary from a dict."""
    return RunSummary(
        total_features=d["total_features"],
        total_scenarios=d["total_scenarios"],
        passed=d["passed"],
        failed=d["failed"],
        skipped=d["skipped"],
        total_duration=d["total_duration"],
        pass_rate=d["pass_rate"],
    )


def _dict_to_run_data(d: dict) -> RunData:
    """Reconstruct RunData hierarchy from dataclasses.asdict() output."""
    return RunData(
        run_id=d["run_id"],
        title=d["title"],
        started_at=d["started_at"],
        finished_at=d["finished_at"],
        alumnium_model=d["alumnium_model"],
        summary=_dict_to_run_summary(d["summary"]),
        features=[_dict_to_feature(f) for f in d.get("features", [])],
        narrative=_dict_to_narrative(d.get("narrative")),
        screenshot_mode=d.get("screenshot_mode", "on_failure"),
    )


def main() -> None:
    """Re-generate an Alumnium HTML report from a JSON data file."""
    parser = argparse.ArgumentParser(
        description="Re-generate an Alumnium HTML report from a JSON data file."
    )
    parser.add_argument("json_file", help="Path to report_*.json")
    parser.add_argument("--output", default="reports", help="Output directory")
    args = parser.parse_args()

    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"Error: file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        run_data = _dict_to_run_data(data)
        _, html_path, _ = ReportGenerator(args.output).write(run_data)
        print(html_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
