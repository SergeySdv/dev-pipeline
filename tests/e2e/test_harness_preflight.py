from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.e2e.harness.preflight import run_preflight


class _FakeRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")


def test_run_preflight_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "run-local-dev.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    monkeypatch.setenv("HARNESS_GITHUB_REPOS", "a,b,c")

    runner = _FakeRunner()
    report = run_preflight(
        project_root=tmp_path,
        command_exists=lambda command: True,
        command_runner=runner,
        http_probe=lambda url, timeout: (True, "ok"),
    )

    assert report.ok
    assert any(call[-1] == "up" for call in runner.calls)
    assert any(call[:2] == ["bash", "-lc"] and "backend start" in call[2] for call in runner.calls)


def test_run_preflight_requires_repo_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "run-local-dev.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    monkeypatch.delenv("HARNESS_GITHUB_REPOS", raising=False)
    monkeypatch.delenv("HARNESS_REPO_URL_OVERRIDE", raising=False)

    report = run_preflight(
        project_root=tmp_path,
        command_exists=lambda command: True,
        command_runner=_FakeRunner(),
        http_probe=lambda url, timeout: (True, "ok"),
    )

    assert not report.ok
    assert any("No repos configured" in error for error in report.errors)


def test_run_preflight_requires_three_repos_without_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = tmp_path / "scripts" / "run-local-dev.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    monkeypatch.setenv("HARNESS_GITHUB_REPOS", "only-one")
    monkeypatch.delenv("HARNESS_REPO_URL_OVERRIDE", raising=False)

    report = run_preflight(
        project_root=tmp_path,
        command_exists=lambda command: True,
        command_runner=_FakeRunner(),
        http_probe=lambda url, timeout: (True, "ok"),
    )

    assert not report.ok
    assert any("at least three repositories" in error for error in report.errors)


def test_run_preflight_allows_single_repo_with_scenario_filter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = tmp_path / "scripts" / "run-local-dev.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    monkeypatch.setenv("HARNESS_GITHUB_REPOS", "only-one")
    monkeypatch.setenv("HARNESS_SCENARIO", "live_onboarding_demo_spring")
    monkeypatch.delenv("HARNESS_REPO_URL_OVERRIDE", raising=False)

    report = run_preflight(
        project_root=tmp_path,
        command_exists=lambda command: True,
        command_runner=_FakeRunner(),
        http_probe=lambda url, timeout: (True, "ok"),
    )

    assert report.ok


def test_run_preflight_no_autostart_skips_runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HARNESS_GITHUB_REPOS", "a,b,c")

    runner = _FakeRunner()
    report = run_preflight(
        auto_start=False,
        project_root=tmp_path,
        command_exists=lambda command: True,
        command_runner=runner,
        http_probe=lambda url, timeout: (True, "ok"),
    )

    assert report.ok
    assert runner.calls == []
    assert report.warnings


def test_run_preflight_waits_for_backend_readiness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "run-local-dev.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    monkeypatch.setenv("HARNESS_GITHUB_REPOS", "a,b,c")
    monkeypatch.setenv("HARNESS_READY_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("HARNESS_READY_POLL_INTERVAL_SECONDS", "0.01")

    calls = {"backend": 0, "windmill": 0}

    def _probe(url: str, timeout: float) -> tuple[bool, str]:
        del timeout
        if "8000/health" in url:
            calls["backend"] += 1
            return (calls["backend"] >= 2, "backend")
        calls["windmill"] += 1
        return (calls["windmill"] >= 2, "windmill")

    report = run_preflight(
        project_root=tmp_path,
        command_exists=lambda command: True,
        command_runner=_FakeRunner(),
        http_probe=_probe,
    )

    assert report.ok
    assert calls["backend"] >= 2
    assert calls["windmill"] >= 2
