from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from devgodzilla.windmill.client import JobStatus
from tests.e2e.harness.live_cli import (
    _build_cli_env,
    _build_windmill_client,
    _checkout_and_update_branch,
    _desired_feature_cycles,
    _parse_json_output,
    _stage_log_file,
    _stage_protocol_feature_cycles,
    _stage_project_onboard,
    _stage_project_onboard_windmill,
    _wait_for_windmill_job,
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
        def close(self):
            return None

    monkeypatch.setattr(
        "tests.e2e.harness.live_cli._wait_for_windmill_job",
        lambda **_kwargs: type("_Job", (), {"status": JobStatus.COMPLETED, "error": None, "result": None})(),
    )
    monkeypatch.setattr("tests.e2e.harness.live_cli._build_windmill_client", lambda _env: _FakeClient())

    result = _stage_project_onboard_windmill(ctx, scenario, "project_onboard_windmill")
    assert result["windmill_job_id"] == "job-123"
    assert result["windmill_status"] == "completed"


def test_stage_project_onboard_windmill_surfaces_payload_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
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
        lambda *args, **kwargs: {"success": True, "windmill_job_id": "job-err"},
    )

    class _FakeClient:
        def close(self):
            return None

    monkeypatch.setattr(
        "tests.e2e.harness.live_cli._wait_for_windmill_job",
        lambda **_kwargs: type(
            "_Job",
            (),
            {
                "status": JobStatus.COMPLETED,
                "error": None,
                "result": {"success": False, "error": "Project not found"},
            },
        )(),
    )
    monkeypatch.setattr("tests.e2e.harness.live_cli._build_windmill_client", lambda _env: _FakeClient())

    with pytest.raises(RuntimeError, match="payload reported failure"):
        _stage_project_onboard_windmill(ctx, scenario, "project_onboard_windmill")


def test_stage_project_onboard_windmill_accepts_payload_local_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    payload_root = tmp_path / "payload-repo"
    discovery_md = payload_root / "specs" / "discovery" / "_runtime" / "DISCOVERY.md"
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
        lambda *args, **kwargs: {"success": True, "windmill_job_id": "job-ok"},
    )

    class _FakeClient:
        def close(self):
            return None

    monkeypatch.setattr(
        "tests.e2e.harness.live_cli._wait_for_windmill_job",
        lambda **_kwargs: type(
            "_Job",
            (),
            {
                "status": JobStatus.COMPLETED,
                "error": None,
                "result": {
                    "success": True,
                    "local_path": str(payload_root),
                    "discovery_success": True,
                },
            },
        )(),
    )
    monkeypatch.setattr("tests.e2e.harness.live_cli._build_windmill_client", lambda _env: _FakeClient())

    result = _stage_project_onboard_windmill(ctx, scenario, "project_onboard_windmill")
    assert result["repo_root"] == str(payload_root)
    assert ctx.metadata["repo_root"] == str(payload_root)


def test_stage_log_file_uses_attempt_metadata(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    ctx = HarnessRunContext(
        scenario_id="logging",
        run_dir=run_dir,
        diagnostics_dir=run_dir / "diagnostics",
        metadata={"_current_attempt": 3},
    )
    path = _stage_log_file(ctx, "protocol_plan", "protocol-plan")
    assert "protocol_plan" in path.name
    assert "attempt-3" in path.name
    assert path.parent == ctx.diagnostics_dir


def test_parse_json_output_accepts_last_json_line() -> None:
    payload = _parse_json_output("noise\n{\"success\": true, \"id\": 5}\n")
    assert payload["success"] is True
    assert payload["id"] == 5


def test_checkout_and_update_branch_falls_back_to_origin_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, ...]] = []

    def _fake_run_git(*args: str, cwd: Path, env: dict[str, str], timeout: int = 60) -> str:
        del cwd, env, timeout
        calls.append(args)
        if args == ("checkout", "main"):
            raise RuntimeError("pathspec main not found")
        if args == ("symbolic-ref", "--short", "refs/remotes/origin/HEAD"):
            return "origin/master"
        return ""

    monkeypatch.setattr("tests.e2e.harness.live_cli._run_git", _fake_run_git)

    branch = _checkout_and_update_branch(tmp_path, {}, "main")
    assert branch == "master"
    assert ("checkout", "main") in calls
    assert ("checkout", "master") in calls


def test_build_cli_env_injects_windmill_from_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "tests.e2e.harness.live_cli.load_config",
        lambda: SimpleNamespace(
            windmill_url="http://localhost:8001",
            windmill_token="abc123",
            windmill_workspace="demo1",
            windmill_env_file=None,
        ),
    )

    env = _build_cli_env(tmp_path / "run")
    assert env["DEVGODZILLA_WINDMILL_TOKEN"] == "abc123"
    assert env["DEVGODZILLA_WINDMILL_URL"] == "http://localhost:8001"


