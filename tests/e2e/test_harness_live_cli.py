from __future__ import annotations

from pathlib import Path

import pytest

from devgodzilla.windmill.client import JobStatus
from tests.e2e.harness.live_cli import (
    _stage_project_onboard,
    _stage_project_onboard_windmill,
)
from tests.e2e.harness.runner import HarnessRunContext
from tests.e2e.harness.scenario_loader import RepoConfig, RetryConfig, ScenarioConfig, TimeoutConfig


def _scenario(discovery_outputs: list[str]) -> ScenarioConfig:
    return ScenarioConfig(
        scenario_id="live-cli-test",
        source="github_user_allowlist",
        repo=RepoConfig(
            owner="ilyafedotov-ops",
            name="demo",
            url="https://github.com/ilyafedotov-ops/demo.git",
            default_branch="main",
        ),
        adapter_id="demo",
        workflow_stages=["project_onboard_windmill"],
        discovery_outputs=discovery_outputs,
        min_protocol_steps=1,
        terminal_protocol_status="completed",
        artifact_patterns=[],
        retries=RetryConfig(max_attempts=1, backoff_seconds=0, max_backoff_seconds=0),
        timeouts=TimeoutConfig(onboard_seconds=30, planning_seconds=30, execution_seconds=30),
        raw={},
    )


def test_stage_project_onboard_switches_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ctx = HarnessRunContext(
        scenario_id="switch-mode",
        run_dir=tmp_path / "run",
        diagnostics_dir=tmp_path / "run" / "diagnostics",
        metadata={},
    )
    scenario = _scenario(["specs/discovery/_runtime/DISCOVERY.md"])

    monkeypatch.setattr(
        "tests.e2e.harness.live_cli._stage_project_onboard_agent",
        lambda *_args, **_kwargs: {"mode": "agent"},
    )
    monkeypatch.setattr(
        "tests.e2e.harness.live_cli._stage_project_onboard_windmill",
        lambda *_args, **_kwargs: {"mode": "windmill"},
    )

    monkeypatch.setenv("HARNESS_ONBOARD_MODE", "agent")
    assert _stage_project_onboard(ctx, scenario, "project_onboard")["mode"] == "agent"

    monkeypatch.setenv("HARNESS_ONBOARD_MODE", "windmill")
    assert _stage_project_onboard(ctx, scenario, "project_onboard")["mode"] == "windmill"


def test_stage_project_onboard_windmill_waits_for_job(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    discovery_md = repo_root / "specs" / "discovery" / "_runtime" / "DISCOVERY.md"
    discovery_md.parent.mkdir(parents=True, exist_ok=True)
    discovery_md.write_text("# discovery", encoding="utf-8")

    run_dir = tmp_path / "run"
    ctx = HarnessRunContext(
        scenario_id="windmill",
        run_dir=run_dir,
        diagnostics_dir=run_dir / "diagnostics",
        metadata={
            "project_id": 9,
            "env": {
                "DEVGODZILLA_WINDMILL_URL": "http://localhost:8001",
                "DEVGODZILLA_WINDMILL_TOKEN": "token",
                "DEVGODZILLA_WINDMILL_WORKSPACE": "demo1",
            },
            "repo_root": str(repo_root),
            "base_branch": "main",
        },
    )
    scenario = _scenario(["specs/discovery/_runtime/DISCOVERY.md"])

    monkeypatch.setattr(
        "tests.e2e.harness.live_cli._run_cli",
        lambda *args, **kwargs: {
            "success": True,
            "windmill_job_id": "job-123",
        },
    )

    class _FakeClient:
        def wait_for_job(self, job_id: str, timeout: float, poll_interval: float):
            return type("_Job", (), {"status": JobStatus.COMPLETED, "error": None})()

        def close(self):
            return None

    monkeypatch.setattr("tests.e2e.harness.live_cli._build_windmill_client", lambda _env: _FakeClient())

    result = _stage_project_onboard_windmill(ctx, scenario, "project_onboard_windmill")
    assert result["windmill_job_id"] == "job-123"
    assert result["windmill_status"] == "completed"
