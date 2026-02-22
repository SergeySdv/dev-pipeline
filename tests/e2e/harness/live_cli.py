from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from devgodzilla.config import load_config
from devgodzilla.db.database import get_database
from devgodzilla.windmill.client import JobStatus, WindmillClient, WindmillConfig

from .assertions import (
    assert_glob_matches,
    assert_paths_exist,
    assert_protocol_terminal_status,
    write_diagnostic_file,
)
from .runner import HarnessRunContext, StageHandler
from .scenario_loader import ScenarioConfig

REPO_ROOT = Path(__file__).resolve().parents[3]
ProgressCallback = Callable[[Any], None]


def _run_cli(
    *args: str,
    cwd: Path,
    env: dict[str, str],
    timeout: int,
    log_file: Path | None = None,
) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "devgodzilla.cli.main", "--json", *args]
    log_handle = None
    log_lock = threading.Lock()
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_file.open("a", encoding="utf-8")
        log_handle.write(f"{datetime.now(UTC).isoformat()} meta cmd={' '.join(cmd)} cwd={cwd}\n")

    proc = subprocess.Popen(  # noqa: S603
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def _consume(stream, sink: list[str], source: str) -> None:
        for line in iter(stream.readline, ""):
            sink.append(line)
            if log_handle is not None:
                with log_lock:
                    log_handle.write(f"{datetime.now(UTC).isoformat()} {source} {line}")
                    log_handle.flush()
        stream.close()

    threads: list[threading.Thread] = []
    if proc.stdout is not None:
        thread = threading.Thread(target=_consume, args=(proc.stdout, stdout_lines, "stdout"), daemon=True)
        thread.start()
        threads.append(thread)
    if proc.stderr is not None:
        thread = threading.Thread(target=_consume, args=(proc.stderr, stderr_lines, "stderr"), daemon=True)
        thread.start()
        threads.append(thread)

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.wait()
        for thread in threads:
            thread.join(timeout=0.2)
        stdout_text = "".join(stdout_lines)
        stderr_text = "".join(stderr_lines)
        if log_handle is not None:
            log_handle.write(f"{datetime.now(UTC).isoformat()} meta timeout seconds={timeout}\n")
        raise RuntimeError(
            "CLI command timed out\n"
            f"cmd: {' '.join(cmd)}\n"
            f"cwd: {cwd}\n"
            f"timeout_seconds: {timeout}\n"
            f"log_file: {log_file}\n"
            f"stdout:\n{stdout_text}\n"
            f"stderr:\n{stderr_text}\n"
        ) from exc
    finally:
        for thread in threads:
            thread.join(timeout=0.2)
        if log_handle is not None:
            log_handle.close()

    stdout_text = "".join(stdout_lines)
    stderr_text = "".join(stderr_lines)
    if proc.returncode != 0:
        raise RuntimeError(
            "CLI command failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"cwd: {cwd}\n"
            f"exit_code: {proc.returncode}\n"
            f"log_file: {log_file}\n"
            f"stdout:\n{stdout_text}\n"
            f"stderr:\n{stderr_text}\n"
        )
    parsed = _parse_json_output(stdout_text)
    if not isinstance(parsed, dict):
        raise RuntimeError(
            "CLI command returned non-object JSON payload\n"
            f"cmd: {' '.join(cmd)}\n"
            f"log_file: {log_file}\n"
            f"stdout:\n{stdout_text}\n"
        )
    return parsed


def _parse_json_output(stdout_text: str) -> Any:
    stripped = stdout_text.strip()
    if not stripped:
        raise ValueError("CLI stdout is empty; expected JSON payload")

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    lines = [line.strip() for line in stdout_text.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"Unable to parse CLI JSON output from stdout: {stdout_text[:1000]}")


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


def _checkout_and_update_branch(repo_root: Path, env: dict[str, str], preferred_branch: str) -> str:
    try:
        _run_git("checkout", preferred_branch, cwd=repo_root, env=env)
        _run_git("pull", "--ff-only", "origin", preferred_branch, cwd=repo_root, env=env)
        return preferred_branch
    except RuntimeError as primary_error:
        try:
            symref = _run_git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=repo_root, env=env)
        except RuntimeError:
            raise primary_error

        fallback_branch = symref.split("/", 1)[1] if "/" in symref else symref
        fallback_branch = fallback_branch.strip()
        if not fallback_branch or fallback_branch == preferred_branch:
            raise primary_error

        _run_git("checkout", fallback_branch, cwd=repo_root, env=env)
        _run_git("pull", "--ff-only", "origin", fallback_branch, cwd=repo_root, env=env)
        return fallback_branch


