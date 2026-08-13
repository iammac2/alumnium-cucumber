"""AlumniumReporter — behave lifecycle hook receiver and data collector."""

from __future__ import annotations

import dataclasses
import os
import secrets
import shutil
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
            chat_api_key=os.environ.get("ALUMNIUM_CHAT_API_KEY") or None,
            chat_api_base=os.environ.get("ALUMNIUM_CHAT_BASE_URL") or None,
            chat_model=os.environ.get("ALUMNIUM_CHAT_MODEL") or None,
        )
        self._current_feature: FeatureData | None = None
        self._current_scenario: ScenarioData | None = None
        self._step_start: float = 0.0
        self._prev_step_type: str | None = None
        # al.metrics entries consumed so far in the current scenario (issue #8).
        self._consumed: int = 0
        # (ScenarioData, al.artifacts_dir) pairs, for collecting traces at report time.
        self._scenario_artifacts: list[tuple[ScenarioData, str]] = []
        self._traces_dir = self._run_dir / "traces"

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
        # A fresh Alumni instance is created per scenario, so its metrics list resets too.
        self._consumed = 0

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

        # Capture the Alumnium artifacts dir while the session/driver are still alive
        # (environment.py calls al.quit() after this hook). The Playwright trace.zip is
        # written on quit, so it is collected later at report-generation time.
        al = getattr(context, "al", None)
        if al is not None:
            try:
                self._scenario_artifacts.append((self._current_scenario, str(al.artifacts_dir)))
            except Exception:  # noqa: BLE001
                pass  # older Alumnium without artifacts support

        # Map behave Status to string
        status_str = _status_to_str(scenario.status)
        self._current_scenario.status = status_str
        self._current_scenario.duration = round(
            sum(s.duration for s in self._current_scenario.steps), 3
        )

        if status_str in ("failed", "error") and self._enable_ai:
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

        # Capture exception class name for 'error' status steps
        exception_type = None
        exc = getattr(step, "exception", None)
        if exc is not None:
            exception_type = type(exc).__name__

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
            exception_type=exception_type,
        )
        self._current_scenario.steps.append(step_data)
        self._enrich_from_metrics(context, step_data)

    def _al_metrics(self, context):
        """Return al.metrics for the current scenario, or None (older/absent Alumnium)."""
        al = getattr(context, "al", None)
        if al is None:
            return None
        try:
            return al.metrics
        except Exception:  # noqa: BLE001
            return None

    def _enrich_from_metrics(self, context, step_data: StepData) -> None:
        """Attach per-step tokens/duration/outcome/artifacts from al.metrics (issue #8).

        Correlation is positional: metrics entries are consumed in call order. A step that
        did not dispatch to Alumnium simply adds no new entry, so alignment is preserved.
        Degrades gracefully when al.metrics is unavailable.
        """
        metrics = self._al_metrics(context)
        if metrics is None:
            return
        try:
            all_steps = list(metrics.steps)
        except Exception:  # noqa: BLE001
            return
        new_steps = all_steps[self._consumed :]
        self._consumed = len(all_steps)
        if not new_steps:
            return

        ms = new_steps[-1]
        step_data.tokens = dataclasses.asdict(ms.tokens)
        step_data.alumnium_duration = ms.duration
        step_data.alumnium_outcome = ms.outcome
        step_data.artifacts = [{"path": str(a.path), "kind": a.kind, "mime": a.mime} for a in ms.artifacts]
        self._copy_screenshot_from_metrics(ms, step_data)

    def _copy_screenshot_from_metrics(self, ms, step_data: StepData) -> None:
        """Copy a screenshot captured by Alumnium into the report dir, honouring screenshot_mode."""
        if self._screenshot_mode == "off":
            return
        if self._screenshot_mode == "on_failure" and step_data.status not in ("failed", "error"):
            return
        if self._current_scenario is None:
            return
        shots = [a for a in ms.artifacts if a.kind == "screenshot"]
        if not shots:
            return
        src = Path(shots[-1].path)
        if not src.exists():
            return
        index = len(self._current_scenario.steps)
        filename = f"{self._current_scenario.id}_step{index}.png"
        try:
            self._screenshots_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, self._screenshots_dir / filename)
            step_data.screenshot_path = f"screenshots/{filename}"
        except Exception as e:  # noqa: BLE001
            print(f"[alumnium-reporter] WARNING: screenshot copy failed: {e}", file=sys.stderr)

    def _collect_traces(self) -> None:
        """Copy each scenario's Playwright trace.zip (written on al.quit()) into the report."""
        for scenario_data, artifacts_dir in self._scenario_artifacts:
            src = Path(artifacts_dir) / "trace.zip"
            if not src.exists():
                continue
            try:
                self._traces_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, self._traces_dir / f"{scenario_data.id}.zip")
                scenario_data.trace_path = f"traces/{scenario_data.id}.zip"
            except Exception as e:  # noqa: BLE001
                print(f"[alumnium-reporter] WARNING: trace copy failed: {e}", file=sys.stderr)

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

        if self._screenshot_mode == "on_failure" and last_step.status not in ("failed", "error"):
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
        self._collect_traces()
        self._run_data.total_tokens = _aggregate_tokens(self._run_data)

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


_TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cache_creation",
    "cache_read",
    "reasoning",
)


def _aggregate_tokens(run_data: RunData) -> dict | None:
    """Sum per-step token usage across the whole run. Returns None if no metrics were captured."""
    total = {key: 0 for key in _TOKEN_KEYS}
    seen = False
    for feature in run_data.features:
        for scenario in feature.scenarios:
            for step in scenario.steps:
                if step.tokens:
                    seen = True
                    for key in _TOKEN_KEYS:
                        total[key] += int(step.tokens.get(key, 0))
    return total if seen else None


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
            elif scenario.status in ("failed", "error"):
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
