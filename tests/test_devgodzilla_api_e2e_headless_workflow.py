from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
    from devgodzilla.api.app import app
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore
    app = None  # type: ignore


def _write_opencode_stub(bin_dir: Path, log_path: Path) -> None:
    stub = bin_dir / "opencode"
    stub.write_text(
        """#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

log_path = os.environ.get("OPENCODE_E2E_LOG")
if log_path:
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")

prompt = sys.stdin.read()
root = Path(os.getcwd())

if "DISCOVERY_SUMMARY.json" in prompt or "specs/discovery/_runtime/DISCOVERY" in prompt:
    out = root / "specs" / "discovery" / "_runtime"
    out.mkdir(parents=True, exist_ok=True)
    (out / "DISCOVERY.md").write_text("# Discovery\\n", encoding="utf-8")
    (out / "DISCOVERY_SUMMARY.json").write_text(json.dumps({"languages": ["python"]}), encoding="utf-8")
    (out / "ARCHITECTURE.md").write_text("# Architecture\\n", encoding="utf-8")
    (out / "API_REFERENCE.md").write_text("# API Reference\\n", encoding="utf-8")
    (out / "CI_NOTES.md").write_text("# CI Notes\\n", encoding="utf-8")

if ".protocols/" in prompt and "step-01-setup.md" in prompt:
    m = re.search(r"\\.protocols/([^/\\s]+)/", prompt)
    name = m.group(1) if m else "e2e-protocol"
    proto = root / ".protocols" / name
    proto.mkdir(parents=True, exist_ok=True)
    (proto / "plan.md").write_text(f"# Plan: {name}\\n", encoding="utf-8")
    (proto / "step-01-setup.md").write_text("# setup\\n", encoding="utf-8")
    (proto / "step-02-implement.md").write_text("# implement\\n", encoding="utf-8")
    (proto / "step-03-verify.md").write_text("# verify\\n", encoding="utf-8")

print("ok")
sys.exit(0)
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
@pytest.mark.integration
def test_api_e2e_headless_workflow_real_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if os.environ.get("DEVGODZILLA_RUN_E2E") != "1":
        pytest.skip("Set DEVGODZILLA_RUN_E2E=1 to enable real-repo E2E.")
    if shutil.which("git") is None:
        pytest.skip("git is required for this E2E test.")

    repo_root = Path(__file__).resolve().parents[1]

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    opencode_log = tmp_path / "opencode.jsonl"
    _write_opencode_stub(bin_dir, opencode_log)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
            "OPENCODE_E2E_LOG": str(opencode_log),
            "PYTHONPATH": str(repo_root),
            "DEVGODZILLA_ENV": "test",
            "DEVGODZILLA_DB_PATH": str(tmp_path / "devgodzilla.sqlite"),
            "DEVGODZILLA_DEFAULT_ENGINE_ID": "opencode",
            "DEVGODZILLA_OPENCODE_MODEL": "zai-coding-plan/glm-5",
            "DEVGODZILLA_AUTO_GENERATE_PROTOCOL": "true",
        }
    )
    monkeypatch.setenv("PATH", env["PATH"])
    monkeypatch.setenv("OPENCODE_E2E_LOG", env["OPENCODE_E2E_LOG"])
    monkeypatch.setenv("PYTHONPATH", env["PYTHONPATH"])
    monkeypatch.setenv("DEVGODZILLA_ENV", env["DEVGODZILLA_ENV"])
    monkeypatch.setenv("DEVGODZILLA_DB_PATH", env["DEVGODZILLA_DB_PATH"])
    monkeypatch.setenv("DEVGODZILLA_DEFAULT_ENGINE_ID", env["DEVGODZILLA_DEFAULT_ENGINE_ID"])
    monkeypatch.setenv("DEVGODZILLA_OPENCODE_MODEL", env["DEVGODZILLA_OPENCODE_MODEL"])
    monkeypatch.setenv("DEVGODZILLA_AUTO_GENERATE_PROTOCOL", env["DEVGODZILLA_AUTO_GENERATE_PROTOCOL"])

    git_url = "https://github.com/ilyafedotov-ops/click"
    cloned_repo = tmp_path / "click"
    subprocess.run(  # noqa: S603
        ["git", "clone", "--depth", "1", git_url, str(cloned_repo)],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
    )

    base_branch = (
        subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cloned_repo, text=True)  # noqa: S603,S607
        .strip()
    )

    with TestClient(app) as client:  # type: ignore[arg-type]
        created = client.post(
            "/projects",
            json={"name": "click-api-e2e", "git_url": git_url, "base_branch": base_branch, "local_path": str(cloned_repo)},
        )
        assert created.status_code == 200
        project = created.json()
        project_id = int(project["id"])

        onboard = client.post(
            f"/projects/{project_id}/actions/onboard",
            json={
                "branch": base_branch,
                "clone_if_missing": False,
                "run_discovery_agent": True,
                "discovery_pipeline": True,
                "discovery_engine_id": "opencode",
                "discovery_model": "zai-coding-plan/glm-5",
            },
        )
        assert onboard.status_code == 200
        onboarded = onboard.json()
        assert onboarded["success"] is True
        assert onboarded["discovery_success"] is True
        assert onboarded["discovery_missing_outputs"] == []

        proto = client.post(
            f"/projects/{project_id}/protocols",
            json={"protocol_name": "e2e-proto", "description": "api e2e", "base_branch": base_branch, "auto_start": False},
        )
        assert proto.status_code == 200
        protocol_id = int(proto.json()["id"])

        started = client.post(f"/protocols/{protocol_id}/actions/start", json={})
        assert started.status_code == 200

        # Poll until planned (planning runs as background task in-process).
        for _ in range(60):
            p = client.get(f"/protocols/{protocol_id}")
            assert p.status_code == 200
            status = p.json()["status"]
            if status == "planned":
                break
        else:
            raise AssertionError(f"Protocol did not reach planned status: {status}")

        step_ids: list[int] = []
        while True:
            nxt = client.post(f"/protocols/{protocol_id}/actions/run_next_step", json={})
            assert nxt.status_code == 200
            step_id = nxt.json()["step_run_id"]
            if step_id is None:
                break
            step_ids.append(int(step_id))

            ex = client.post(f"/steps/{step_id}/actions/execute", json={})
            assert ex.status_code == 200

        assert step_ids, "Expected at least one planned step"

        final = client.get(f"/protocols/{protocol_id}")
        assert final.status_code == 200
        assert final.json()["status"] == "completed"

    # Validate discovery outputs exist on disk (written by agent).
    discovery_dir = cloned_repo / "specs" / "discovery" / "_runtime"
    assert (discovery_dir / "DISCOVERY.md").exists()
    assert (discovery_dir / "DISCOVERY_SUMMARY.json").exists()