def _workspace_root() -> Path:
    default = REPO_ROOT / "projects" / "harness-cache"
    root = Path(os.environ.get("HARNESS_WORKSPACE_ROOT", str(default))).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _stage_log_file(ctx: HarnessRunContext, stage: str, command_label: str) -> Path:
    attempt = int(ctx.metadata.get("_current_attempt", 1))
    safe_label = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in command_label)
    return ctx.diagnostics_dir / f"cli-{stage}-attempt-{attempt}-{safe_label}.log"


def _emit_ctx_event(ctx: HarnessRunContext, event_type: str, payload: dict[str, Any]) -> None:
    if ctx.event_emitter is None:
        return
    ctx.event_emitter(event_type, payload)


def _harness_api_base_url(env: dict[str, str]) -> str:
    base = (
        env.get("DEVGODZILLA_API_URL")
        or os.environ.get("HARNESS_API_BASE_URL")
        or "http://localhost:8000"
    )
    return base.rstrip("/")


def _fetch_onboarding_summary(
    *,
    api_base_url: str,
    project_id: int,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{api_base_url}/projects/{project_id}/onboarding",
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw) if raw else {}
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected onboarding summary payload type: {type(parsed).__name__}")
    return parsed


def _fetch_cli_executions(
    *,
    api_base_url: str,
    project_id: int,
    execution_type: str,
    status: str,
    limit: int = 10,
    timeout_seconds: float = 5.0,
) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "project_id": str(project_id),
            "execution_type": execution_type,
            "status": status,
            "limit": str(limit),
        }
    )
    req = urllib.request.Request(
        f"{api_base_url}/cli-executions?{query}",
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw) if raw else {}
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected CLI execution list payload type: {type(parsed).__name__}")
    executions = parsed.get("executions")
    if not isinstance(executions, list):
        return []
    return [item for item in executions if isinstance(item, dict)]


