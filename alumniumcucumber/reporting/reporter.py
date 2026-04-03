"""AlumniumReporter — behave lifecycle hook receiver and data collector."""

from __future__ import annotations

import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .analyser import AiAnalyser
from .bridge import LlmProviderBridge
from .models import (
    AiAnalysis,
    FeatureData,
    Narrative,
    RunData,
    RunSummary,
    ScenarioData,
    StepData,
)
from .narrative import NarrativeGenerator


def _safe(method_name: str):
    """Decorator factory: wrap a method so it never raises, logging to stderr."""
    def decorator(fn):
        def wrapper(self, *args, **kwargs):
            try:
                return fn(self, *args, **kwargs)
            except Exception as e:  # noqa: BLE001
                print(
                    f"[alumnium-reporter] ERROR: {method_name}: {e}",
                    file=sys.stderr,
                )
        return wrapper
    return decorator


class AlumniumReporter:
    """Behave lifecycle hook receiver that collects test data and generates reports.

    Usage in features/environment.py::

        from alumniumcucumber.reporting import AlumniumReporter

        _reporter = AlumniumReporter(output_dir="reports", enable_ai=True)

        def before_feature(context, feature):
            _reporter.before_feature(context, feature)

        # ... etc.

        def after_all(context):
            _reporter.generate_report()
    """

    def __init__(
        self,
        output_dir: str = "reports",
        enable_ai: bool = True,
        report_title: str = "Alumnium Test Report",
        screenshot_mode: str = "on_failure",
    ) -> None:
        """Initialise the reporter.

        Args:
            output_dir: Parent output directory. Each run creates a subdirectory.
            enable_ai: Master switch. If False, all AI calls are skipped.
            report_title: Shown in the HTML report header.
            screenshot_mode: 'on_failure' | 'every_step' | 'off'.
        """
        self._output_dir = output_dir
        self._enable_ai = enable_ai
        self._report_title = report_title
        self._screenshot_mode = screenshot_mode

        # Internal state
        self._run_id = secrets.token_hex(4).upper()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._bridge = LlmProviderBridge()

        # Per-run directory paths (determined here so screenshots can be written during the run)
        self._run_dir = Path(output_dir) / f"run_{self._run_id}"
        self._screenshots_dir = self._run_dir / "screenshots"

        self._run_data = RunData(
            run_id=self._run_id,
            title=report_title,
            started_at=self._started_at,
            finished_at="",
            alumnium_model=self._bridge._raw_model or "unset",
            summary=RunSummary(
                total_features=0,
                total_scenarios=0,
                passed=0,
                failed=0,
                skipped=0,
                total_duration=0.0,
                pass_rate=0.0,
            ),
            features=[],
            narrative=None,
            screenshot_mode=screenshot_mode,
        )
        self._current_feature: FeatureData | None = None
        self._current_scenario: ScenarioData | None = None
        self._step_start: float = 0.0
        self._prev_step_type: str | None = None

    @_safe("before_feature")
    def before_feature(self, context, feature) -> None:
        """Create a FeatureData and set it as the current feature."""
        self._current_feature = FeatureData(
            name=feature.name,
            file=feature.filename,
            description=" ".join(feature.description) if feature.description else "",
            tags=list(feature.tags) if feature.tags else [],
            scenarios=[],
        )
        self._prev_step_type = None

    @_safe("after_feature")
    def after_feature(self, context, feature) -> None:
        """Append the current feature to run data."""
        if self._current_feature is not None:
            self._run_data.features.append(self._current_feature)
        self._current_feature = None

    @_safe("before_scenario")
    def before_scenario(self, context, scenario) -> None:
        """Create a ScenarioData and set it as the current scenario."""
        import uuid  # noqa: PLC0415
        scenario_id = str(uuid.uuid4()).replace("-", "")[:8].upper()
        self._current_scenario = ScenarioData(
            id=scenario_id,
            name=scenario.name,
            tags=list(scenario.tags) if scenario.tags else [],
            status="running",
            duration=0.0,
            started_at=datetime.now(timezone.utc).isoformat(),
            steps=[],
            ai_analysis=None,
        )
        self._prev_step_type = None

    def set_model_identity(self, al: object) -> None:
        """Enrich alumnium_model with the resolved name from the Alumni instance.

        Called once per run (guards against repeat calls). Falls back silently
        if Alumni internals change.
        """
        if getattr(self, "_model_resolved", False):
            return
        try:
            provider = al.model.provider.value  # e.g. "ollama"
            name = al.model.name  # e.g. "mistral-small3.1"
            if provider and name:
                self._run_data.alumnium_model = f"{provider}/{name}"
                self._model_resolved = True
        except Exception:  # noqa: BLE001
            pass  # leave existing value if Alumni structure changes

    @_safe("after_scenario")
    def after_scenario(self, context, scenario) -> None:
        """Finalise the scenario, run AI analysis if needed, append to feature."""
        if self._current_scenario is None:
            return

        # Map behave Status to string
        status_str = _status_to_str(scenario.status)
        self._current_scenario.status = status_str
        self._current_scenario.duration = round(
            sum(s.duration for s in self._current_scenario.steps), 3
        )

        if status_str == "failed" and self._enable_ai:
            try:
                analyser = AiAnalyser(self._bridge)
                self._current_scenario.ai_analysis = analyser.analyse(self._current_scenario)
            except Exception as e:  # noqa: BLE001
                print(
                    f"[alumnium-reporter] ERROR: AI analysis failed: {e}",
                    file=sys.stderr,
                )
                self._current_scenario.ai_analysis = AiAnalysis(
                    summary="AI analysis unavailable.",
                    root_cause=str(e),
                    suggestion="Check LLM provider configuration.",
                    severity="unknown",
                    provider=self._bridge.provider_name,
                    error=str(e),
                )

        if self._current_feature is not None:
            self._current_feature.scenarios.append(self._current_scenario)

        self._current_scenario = None

    @_safe("before_step")
    def before_step(self, context, step) -> None:
        """Record the step start time."""
        self._step_start = time.monotonic()

    @_safe("after_step")
    def after_step(self, context, step) -> None:
        """Compute duration, derive alumnium_type, create StepData."""
        if self._current_scenario is None:
            return

        duration = round(time.monotonic() - self._step_start, 3)
        status_str = _status_to_str(step.status)

        # Derive alumnium_type from step_type
        step_type = step.step_type  # 'given', 'when', 'then', 'step'
        alumnium_type = _derive_alumnium_type(step_type, self._prev_step_type)

        # Update prev step type for 'And'/'But' ('step') inheritance
        if step_type != "step":
            self._prev_step_type = step_type

        # Truncate error message
        error_message = getattr(step, "error_message", None)
        if error_message and len(error_message) > 4000:
            error_message = error_message[:4000]

        # Convert data table
        data_table = None
        if hasattr(step, "table") and step.table is not None:
            data_table = [list(step.table.headings)]
            for row in step.table.rows:
                data_table.append(list(row.cells))

        doc_string = getattr(step, "text", None)

        step_data = StepData(
            keyword=step.keyword.strip(),
            text=step.name,
            step_type=step_type,
            alumnium_type=alumnium_type,
            status=status_str,
            duration=duration,
            error_message=error_message,
            doc_string=doc_string,
            data_table=data_table,
        )
        self._current_scenario.steps.append(step_data)

    def attach_screenshot(self, png_bytes: bytes | None) -> None:
        """Write a PNG screenshot for the most recently recorded step.

        Safe to call unconditionally — respects screenshot_mode and silently
        handles None/empty bytes or write failures. Never affects test outcome.
        """
        if self._screenshot_mode == "off":
            return
        if not png_bytes:
            return
        if self._current_scenario is None or not self._current_scenario.steps:
            return

        last_step = self._current_scenario.steps[-1]

        if self._screenshot_mode == "on_failure" and last_step.status != "failed":
            return

        step_index = len(self._current_scenario.steps)
        scenario_id = self._current_scenario.id
        filename = f"{scenario_id}_step{step_index}.png"

        try:
            self._screenshots_dir.mkdir(parents=True, exist_ok=True)
            (self._screenshots_dir / filename).write_bytes(png_bytes)
            last_step.screenshot_path = f"screenshots/{filename}"
        except Exception as e:  # noqa: BLE001
            print(
                f"[alumnium-reporter] WARNING: screenshot write failed: {e}",
                file=sys.stderr,
            )

    def generate_report(self) -> Path:
        """Finalise and write the report. Returns the Path to the HTML file.

        Called from after_all() in environment.py.
        """
        try:
            return self._do_generate_report()
        except Exception as e:  # noqa: BLE001
            print(
                f"[alumnium-reporter] ERROR: generate_report failed: {e}",
                file=sys.stderr,
            )
            # Return a dummy path so callers don't break
            return Path(self._output_dir) / f"report_{self._run_id}.html"

    def _do_generate_report(self) -> Path:
        """Internal: generate the report. May raise."""
        from .generator import ReportGenerator  # noqa: PLC0415

        self._run_data.finished_at = datetime.now(timezone.utc).isoformat()
        self._run_data.summary = _compute_summary(self._run_data)

        if self._enable_ai:
            if not self._bridge._raw_model:
                print(
                    "[alumnium-reporter] WARNING: ALUMNIUM_MODEL is unset; "
                    "AI narrative skipped.",
                    file=sys.stderr,
                )
            else:
                try:
                    gen = NarrativeGenerator(self._bridge)
                    self._run_data.narrative = gen.generate(self._run_data)
                except Exception as e:  # noqa: BLE001
                    print(
                        f"[alumnium-reporter] ERROR: narrative generation failed: {e}",
                        file=sys.stderr,
                    )

        run_dir, html_path, json_path = ReportGenerator(self._output_dir).write(self._run_data)

        s = self._run_data.summary
        n_screenshots = (
            len(list((run_dir / "screenshots").glob("*.png")))
            if (run_dir / "screenshots").exists()
            else 0
        )
        screenshots_line = (
            f"   Screenshots  \u2192  {run_dir / 'screenshots'}/  ({n_screenshots} captured)\n"
            if n_screenshots
            else ""
        )
        print(
            f"\u2705  Alumnium Report  \u00b7  {s.passed}/{s.total_scenarios} passed"
            f"  \u00b7  Run {self._run_data.run_id}\n\n"
            f"   Folder  \u2192  {run_dir}/\n"
            f"   HTML    \u2192  {html_path}\n"
            f"   JSON    \u2192  {json_path}\n"
            f"{screenshots_line}"
        )

        from .server import launch  # noqa: PLC0415
        launch(run_dir, "report.html")

        return html_path


