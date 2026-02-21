from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from .assertions import write_diagnostic_file
from .scenario_loader import ScenarioConfig

StageHandler = Callable[["HarnessRunContext", ScenarioConfig, str], dict[str, Any] | None]
SleepFn = Callable[[float], None]
ClockFn = Callable[[], float]
EventEmitter = Callable[[str, dict[str, Any]], None]


@dataclass
class HarnessRunContext:
    scenario_id: str
    run_dir: Path
    diagnostics_dir: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageResult:
    stage: str
    status: str
    attempts: int
    duration_ms: int
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class HarnessRunResult:
    scenario_id: str
    run_dir: Path
    diagnostics_dir: Path
    status: str
    started_at: str
    finished_at: str
    stages: list[StageResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status == "passed"


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def _make_run_dir(run_root: Path, scenario_id: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = run_root / f"{stamp}-{scenario_id}"
    (run_dir / "diagnostics").mkdir(parents=True, exist_ok=True)
    return run_dir


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return {key: _json_safe(getattr(value, key)) for key in value.__dataclass_fields__}
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def _append_event(diagnostics_dir: Path, event_type: str, payload: dict[str, Any]) -> None:
    event = {
        "ts": _now_utc(),
        "event_type": event_type,
        **payload,
    }
    path = diagnostics_dir / "events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_json_safe(event), sort_keys=True))
        handle.write("\n")


def _execute_stage_with_retries(
    handler: StageHandler,
    ctx: HarnessRunContext,
    scenario: ScenarioConfig,
    stage: str,
    *,
    sleep_fn: SleepFn,
    clock_fn: ClockFn,
    emit_event: EventEmitter,
) -> StageResult:
    start = clock_fn()
    attempts = 0
    error_message: str | None = None
    details: dict[str, Any] = {}

    for attempt in range(1, scenario.retries.max_attempts + 1):
        attempts = attempt
        ctx.metadata["_current_stage"] = stage
        ctx.metadata["_current_attempt"] = attempt
        emit_event(
            "stage_started",
            {
                "scenario_id": scenario.scenario_id,
                "stage": stage,
                "attempt": attempt,
                "max_attempts": scenario.retries.max_attempts,
            },
        )
        try:
            result = handler(ctx, scenario, stage)
            if result:
                details = result
            duration_ms = int((clock_fn() - start) * 1000)
            emit_event(
                "stage_succeeded",
                {
                    "scenario_id": scenario.scenario_id,
                    "stage": stage,
                    "attempt": attempt,
                    "duration_ms": duration_ms,
                    "details": details,
                },
            )
            return StageResult(
                stage=stage,
                status="passed",
                attempts=attempts,
                duration_ms=duration_ms,
                details=details,
            )
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            if attempt >= scenario.retries.max_attempts:
                break
            delay = min(
                scenario.retries.backoff_seconds * (2 ** (attempt - 1)),
                scenario.retries.max_backoff_seconds,
            )
            emit_event(
                "stage_retry",
                {
                    "scenario_id": scenario.scenario_id,
                    "stage": stage,
                    "attempt": attempt,
                    "next_attempt": attempt + 1,
                    "delay_seconds": delay,
                    "error": error_message,
                },
            )
            sleep_fn(delay)
        finally:
            ctx.metadata.pop("_current_stage", None)
            ctx.metadata.pop("_current_attempt", None)

    duration_ms = int((clock_fn() - start) * 1000)
    emit_event(
        "stage_failed",
        {
            "scenario_id": scenario.scenario_id,
            "stage": stage,
            "attempts": attempts,
            "duration_ms": duration_ms,
            "error": error_message or "unknown stage error",
        },
    )
    return StageResult(
        stage=stage,
        status="failed",
        attempts=attempts,
        duration_ms=duration_ms,
        error=error_message or "unknown stage error",
    )


def run_scenario(
    scenario: ScenarioConfig,
    stage_handlers: Mapping[str, StageHandler],
    *,
    run_root: Path | None = None,
    continue_on_error: bool = False,
    sleep_fn: SleepFn = time.sleep,
    clock_fn: ClockFn = time.monotonic,
) -> HarnessRunResult:
    base = run_root or (Path("runs") / "harness")
    run_dir = _make_run_dir(base, scenario.scenario_id)
    diagnostics_dir = run_dir / "diagnostics"
    ctx = HarnessRunContext(
        scenario_id=scenario.scenario_id,
        run_dir=run_dir,
        diagnostics_dir=diagnostics_dir,
    )

    started_at = _now_utc()
    _append_event(
        diagnostics_dir,
        "run_started",
        {
            "scenario_id": scenario.scenario_id,
            "started_at": started_at,
            "workflow_stages": list(scenario.workflow_stages),
            "continue_on_error": continue_on_error,
        },
    )
    stage_results: list[StageResult] = []
    run_status = "passed"

    for stage in scenario.workflow_stages:
        handler = stage_handlers.get(stage)
        if handler is None:
            stage_result = StageResult(
                stage=stage,
                status="failed",
                attempts=0,
                duration_ms=0,
                error=f"No stage handler registered for '{stage}'",
            )
        else:
            stage_result = _execute_stage_with_retries(
                handler,
                ctx,
                scenario,
                stage,
                sleep_fn=sleep_fn,
                clock_fn=clock_fn,
                emit_event=lambda event_type, payload: _append_event(
                    diagnostics_dir,
                    event_type,
                    payload,
                ),
            )

        stage_results.append(stage_result)
        if stage_result.status != "passed":
            run_status = "failed"
            if handler is None:
                _append_event(
                    diagnostics_dir,
                    "stage_failed",
                    {
                        "scenario_id": scenario.scenario_id,
                        "stage": stage_result.stage,
                        "attempts": stage_result.attempts,
                        "duration_ms": stage_result.duration_ms,
                        "error": stage_result.error,
                        "reason": "missing_handler",
                    },
                )
            write_diagnostic_file(
                run_dir,
                f"stage-{stage}-failure",
                {
                    "scenario_id": scenario.scenario_id,
                    "stage": stage_result.stage,
                    "error": stage_result.error,
                    "attempts": stage_result.attempts,
                },
            )
            if not continue_on_error:
                break

    result = HarnessRunResult(
        scenario_id=scenario.scenario_id,
        run_dir=run_dir,
        diagnostics_dir=diagnostics_dir,
        status=run_status,
        started_at=started_at,
        finished_at=_now_utc(),
        stages=stage_results,
    )
    _append_event(
        diagnostics_dir,
        "run_finished",
        {
            "scenario_id": scenario.scenario_id,
            "status": result.status,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "stages_executed": len(result.stages),
            "failed_stages": [stage.stage for stage in result.stages if stage.status != "passed"],
        },
    )
    write_diagnostic_file(run_dir, "run-summary", result)
    return result
