from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.harness.runner import run_scenario
from tests.e2e.harness.scenario_loader import RepoConfig, RetryConfig, ScenarioConfig, TimeoutConfig


def _scenario(stages: list[str]) -> ScenarioConfig:
    return ScenarioConfig(
        scenario_id="runner-test",
        source="github_user_allowlist",
        repo=RepoConfig(
            owner="ilyafedotov-ops",
            name="demo",
            url="https://github.com/ilyafedotov-ops/demo.git",
            default_branch="main",
        ),
        adapter_id="demo",
        workflow_stages=stages,
        discovery_outputs=["specs/discovery/_runtime/DISCOVERY.md"],
        min_protocol_steps=2,
        terminal_protocol_status="completed",
        artifact_patterns=[],
        retries=RetryConfig(max_attempts=3, backoff_seconds=0.0, max_backoff_seconds=0.0),
        timeouts=TimeoutConfig(onboard_seconds=10, planning_seconds=10, execution_seconds=10),
        raw={},
    )


def test_run_scenario_success(tmp_path: Path) -> None:
    scenario = _scenario(["a", "b"])

    handlers = {
        "a": lambda ctx, scn, stage: {"ok": stage},
        "b": lambda ctx, scn, stage: {"ok": stage},
    }

    result = run_scenario(scenario, handlers, run_root=tmp_path)
    assert result.success
    assert [stage.status for stage in result.stages] == ["passed", "passed"]
    events_path = result.diagnostics_dir / "events.jsonl"
    assert events_path.exists()
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    event_types = [event["event_type"] for event in events]
    assert event_types[0] == "run_started"
    assert event_types[-1] == "run_finished"
    assert "stage_succeeded" in event_types


def test_run_scenario_retry_then_success(tmp_path: Path) -> None:
    scenario = _scenario(["retry"])
    calls = {"count": 0}

    def _handler(ctx, scn, stage):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("transient")
        return {"attempt": calls["count"]}

    result = run_scenario(scenario, {"retry": _handler}, run_root=tmp_path)
    assert result.success
    assert result.stages[0].attempts == 2
    events_path = result.diagnostics_dir / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    retry_events = [event for event in events if event["event_type"] == "stage_retry"]
    assert retry_events
    assert retry_events[0]["stage"] == "retry"


def test_run_scenario_missing_handler_fails(tmp_path: Path) -> None:
    scenario = _scenario(["missing"])
    result = run_scenario(scenario, {}, run_root=tmp_path)

    assert not result.success
    assert result.stages[0].status == "failed"
    diag = result.diagnostics_dir / "stage-missing-failure.json"
    assert diag.exists()
    events_path = result.diagnostics_dir / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(event["event_type"] == "stage_failed" and event["stage"] == "missing" for event in events)


def test_run_scenario_allows_stage_handlers_to_emit_custom_events(tmp_path: Path) -> None:
    scenario = _scenario(["emit"])

    def _handler(ctx, scn, stage):
        del scn, stage
        assert ctx.event_emitter is not None
        ctx.event_emitter(
            "custom_event",
            {
                "scenario_id": ctx.scenario_id,
                "stage": "emit",
                "note": "from-handler",
            },
        )
        return {"ok": True}

    result = run_scenario(scenario, {"emit": _handler}, run_root=tmp_path)
    assert result.success
    events_path = result.diagnostics_dir / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(event["event_type"] == "custom_event" and event["note"] == "from-handler" for event in events)


def test_run_scenario_writes_partial_summary_on_interrupt(tmp_path: Path) -> None:
    scenario = _scenario(["ok", "boom"])

    def _ok(ctx, scn, stage):
        del ctx, scn, stage
        return {"ok": True}

    def _boom(ctx, scn, stage):
        del ctx, scn, stage
        raise KeyboardInterrupt("stop-now")

    with pytest.raises(KeyboardInterrupt, match="stop-now"):
        run_scenario(scenario, {"ok": _ok, "boom": _boom}, run_root=tmp_path)

    run_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    summary_path = run_dir / "diagnostics" / "run-summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "interrupted"
    assert [stage["stage"] for stage in summary["stages"]] == ["ok"]

    events_path = run_dir / "diagnostics" / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(event["event_type"] == "run_interrupted" and event["stage"] == "boom" for event in events)