def test_build_cli_env_honors_preconfigured_db_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DEVGODZILLA_DB_PATH", "/tmp/shared-harness.sqlite")
    monkeypatch.setattr(
        "tests.e2e.harness.live_cli.load_config",
        lambda: SimpleNamespace(
            windmill_url=None,
            windmill_token=None,
            windmill_workspace=None,
            windmill_env_file=None,
        ),
    )

    env = _build_cli_env(tmp_path / "run")
    assert env["DEVGODZILLA_DB_PATH"] == "/tmp/shared-harness.sqlite"


def test_build_windmill_client_uses_config_token_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tests.e2e.harness.live_cli.load_config",
        lambda: SimpleNamespace(
            windmill_url="http://localhost:8001",
            windmill_token="fallback-token",
            windmill_workspace="demo1",
            windmill_env_file=None,
        ),
    )

    client = _build_windmill_client({})
    assert client.config.token == "fallback-token"
    client.close()


def test_wait_for_windmill_job_streams_logs(tmp_path: Path) -> None:
    log_file = tmp_path / "windmill.log"

    class _FakeClient:
        def __init__(self) -> None:
            self.calls = 0

        def get_job(self, _job_id: str):
            self.calls += 1
            status = JobStatus.RUNNING if self.calls == 1 else JobStatus.COMPLETED
            return type("_Job", (), {"status": status, "error": None, "result": None})()

        def get_job_logs(self, _job_id: str) -> str:
            if self.calls == 1:
                return "line-1\n"
            return "line-1\nline-2\n"

    job = _wait_for_windmill_job(
        client=_FakeClient(),
        job_id="job-1",
        timeout_seconds=5,
        poll_interval_seconds=0.01,
        log_file=log_file,
        heartbeat_timeout_seconds=0,
    )

    content = log_file.read_text(encoding="utf-8")
    assert job.status == JobStatus.COMPLETED
    assert "line-1" in content
    assert "line-2" in content


def test_desired_feature_cycles_defaults_and_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HARNESS_FEATURE_CYCLES", raising=False)
    assert _desired_feature_cycles() == 2

    monkeypatch.setenv("HARNESS_FEATURE_CYCLES", "3")
    assert _desired_feature_cycles() == 3

    monkeypatch.setenv("HARNESS_FEATURE_CYCLES", "0")
    assert _desired_feature_cycles() == 1

    monkeypatch.setenv("HARNESS_FEATURE_CYCLES", "bad")
    with pytest.raises(RuntimeError, match="HARNESS_FEATURE_CYCLES"):
        _desired_feature_cycles()


def test_stage_protocol_feature_cycles_runs_multiple_cycles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ctx = HarnessRunContext(
        scenario_id="feature-cycles",
        run_dir=tmp_path / "run",
        diagnostics_dir=tmp_path / "run" / "diagnostics",
        metadata={},
    )
    scenario = _scenario(["specs/discovery/_runtime/DISCOVERY.md"])
    monkeypatch.setenv("HARNESS_FEATURE_CYCLES", "3")

    calls: list[tuple[str, str]] = []

    def _fake_create(_ctx: HarnessRunContext, _scenario: ScenarioConfig, stage: str) -> dict[str, object]:
        cycle = int(_ctx.metadata["_protocol_cycle_index"]) + 1
        _ctx.metadata["protocol_id"] = cycle * 100
        _ctx.metadata["protocol_name"] = f"proto-{cycle}"
        calls.append(("create", stage))
        return {"protocol_run_id": cycle * 100}

    def _fake_worktree(_ctx: HarnessRunContext, _scenario: ScenarioConfig, stage: str) -> dict[str, object]:
        cycle = int(_ctx.metadata["_protocol_cycle_index"]) + 1
        calls.append(("worktree", stage))
        return {"worktree_path": f"/tmp/wt-{cycle}"}

    def _fake_plan(_ctx: HarnessRunContext, _scenario: ScenarioConfig, stage: str) -> dict[str, object]:
        cycle = int(_ctx.metadata["_protocol_cycle_index"]) + 1
        calls.append(("plan", stage))
        return {"steps_created": cycle}

    def _fake_execute(_ctx: HarnessRunContext, _scenario: ScenarioConfig, stage: str) -> dict[str, object]:
        cycle = int(_ctx.metadata["_protocol_cycle_index"]) + 1
        calls.append(("execute", stage))
        return {
            "executed_steps": cycle,
            "protocol_status": "completed",
            "protocol_root": f"/tmp/proto-{cycle}",
        }

    monkeypatch.setattr("tests.e2e.harness.live_cli._stage_protocol_create", _fake_create)
    monkeypatch.setattr("tests.e2e.harness.live_cli._stage_protocol_worktree", _fake_worktree)
    monkeypatch.setattr("tests.e2e.harness.live_cli._stage_protocol_plan", _fake_plan)
    monkeypatch.setattr("tests.e2e.harness.live_cli._stage_step_execute", _fake_execute)

    result = _stage_protocol_feature_cycles(ctx, scenario, "protocol_feature_cycles")
    assert result["feature_cycles"] == 3
    assert result["total_steps_created"] == 6
    assert result["total_executed_steps"] == 6
    assert len(result["cycles"]) == 3
    assert calls[0][1] == "protocol_feature_cycles-cycle-1-protocol_create"
    assert calls[-1][1] == "protocol_feature_cycles-cycle-3-step_execute"
