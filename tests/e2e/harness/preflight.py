from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import httpx

REPO_ROOT = Path(__file__).resolve().parents[3]

CommandRunner = Callable[[list[str], Path, int], subprocess.CompletedProcess[str]]
CommandExists = Callable[[str], bool]
HttpProbe = Callable[[str, float], tuple[bool, str]]


def _default_command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def _default_command_runner(args: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _default_http_probe(url: str, timeout: float) -> tuple[bool, str]:
    try:
        response = httpx.get(url, timeout=timeout)
    except Exception as exc:  # pragma: no cover - network exceptions are environment-dependent
        return False, str(exc)

    body = response.text[:256]
    return response.status_code < 500, body


def _wait_for_probe(
    probe: HttpProbe,
    *,
    url: str,
    probe_timeout_seconds: float,
    ready_timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[bool, str]:
    deadline = time.monotonic() + ready_timeout_seconds
    last_body = ""
    while time.monotonic() < deadline:
        ok, body = probe(url, probe_timeout_seconds)
        last_body = body
        if ok:
            return True, body
        time.sleep(poll_interval_seconds)
    return False, last_body


@dataclass
class PreflightReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def _add_error(report: PreflightReport, message: str) -> None:
    report.errors.append(message)


def _require_command(report: PreflightReport, command: str, command_exists: CommandExists) -> None:
    if not command_exists(command):
        _add_error(report, f"Missing required command: {command}")


def _run_and_capture(
    report: PreflightReport,
    args: list[str],
    *,
    name: str,
    cwd: Path,
    timeout: int,
    runner: CommandRunner,
) -> bool:
    proc = runner(args, cwd, timeout)
    report.details[f"{name}_exit_code"] = str(proc.returncode)
    report.details[f"{name}_stdout"] = (proc.stdout or "")[:300]
    report.details[f"{name}_stderr"] = (proc.stderr or "")[:300]
    if proc.returncode != 0:
        _add_error(report, f"Command failed ({name}): {' '.join(args)}")
        return False
    return True


def ensure_local_services(
    report: PreflightReport,
    *,
    project_root: Path,
    runner: CommandRunner,
    auto_start: bool,
) -> None:
    if not auto_start:
        report.warnings.append("Harness preflight auto_start disabled; assuming services already running.")
        return

    script = project_root / "scripts" / "run-local-dev.sh"
    if not script.exists():
        _add_error(report, f"Local dev script not found: {script}")
        return

    _run_and_capture(
        report,
        ["bash", str(script), "up"],
        name="infra_up",
        cwd=project_root,
        timeout=240,
        runner=runner,
    )
    if os.environ.get("HARNESS_WINDMILL_AUTO_IMPORT", "1") == "1":
        _run_and_capture(
            report,
            ["bash", str(script), "import"],
            name="windmill_import",
            cwd=project_root,
            timeout=900,
            runner=runner,
        )
    background_backend_cmd = (
        f"nohup bash {shlex.quote(str(script))} backend start "
        "> /tmp/devgodzilla-harness-backend.log 2>&1 &"
    )
    _run_and_capture(
        report,
        ["bash", "-lc", background_backend_cmd],
        name="backend_start",
        cwd=project_root,
        timeout=30,
        runner=runner,
    )


def run_preflight(
    *,
    auto_start: bool = True,
    require_opencode: bool = True,
    require_windmill: bool = True,
    project_root: Path | None = None,
    command_exists: CommandExists | None = None,
    command_runner: CommandRunner | None = None,
    http_probe: HttpProbe | None = None,
) -> PreflightReport:
    report = PreflightReport()
    root = project_root or REPO_ROOT
    exists = command_exists or _default_command_exists
    runner = command_runner or _default_command_runner
    probe = http_probe or _default_http_probe

    _require_command(report, "git", exists)
    if require_opencode:
        _require_command(report, "opencode", exists)

    repo_list = [repo.strip() for repo in os.environ.get("HARNESS_GITHUB_REPOS", "").split(",") if repo.strip()]
    has_repo_list = bool(repo_list)
    has_repo_override = bool(os.environ.get("HARNESS_REPO_URL_OVERRIDE"))
    has_scenario_filter = bool(os.environ.get("HARNESS_SCENARIO"))
    if not has_repo_list and not has_repo_override:
        _add_error(
            report,
            "No repos configured: set HARNESS_GITHUB_REPOS with at least three repos "
            "(for example: test-glm5-demo,SimpleAdminReporter,demo-spring) or set HARNESS_REPO_URL_OVERRIDE",
        )
    elif has_repo_list and not has_repo_override and not has_scenario_filter and len(repo_list) < 3:
        _add_error(
            report,
            "HARNESS_GITHUB_REPOS must include at least three repositories for matrix coverage, "
            f"got {len(repo_list)}",
        )

    ensure_local_services(
        report,
        project_root=root,
        runner=runner,
        auto_start=auto_start,
    )

    backend_health = os.environ.get("HARNESS_BACKEND_HEALTH_URL", "http://localhost:8000/health")
    ready_timeout_seconds = float(os.environ.get("HARNESS_READY_TIMEOUT_SECONDS", "90"))
    poll_interval_seconds = float(os.environ.get("HARNESS_READY_POLL_INTERVAL_SECONDS", "2"))
    backend_ok, backend_body = _wait_for_probe(
        probe,
        url=backend_health,
        probe_timeout_seconds=4.0,
        ready_timeout_seconds=ready_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    report.details["backend_health_url"] = backend_health
    report.details["backend_health_probe"] = backend_body
    if not backend_ok:
        _add_error(report, f"Backend health check failed: {backend_health}")

    if require_windmill:
        windmill_version = os.environ.get("HARNESS_WINDMILL_VERSION_URL", "http://localhost:8001/api/version")
        windmill_ok, windmill_body = _wait_for_probe(
            probe,
            url=windmill_version,
            probe_timeout_seconds=4.0,
            ready_timeout_seconds=ready_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        report.details["windmill_version_url"] = windmill_version
        report.details["windmill_version_probe"] = windmill_body
        if not windmill_ok:
            _add_error(report, f"Windmill version check failed: {windmill_version}")

    return report