def _cancel_cli_execution(
    *,
    api_base_url: str,
    execution_id: str,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{api_base_url}/cli-executions/{execution_id}/cancel",
        headers={"Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw) if raw else {}
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected CLI execution cancel payload type: {type(parsed).__name__}")
    return parsed


def _cancel_windmill_job_on_interrupt(
    ctx: HarnessRunContext,
    *,
    client: WindmillClient,
    job_id: str,
    stage: str,
    project_id: int,
) -> None:
    try:
        client.cancel_job(job_id)
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc) or exc.__class__.__name__
        if "400" in error_message:
            windmill_status = None
            try:
                job = client.get_job(job_id)
            except Exception:
                job = None
            if job is not None:
                status_obj = getattr(job, "status", None)
                windmill_status = getattr(status_obj, "value", None) or str(status_obj or "")
                windmill_status = str(windmill_status).lower() or None
            _emit_ctx_event(
                ctx,
                "windmill_job_cancel_skipped",
                {
                    "scenario_id": ctx.scenario_id,
                    "stage": stage,
                    "project_id": project_id,
                    "windmill_job_id": job_id,
                    "windmill_status": windmill_status,
                    "reason": "queue_cancel_rejected",
                    "cancel_error": error_message,
                },
            )
            return
        _emit_ctx_event(
            ctx,
            "windmill_job_cancel_failed",
            {
                "scenario_id": ctx.scenario_id,
                "stage": stage,
                "project_id": project_id,
                "windmill_job_id": job_id,
                "error": error_message,
            },
        )
        return

    _emit_ctx_event(
        ctx,
        "windmill_job_cancelled",
        {
            "scenario_id": ctx.scenario_id,
            "stage": stage,
            "project_id": project_id,
            "windmill_job_id": job_id,
            "reason": "keyboard_interrupt",
        },
    )


def _cancel_backend_discovery_on_interrupt(
    ctx: HarnessRunContext,
    *,
    env: dict[str, str],
    project_id: int,
    stage: str,
    reason: str,
) -> None:
    api_base_url = _harness_api_base_url(env)
    try:
        executions = _fetch_cli_executions(
            api_base_url=api_base_url,
            project_id=project_id,
            execution_type="discovery",
            status="running",
        )
    except Exception as exc:  # noqa: BLE001
        _emit_ctx_event(
            ctx,
            "backend_discovery_cancel_scan_failed",
            {
                "scenario_id": ctx.scenario_id,
                "stage": stage,
                "project_id": project_id,
                "api_base_url": api_base_url,
                "reason": reason,
                "error": str(exc) or exc.__class__.__name__,
            },
        )
        return

    if not executions:
        _emit_ctx_event(
            ctx,
            "backend_discovery_cancel_skipped",
            {
                "scenario_id": ctx.scenario_id,
                "stage": stage,
                "project_id": project_id,
                "api_base_url": api_base_url,
                "reason": reason,
                "detail": "no_running_discovery_executions",
            },
        )
        return

    for execution in executions:
        execution_id = str(execution.get("execution_id") or "").strip()
        if not execution_id:
            continue
        try:
            result = _cancel_cli_execution(api_base_url=api_base_url, execution_id=execution_id)
        except Exception as exc:  # noqa: BLE001
            _emit_ctx_event(
                ctx,
                "backend_discovery_cancel_failed",
                {
                    "scenario_id": ctx.scenario_id,
                    "stage": stage,
                    "project_id": project_id,
                    "api_base_url": api_base_url,
                    "execution_id": execution_id,
                    "reason": reason,
                    "error": str(exc) or exc.__class__.__name__,
                },
            )
            continue

        _emit_ctx_event(
            ctx,
            "backend_discovery_cancelled",
            {
                "scenario_id": ctx.scenario_id,
                "stage": stage,
                "project_id": project_id,
                "api_base_url": api_base_url,
                "execution_id": execution_id,
                "reason": reason,
                "cancel_result": result.get("status"),
                "termination_result": result.get("termination_result"),
                "pid": result.get("pid"),
            },
        )


def _mirror_onboarding_progress(
    ctx: HarnessRunContext,
    *,
    env: dict[str, str],
    project_id: int,
    stage: str,
    windmill_job_id: str,
    windmill_status: str,
) -> None:
    api_base_url = _harness_api_base_url(env)
    try:
        summary = _fetch_onboarding_summary(api_base_url=api_base_url, project_id=project_id)
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc) or exc.__class__.__name__
        if ctx.metadata.get("_onboarding_progress_poll_error") != error_message:
            ctx.metadata["_onboarding_progress_poll_error"] = error_message
            _emit_ctx_event(
                ctx,
                "onboarding_progress_poll_error",
                {
                    "scenario_id": ctx.scenario_id,
                    "stage": stage,
                    "project_id": project_id,
                    "windmill_job_id": windmill_job_id,
                    "windmill_status": windmill_status,
                    "api_base_url": api_base_url,
                    "error": error_message,
                },
            )
        return

    ctx.metadata.pop("_onboarding_progress_poll_error", None)
    stages = summary.get("stages") if isinstance(summary.get("stages"), list) else []
    stages_snapshot = [
        {
            "name": str(item.get("name") or ""),
            "status": str(item.get("status") or ""),
        }
        for item in stages
        if isinstance(item, dict)
    ]
    status_snapshot = {
        "onboarding_status": str(summary.get("status") or ""),
        "stages": stages_snapshot,
    }
    if ctx.metadata.get("_onboarding_progress_snapshot") != status_snapshot:
        ctx.metadata["_onboarding_progress_snapshot"] = status_snapshot
        _emit_ctx_event(
            ctx,
            "onboarding_progress",
            {
                "scenario_id": ctx.scenario_id,
                "stage": stage,
                "project_id": project_id,
                "windmill_job_id": windmill_job_id,
                "windmill_status": windmill_status,
                "onboarding_status": status_snapshot["onboarding_status"],
                "stages": stages_snapshot,
            },
        )

    raw_events = summary.get("events") if isinstance(summary.get("events"), list) else []
    backend_events = [item for item in raw_events if isinstance(item, dict)]
    backend_events.sort(key=lambda item: int(item.get("id") or 0))
    last_seen_id = int(ctx.metadata.get("_onboarding_last_event_id") or 0)
    for item in backend_events:
        event_id = int(item.get("id") or 0)
        if event_id <= last_seen_id:
            continue
        _emit_ctx_event(
            ctx,
            "onboarding_backend_event",
            {
                "scenario_id": ctx.scenario_id,
                "stage": stage,
                "project_id": project_id,
                "windmill_job_id": windmill_job_id,
                "windmill_status": windmill_status,
                "event_id": event_id,
                "backend_event_type": str(item.get("event_type") or ""),
                "message": str(item.get("message") or ""),
                "created_at": item.get("created_at"),
                "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
            },
        )
        last_seen_id = event_id
    ctx.metadata["_onboarding_last_event_id"] = last_seen_id