def _status_to_str(status) -> str:
    """Convert a behave Status enum (or string) to a lowercase string."""
    if hasattr(status, "name"):
        return status.name.lower()
    return str(status).lower()


def _derive_alumnium_type(step_type: str, prev_step_type: str | None) -> str:
    """Derive the alumnium_type ('do' or 'check') from step_type."""
    if step_type == "then":
        return "check"
    if step_type in ("given", "when"):
        return "do"
    # step_type == 'step' — inherit from most recent non-step; default 'do'
    if prev_step_type == "then":
        return "check"
    return "do"


def _compute_summary(run_data: RunData) -> RunSummary:
    """Compute the RunSummary from accumulated features."""
    total_features = len(run_data.features)
    total_scenarios = 0
    passed = 0
    failed = 0
    skipped = 0
    total_duration = 0.0

    for feature in run_data.features:
        for scenario in feature.scenarios:
            total_scenarios += 1
            total_duration += scenario.duration
            if scenario.status == "passed":
                passed += 1
            elif scenario.status == "failed":
                failed += 1
            else:
                skipped += 1

    pass_rate = round((passed / total_scenarios * 100), 1) if total_scenarios else 0.0

    return RunSummary(
        total_features=total_features,
        total_scenarios=total_scenarios,
        passed=passed,
        failed=failed,
        skipped=skipped,
        total_duration=round(total_duration, 2),
        pass_rate=pass_rate,
    )
