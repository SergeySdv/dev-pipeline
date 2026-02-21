from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from devgodzilla.db.database import SQLiteDatabase
from devgodzilla.windmill.client import JobStatus, WindmillClient, WindmillConfig

from .assertions import (
    assert_glob_matches,
    assert_paths_exist,
    assert_protocol_terminal_status,
)
from .runner import HarnessRunContext, StageHandler
from .scenario_loader import ScenarioConfig

REPO_ROOT = Path(__file__).resolve().parents[3]


def _run_cli(*args: str, cwd: Path, env: dict[str, str], timeout: int) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "devgodzilla.cli.main", "--json", *args]
    proc = subprocess.run(  # noqa: S603
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "CLI command failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"cwd: {cwd}\n"
            f"exit_code: {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )
    return json.loads(proc.stdout)


def _run_git(*args: str, cwd: Path, env: dict[str, str], timeout: int = 60) -> str:
    proc = subprocess.run(  # noqa: S603
        ["git", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {cwd}:\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return (proc.stdout or "").strip()


def _workspace_root() -> Path:
    default = REPO_ROOT / "projects" / "harness-cache"
    root = Path(os.environ.get("HARNESS_WORKSPACE_ROOT", str(default))).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_cli_env(run_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    db_path = run_dir / "harness.sqlite"
    env.setdefault("PYTHONPATH", str(REPO_ROOT))
    env["DEVGODZILLA_ENV"] = "test"
    env["DEVGODZILLA_DB_PATH"] = str(db_path)
    env.setdefault("DEVGODZILLA_DEFAULT_ENGINE_ID", "opencode")
    env.setdefault("DEVGODZILLA_OPENCODE_MODEL", "zai-coding-plan/glm-5")
    return env


def _stage_project_create(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    del stage
    env = _build_cli_env(ctx.run_dir)

    checkout_root = _workspace_root() / scenario.repo.owner / scenario.repo.name
    checkout_root.parent.mkdir(parents=True, exist_ok=True)

    if (checkout_root / ".git").exists():
        _run_git("fetch", "--all", "--prune", cwd=checkout_root, env=env)
        _run_git("checkout", scenario.repo.default_branch, cwd=checkout_root, env=env)
        _run_git("pull", "--ff-only", "origin", scenario.repo.default_branch, cwd=checkout_root, env=env)
    else:
        _run_git("clone", "--depth", "1", scenario.repo.url, str(checkout_root), cwd=checkout_root.parent, env=env)

    base_branch = _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=checkout_root, env=env)
    project_name = f"{scenario.scenario_id}-{int(time.time())}"
    created = _run_cli(
        "project",
        "create",
        project_name,
        "--repo",
        scenario.repo.url,
        "--branch",
        base_branch,
        "--local-path",
        str(checkout_root),
        "--no-onboard",
        cwd=REPO_ROOT,
        env=env,
        timeout=scenario.timeouts.onboard_seconds,
    )

    if not created.get("success"):
        raise RuntimeError(f"Project creation returned failure payload: {created}")

    ctx.metadata.update(
        {
            "env": env,
            "repo_root": str(checkout_root),
            "base_branch": base_branch,
            "project_id": int(created["project_id"]),
            "project_name": project_name,
        }
    )
    return {"project_id": created["project_id"], "repo_root": str(checkout_root), "base_branch": base_branch}


def _require_metadata(ctx: HarnessRunContext, *keys: str) -> None:
    missing = [key for key in keys if key not in ctx.metadata]
    if missing:
        raise RuntimeError(f"Missing context metadata keys: {', '.join(missing)}")


def _build_windmill_client(env: dict[str, str]) -> WindmillClient:
    config = WindmillConfig(
        base_url=env.get("DEVGODZILLA_WINDMILL_URL", "http://localhost:8001"),
        token=env.get("DEVGODZILLA_WINDMILL_TOKEN", ""),
        workspace=env.get("DEVGODZILLA_WINDMILL_WORKSPACE", "demo1"),
        timeout=float(env.get("DEVGODZILLA_WINDMILL_TIMEOUT", "30")),
        max_retries=int(env.get("DEVGODZILLA_WINDMILL_MAX_RETRIES", "3")),
        backoff_base_seconds=float(env.get("DEVGODZILLA_WINDMILL_BACKOFF_BASE_SECONDS", "0.5")),
        backoff_max_seconds=float(env.get("DEVGODZILLA_WINDMILL_BACKOFF_MAX_SECONDS", "5.0")),
    )
    return WindmillClient(config)


def _stage_project_onboard_agent(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    del stage
    _require_metadata(ctx, "project_id", "env", "repo_root")

    env = ctx.metadata["env"]
    project_id = int(ctx.metadata["project_id"])
    repo_root = Path(ctx.metadata["repo_root"])

    model = os.environ.get("HARNESS_DISCOVERY_MODEL", env.get("DEVGODZILLA_OPENCODE_MODEL", "zai-coding-plan/glm-5"))
    discover = _run_cli(
        "project",
        "discover",
        str(project_id),
        "--agent",
        "--pipeline",
        "--engine",
        "opencode",
        "--model",
        model,
        cwd=REPO_ROOT,
        env=env,
        timeout=scenario.timeouts.onboard_seconds,
    )
    if not discover.get("success"):
        raise RuntimeError(f"Discovery failed payload: {discover}")

    assert_paths_exist(repo_root, scenario.discovery_outputs)
    return {
        "discovery_engine": discover.get("engine_id"),
        "discovery_model": discover.get("model"),
        "onboard_mode": "agent",
    }


def _stage_project_onboard_windmill(
    ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str
) -> dict[str, Any]:
    del stage
    _require_metadata(ctx, "project_id", "env", "repo_root", "base_branch")

    env = ctx.metadata["env"]
    project_id = int(ctx.metadata["project_id"])
    repo_root = Path(ctx.metadata["repo_root"])
    base_branch = str(ctx.metadata["base_branch"])

    onboarded = _run_cli(
        "project",
        "onboard",
        str(project_id),
        "--branch",
        base_branch,
        cwd=REPO_ROOT,
        env=env,
        timeout=scenario.timeouts.onboard_seconds,
    )
    if not onboarded.get("success"):
        raise RuntimeError(f"Windmill onboarding enqueue failed: {onboarded}")

    job_id = str(onboarded.get("windmill_job_id") or "")
    if not job_id:
        raise RuntimeError(f"Missing windmill_job_id in onboard payload: {onboarded}")

    poll_interval = float(os.environ.get("HARNESS_WINDMILL_POLL_INTERVAL", "2.0"))
    client = _build_windmill_client(env)
    try:
        final_job = client.wait_for_job(
            job_id,
            timeout=float(scenario.timeouts.onboard_seconds),
            poll_interval=poll_interval,
        )
        if final_job.status != JobStatus.COMPLETED:
            logs = ""
            try:
                logs = client.get_job_logs(job_id)[:5000]
            except Exception:
                logs = ""
            raise RuntimeError(
                f"Windmill onboarding job failed: id={job_id} status={final_job.status} error={final_job.error} logs={logs}"
            )
    finally:
        client.close()

    assert_paths_exist(repo_root, scenario.discovery_outputs)
    return {
        "windmill_job_id": job_id,
        "onboard_mode": "windmill",
        "windmill_status": final_job.status.value,
    }


def _stage_project_onboard(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    mode = os.environ.get("HARNESS_ONBOARD_MODE", "windmill").strip().lower()
    if mode == "agent":
        return _stage_project_onboard_agent(ctx, scenario, stage)
    return _stage_project_onboard_windmill(ctx, scenario, stage)


def _stage_protocol_create(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    del stage
    _require_metadata(ctx, "project_id", "env", "base_branch")

    env = ctx.metadata["env"]
    project_id = int(ctx.metadata["project_id"])
    base_branch = str(ctx.metadata["base_branch"])
    protocol_name = f"{scenario.scenario_id}-protocol"

    proto = _run_cli(
        "protocol",
        "create",
        str(project_id),
        protocol_name,
        "--description",
        f"Harness protocol for {scenario.scenario_id}",
        "--branch",
        base_branch,
        cwd=REPO_ROOT,
        env=env,
        timeout=scenario.timeouts.planning_seconds,
    )

    if not proto.get("success"):
        raise RuntimeError(f"Protocol create failed payload: {proto}")

    protocol_id = int(proto["protocol_run_id"])
    ctx.metadata.update({"protocol_id": protocol_id, "protocol_name": protocol_name})
    return {"protocol_run_id": protocol_id}


def _stage_protocol_worktree(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    del scenario, stage
    _require_metadata(ctx, "protocol_id", "env")

    env = ctx.metadata["env"]
    protocol_id = int(ctx.metadata["protocol_id"])
    worktree = _run_cli(
        "protocol",
        "worktree",
        str(protocol_id),
        cwd=REPO_ROOT,
        env=env,
        timeout=240,
    )
    if not worktree.get("success"):
        raise RuntimeError(f"Protocol worktree failed payload: {worktree}")

    worktree_path = Path(worktree["worktree_path"])
    if not worktree_path.exists():
        raise RuntimeError(f"Worktree path does not exist: {worktree_path}")

    ctx.metadata["worktree_path"] = str(worktree_path)
    return {"worktree_path": str(worktree_path), "branch": worktree.get("branch")}


def _stage_protocol_plan(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    del stage
    _require_metadata(ctx, "protocol_id", "env")

    env = ctx.metadata["env"]
    protocol_id = int(ctx.metadata["protocol_id"])
    planned = _run_cli(
        "protocol",
        "plan",
        str(protocol_id),
        cwd=REPO_ROOT,
        env=env,
        timeout=scenario.timeouts.planning_seconds,
    )
    if not planned.get("success"):
        raise RuntimeError(f"Protocol plan failed payload: {planned}")

    steps_created = int(planned.get("steps_created") or 0)
    if steps_created < scenario.min_protocol_steps:
        raise RuntimeError(
            f"Expected at least {scenario.min_protocol_steps} planned steps, got {steps_created}"
        )

    return {"steps_created": steps_created}


def _stage_step_execute(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    del stage
    _require_metadata(ctx, "protocol_id", "env")

    env = ctx.metadata["env"]
    protocol_id = int(ctx.metadata["protocol_id"])
    db = SQLiteDatabase(Path(env["DEVGODZILLA_DB_PATH"]))
    db.init_schema()

    step_runs = db.list_step_runs(protocol_id)
    if not step_runs:
        raise RuntimeError(f"No step runs found for protocol {protocol_id}")

    step_engine = os.environ.get("HARNESS_STEP_ENGINE", "opencode").strip() or "opencode"

    for step in step_runs:
        executed = _run_cli(
            "step",
            "execute",
            str(step.id),
            "--engine",
            step_engine,
            cwd=REPO_ROOT,
            env=env,
            timeout=scenario.timeouts.execution_seconds,
        )
        if not executed.get("success"):
            raise RuntimeError(f"Step execution failed for step {step.id}: {executed}")

    protocol = db.get_protocol_run(protocol_id)
    if scenario.terminal_protocol_status and os.environ.get("HARNESS_ASSERT_TERMINAL_STATUS", "0") == "1":
        assert_protocol_terminal_status(protocol.status, expected=scenario.terminal_protocol_status)

    protocol_root = Path(protocol.protocol_root) if protocol.protocol_root else None
    if protocol_root and protocol_root.exists():
        for pattern in scenario.artifact_patterns:
            assert_glob_matches(protocol_root, pattern, min_matches=1)

    return {
        "executed_steps": len(step_runs),
        "engine": step_engine,
        "protocol_status": protocol.status,
        "protocol_root": str(protocol_root) if protocol_root else None,
    }


def build_live_cli_stage_handlers() -> dict[str, StageHandler]:
    return {
        "project_create": _stage_project_create,
        "project_onboard": _stage_project_onboard,
        "project_onboard_agent": _stage_project_onboard_agent,
        "project_onboard_windmill": _stage_project_onboard_windmill,
        "protocol_create": _stage_protocol_create,
        "protocol_worktree": _stage_protocol_worktree,
        "protocol_plan": _stage_protocol_plan,
        "step_execute": _stage_step_execute,
    }