def _build_cli_env(run_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    db_path = run_dir / "harness.sqlite"
    env.setdefault("PYTHONPATH", str(REPO_ROOT))
    env["DEVGODZILLA_ENV"] = "test"
    if not env.get("DEVGODZILLA_DB_URL"):
        env.setdefault("DEVGODZILLA_DB_PATH", str(db_path))
    env.setdefault("DEVGODZILLA_DEFAULT_ENGINE_ID", "opencode")
    env.setdefault("DEVGODZILLA_OPENCODE_MODEL", "zai-coding-plan/glm-5")
    cfg = load_config()
    if cfg.windmill_url:
        env.setdefault("DEVGODZILLA_WINDMILL_URL", cfg.windmill_url)
    if cfg.windmill_token:
        env.setdefault("DEVGODZILLA_WINDMILL_TOKEN", cfg.windmill_token)
    if cfg.windmill_workspace:
        env.setdefault("DEVGODZILLA_WINDMILL_WORKSPACE", cfg.windmill_workspace)
    if cfg.windmill_env_file:
        env.setdefault("DEVGODZILLA_WINDMILL_ENV_FILE", str(cfg.windmill_env_file))
    return env


def _stage_project_create(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    env = _build_cli_env(ctx.run_dir)

    checkout_root = _workspace_root() / scenario.repo.owner / scenario.repo.name
    checkout_root.parent.mkdir(parents=True, exist_ok=True)

    if (checkout_root / ".git").exists():
        _run_git("fetch", "--all", "--prune", cwd=checkout_root, env=env)
        base_branch = _checkout_and_update_branch(checkout_root, env, scenario.repo.default_branch)
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
        log_file=_stage_log_file(ctx, stage, "project-create"),
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
    cfg = load_config()
    token = env.get("DEVGODZILLA_WINDMILL_TOKEN", "") or (cfg.windmill_token or "")
    if not token:
        raise RuntimeError(
            "Windmill token is missing for harness polling. "
            "Set DEVGODZILLA_WINDMILL_TOKEN or DEVGODZILLA_WINDMILL_ENV_FILE."
        )

    config = WindmillConfig(
        base_url=env.get("DEVGODZILLA_WINDMILL_URL", cfg.windmill_url or "http://localhost:8001"),
        token=token,
        workspace=env.get("DEVGODZILLA_WINDMILL_WORKSPACE", cfg.windmill_workspace or "demo1"),
        timeout=float(env.get("DEVGODZILLA_WINDMILL_TIMEOUT", "30")),
        max_retries=int(env.get("DEVGODZILLA_WINDMILL_MAX_RETRIES", "3")),
        backoff_base_seconds=float(env.get("DEVGODZILLA_WINDMILL_BACKOFF_BASE_SECONDS", "0.5")),
        backoff_max_seconds=float(env.get("DEVGODZILLA_WINDMILL_BACKOFF_MAX_SECONDS", "5.0")),
    )
    return WindmillClient(config)


def _wait_for_windmill_job(
    *,
    client: WindmillClient,
    job_id: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
    log_file: Path,
    heartbeat_timeout_seconds: float,
    progress_callback: ProgressCallback | None = None,
) -> Any:
    start = time.monotonic()
    last_status: JobStatus | None = None
    log_offset = 0
    last_progress = start
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(
            f"{datetime.now(UTC).isoformat()} meta wait_start job_id={job_id} "
            f"timeout_seconds={timeout_seconds} poll_interval_seconds={poll_interval_seconds} "
            f"heartbeat_timeout_seconds={heartbeat_timeout_seconds}\n"
        )
        handle.flush()
        while True:
            job = client.get_job(job_id)
            now = time.monotonic()

            if job.status != last_status:
                handle.write(f"{datetime.now(UTC).isoformat()} meta status={job.status.value}\n")
                handle.flush()
                last_status = job.status
                last_progress = now

            try:
                logs = client.get_job_logs(job_id)
            except Exception as exc:  # noqa: BLE001
                logs = ""
                handle.write(f"{datetime.now(UTC).isoformat()} meta log_fetch_error={exc}\n")
                handle.flush()

            if logs:
                if len(logs) < log_offset:
                    log_offset = 0
                if len(logs) > log_offset:
                    delta = logs[log_offset:]
                    handle.write(delta)
                    if not delta.endswith("\n"):
                        handle.write("\n")
                    handle.flush()
                    log_offset = len(logs)
                    last_progress = now

            if progress_callback is not None:
                try:
                    progress_callback(job)
                except Exception as exc:  # noqa: BLE001
                    handle.write(f"{datetime.now(UTC).isoformat()} meta progress_callback_error={exc}\n")
                    handle.flush()

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELED):
                handle.write(f"{datetime.now(UTC).isoformat()} meta wait_finished status={job.status.value}\n")
                handle.flush()
                return job

            if now - start > timeout_seconds:
                raise TimeoutError(
                    f"Windmill job {job_id} did not complete within {timeout_seconds}s "
                    f"(status={job.status.value}, log_file={log_file})"
                )

            if heartbeat_timeout_seconds > 0 and now - last_progress > heartbeat_timeout_seconds:
                raise TimeoutError(
                    f"Windmill job {job_id} had no status/log updates for {heartbeat_timeout_seconds}s "
                    f"(status={job.status.value}, log_file={log_file})"
                )

            time.sleep(poll_interval_seconds)


def _coerce_job_result_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"_raw": value}
        return parsed if isinstance(parsed, dict) else {"_raw": parsed}
    return {}


def _assert_discovery_outputs(
    *,
    repo_root: Path,
    scenario: ScenarioConfig,
    payload_local_path: str | None,
) -> Path:
    roots: list[Path] = [repo_root]
    if payload_local_path:
        candidate = Path(payload_local_path).expanduser().resolve(strict=False)
        if candidate not in roots:
            roots.insert(0, candidate)

    errors: list[str] = []
    for candidate in roots:
        try:
            assert_paths_exist(candidate, scenario.discovery_outputs)
            return candidate
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{candidate}: {exc}")

    checked = ", ".join(str(root) for root in roots)
    details = " | ".join(errors)
    raise RuntimeError(f"Missing expected discovery outputs. checked={checked} details={details}")


def _stage_project_onboard_agent(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
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
        log_file=_stage_log_file(ctx, stage, "project-discover"),
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
        log_file=_stage_log_file(ctx, stage, "project-onboard"),
    )
    if not onboarded.get("success"):
        raise RuntimeError(f"Windmill onboarding enqueue failed: {onboarded}")

    job_id = str(onboarded.get("windmill_job_id") or "")
    if not job_id:
        raise RuntimeError(f"Missing windmill_job_id in onboard payload: {onboarded}")

    poll_interval = float(os.environ.get("HARNESS_WINDMILL_POLL_INTERVAL", "2.0"))
    heartbeat_timeout = float(os.environ.get("HARNESS_WINDMILL_HEARTBEAT_TIMEOUT_SECONDS", "0"))
    windmill_log_file = ctx.diagnostics_dir / f"windmill-job-{job_id}.log"
    client = _build_windmill_client(env)
    try:
        try:
            final_job = _wait_for_windmill_job(
                client=client,
                job_id=job_id,
                timeout_seconds=float(scenario.timeouts.onboard_seconds),
                poll_interval_seconds=poll_interval,
                log_file=windmill_log_file,
                heartbeat_timeout_seconds=heartbeat_timeout,
                progress_callback=lambda job: _mirror_onboarding_progress(
                    ctx,
                    env=env,
                    project_id=project_id,
                    stage=stage,
                    windmill_job_id=job_id,
                    windmill_status=job.status.value,
                ),
            )
        except KeyboardInterrupt:
            _cancel_windmill_job_on_interrupt(
                ctx,
                client=client,
                job_id=job_id,
                stage=stage,
                project_id=project_id,
            )
            _cancel_backend_discovery_on_interrupt(
                ctx,
                env=env,
                project_id=project_id,
                stage=stage,
                reason="keyboard_interrupt",
            )
            raise
        if final_job.status != JobStatus.COMPLETED:
            logs = ""
            try:
                logs = client.get_job_logs(job_id)[:5000]
            except Exception:
                logs = ""
            raise RuntimeError(
                "Windmill onboarding job failed: "
                f"id={job_id} status={final_job.status} error={final_job.error} "
                f"log_file={windmill_log_file} logs={logs}"
            )
    finally:
        client.close()

    job_result = _coerce_job_result_dict(final_job.result)
    write_diagnostic_file(
        ctx.run_dir,
        f"windmill-job-{job_id}",
        {
            "job_id": job_id,
            "status": final_job.status.value,
            "error": final_job.error,
            "result": job_result or final_job.result,
            "job_log_file": str(windmill_log_file),
        },
    )

    if job_result:
        if job_result.get("success") is False:
            payload_error = str(job_result.get("error") or "unknown")
            hint = ""
            if "project not found" in payload_error.lower():
                hint = (
                    " This usually indicates harness CLI and backend use different databases; "
                    "align DEVGODZILLA_DB_URL/DEVGODZILLA_DB_PATH."
                )
            raise RuntimeError(
                f"Windmill onboarding payload reported failure: id={job_id} error={payload_error}.{hint}"
            )

        if job_result.get("discovery_success") is False:
            missing = job_result.get("discovery_missing_outputs") or []
            discovery_error = job_result.get("discovery_error")
            raise RuntimeError(
                f"Windmill onboarding discovery failed: id={job_id} error={discovery_error} missing_outputs={missing}"
            )

    payload_local_path = str(job_result.get("local_path") or "").strip() if job_result else ""
    resolved_repo_root = _assert_discovery_outputs(
        repo_root=repo_root,
        scenario=scenario,
        payload_local_path=payload_local_path or None,
    )
    if resolved_repo_root != repo_root:
        ctx.metadata["repo_root"] = str(resolved_repo_root)

    return {
        "windmill_job_id": job_id,
        "onboard_mode": "windmill",
        "windmill_status": final_job.status.value,
        "windmill_log_file": str(windmill_log_file),
        "repo_root": str(resolved_repo_root),
        "discovery_success": job_result.get("discovery_success") if job_result else None,
    }


def _stage_project_onboard(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    mode = os.environ.get("HARNESS_ONBOARD_MODE", "windmill").strip().lower()
    if mode == "agent":
        return _stage_project_onboard_agent(ctx, scenario, stage)
    return _stage_project_onboard_windmill(ctx, scenario, stage)


def _stage_protocol_create(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    _require_metadata(ctx, "project_id", "env", "base_branch")

    env = ctx.metadata["env"]
    project_id = int(ctx.metadata["project_id"])
    base_branch = str(ctx.metadata["base_branch"])
    cycle_index = int(ctx.metadata.get("_protocol_cycle_index", 0))
    cycle_total = int(ctx.metadata.get("_protocol_cycle_total", 1))
    if cycle_total > 1:
        protocol_name = f"{scenario.scenario_id}-protocol-{cycle_index + 1}"
        protocol_description = (
            f"Harness protocol cycle {cycle_index + 1}/{cycle_total} for {scenario.scenario_id}"
        )
    else:
        protocol_name = f"{scenario.scenario_id}-protocol"
        protocol_description = f"Harness protocol for {scenario.scenario_id}"

    proto = _run_cli(
        "protocol",
        "create",
        str(project_id),
        protocol_name,
        "--description",
        protocol_description,
        "--branch",
        base_branch,
        cwd=REPO_ROOT,
        env=env,
        timeout=scenario.timeouts.planning_seconds,
        log_file=_stage_log_file(ctx, stage, "protocol-create"),
    )

    if not proto.get("success"):
        raise RuntimeError(f"Protocol create failed payload: {proto}")

    protocol_id = int(proto["protocol_run_id"])
    ctx.metadata.update({"protocol_id": protocol_id, "protocol_name": protocol_name})
    return {"protocol_run_id": protocol_id}


def _stage_protocol_worktree(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    del scenario
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
        log_file=_stage_log_file(ctx, stage, "protocol-worktree"),
    )
    if not worktree.get("success"):
        raise RuntimeError(f"Protocol worktree failed payload: {worktree}")

    worktree_path = Path(worktree["worktree_path"])
    if not worktree_path.exists():
        raise RuntimeError(f"Worktree path does not exist: {worktree_path}")

    ctx.metadata["worktree_path"] = str(worktree_path)
    return {"worktree_path": str(worktree_path), "branch": worktree.get("branch")}


def _stage_protocol_plan(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
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
        log_file=_stage_log_file(ctx, stage, "protocol-plan"),
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
    _require_metadata(ctx, "protocol_id", "env")

    env = ctx.metadata["env"]
    protocol_id = int(ctx.metadata["protocol_id"])
    db_url = env.get("DEVGODZILLA_DB_URL")
    db_path_raw = env.get("DEVGODZILLA_DB_PATH")
    db_path = Path(db_path_raw).expanduser() if db_path_raw else None
    db = get_database(db_url=db_url, db_path=db_path)
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
            log_file=_stage_log_file(ctx, stage, f"step-execute-{step.id}"),
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


def _desired_feature_cycles() -> int:
    raw = os.environ.get("HARNESS_FEATURE_CYCLES", "2").strip()
    try:
        cycles = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"HARNESS_FEATURE_CYCLES must be an integer, got: {raw!r}") from exc
    return max(1, cycles)


def _stage_protocol_feature_cycles(ctx: HarnessRunContext, scenario: ScenarioConfig, stage: str) -> dict[str, Any]:
    cycles = _desired_feature_cycles()
    cycle_results: list[dict[str, Any]] = []

    def _run_cycle_substage(
        cycle_number: int,
        substage: str,
        stage_name: str,
        fn,
    ) -> dict[str, Any]:
        started = time.monotonic()
        _emit_ctx_event(
            ctx,
            "substage_started",
            {
                "scenario_id": ctx.scenario_id,
                "parent_stage": stage,
                "cycle": cycle_number,
                "substage": substage,
                "stage_name": stage_name,
            },
        )
        try:
            result = fn(ctx, scenario, stage_name)
        except Exception as exc:  # noqa: BLE001
            _emit_ctx_event(
                ctx,
                "substage_failed",
                {
                    "scenario_id": ctx.scenario_id,
                    "parent_stage": stage,
                    "cycle": cycle_number,
                    "substage": substage,
                    "stage_name": stage_name,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "error": str(exc) or exc.__class__.__name__,
                },
            )
            raise

        _emit_ctx_event(
            ctx,
            "substage_succeeded",
            {
                "scenario_id": ctx.scenario_id,
                "parent_stage": stage,
                "cycle": cycle_number,
                "substage": substage,
                "stage_name": stage_name,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "details": result or {},
            },
        )
        return result or {}

    for cycle_index in range(cycles):
        cycle_number = cycle_index + 1
        cycle_stage_prefix = f"{stage}-cycle-{cycle_number}"
        cycle_started = time.monotonic()
        _emit_ctx_event(
            ctx,
            "protocol_cycle_started",
            {
                "scenario_id": ctx.scenario_id,
                "parent_stage": stage,
                "cycle": cycle_number,
                "total_cycles": cycles,
            },
        )
        ctx.metadata["_protocol_cycle_index"] = cycle_index
        ctx.metadata["_protocol_cycle_total"] = cycles
        try:
            created = _run_cycle_substage(
                cycle_number,
                "protocol_create",
                f"{cycle_stage_prefix}-protocol_create",
                _stage_protocol_create,
            )
            worktree = _run_cycle_substage(
                cycle_number,
                "protocol_worktree",
                f"{cycle_stage_prefix}-protocol_worktree",
                _stage_protocol_worktree,
            )
            planned = _run_cycle_substage(
                cycle_number,
                "protocol_plan",
                f"{cycle_stage_prefix}-protocol_plan",
                _stage_protocol_plan,
            )
            executed = _run_cycle_substage(
                cycle_number,
                "step_execute",
                f"{cycle_stage_prefix}-step_execute",
                _stage_step_execute,
            )
            _emit_ctx_event(
                ctx,
                "protocol_cycle_finished",
                {
                    "scenario_id": ctx.scenario_id,
                    "parent_stage": stage,
                    "cycle": cycle_number,
                    "total_cycles": cycles,
                    "status": "passed",
                    "duration_ms": int((time.monotonic() - cycle_started) * 1000),
                },
            )
        except Exception as exc:  # noqa: BLE001
            _emit_ctx_event(
                ctx,
                "protocol_cycle_finished",
                {
                    "scenario_id": ctx.scenario_id,
                    "parent_stage": stage,
                    "cycle": cycle_number,
                    "total_cycles": cycles,
                    "status": "failed",
                    "duration_ms": int((time.monotonic() - cycle_started) * 1000),
                    "error": str(exc) or exc.__class__.__name__,
                },
            )
            raise
        finally:
            ctx.metadata.pop("_protocol_cycle_index", None)
            ctx.metadata.pop("_protocol_cycle_total", None)

        cycle_results.append(
            {
                "cycle": cycle_number,
                "protocol_run_id": int(created.get("protocol_run_id") or ctx.metadata.get("protocol_id")),
                "protocol_name": str(ctx.metadata.get("protocol_name") or ""),
                "worktree_path": worktree.get("worktree_path"),
                "steps_created": int(planned.get("steps_created") or 0),
                "executed_steps": int(executed.get("executed_steps") or 0),
                "protocol_status": executed.get("protocol_status"),
                "protocol_root": executed.get("protocol_root"),
            }
        )

    total_steps_created = sum(item["steps_created"] for item in cycle_results)
    total_executed_steps = sum(item["executed_steps"] for item in cycle_results)
    return {
        "feature_cycles": cycles,
        "total_steps_created": total_steps_created,
        "total_executed_steps": total_executed_steps,
        "cycles": cycle_results,
    }


def build_live_cli_stage_handlers() -> dict[str, StageHandler]:
    return {
        "project_create": _stage_project_create,
        "project_onboard": _stage_project_onboard,
        "project_onboard_agent": _stage_project_onboard_agent,
        "project_onboard_windmill": _stage_project_onboard_windmill,
        "protocol_feature_cycles": _stage_protocol_feature_cycles,
        "protocol_create": _stage_protocol_create,
        "protocol_worktree": _stage_protocol_worktree,
        "protocol_plan": _stage_protocol_plan,
        "step_execute": _stage_step_execute,
    }
