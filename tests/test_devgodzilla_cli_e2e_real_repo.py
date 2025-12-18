from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _run_cli(*args: str, cwd: Path, env: dict[str, str]) -> str:
    cmd = [sys.executable, "-m", "devgodzilla.cli.main", *args]
    proc = subprocess.run(  # noqa: S603
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise AssertionError(
            "CLI command failed\n"
            f"cmd: {cmd}\n"
            f"cwd: {cwd}\n"
            f"exit_code: {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )
    return proc.stdout.strip()


def _git(*args: str, cwd: Path, env: dict[str, str]) -> str:
    proc = subprocess.run(  # noqa: S603
        ["git", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return (proc.stdout or "").strip()


@pytest.mark.integration
def test_devgodzilla_cli_e2e_real_repo(tmp_path: Path) -> None:
    if os.environ.get("DEVGODZILLA_RUN_E2E") != "1":
        pytest.skip("Set DEVGODZILLA_RUN_E2E=1 to enable real-repo CLI E2E test.")
    if shutil.which("git") is None:
        pytest.skip("git is required for this E2E test.")

    repo_root = Path(__file__).resolve().parents[1]

    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)

    # Stub `opencode` so the test is deterministic while still exercising the real engine adapter.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    opencode_log = tmp_path / "opencode-argv.jsonl"
    stub = bin_dir / "opencode"
    stub.write_text(
        """#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

log_path = os.environ.get("OPENCODE_E2E_LOG")
entry = {"argv": sys.argv[1:], "cwd": os.getcwd()}
if log_path:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\\n")

# Consume stdin to match real CLI behavior.
prompt = sys.stdin.read()

# Drop a marker file in the working directory for debugging.
Path(".opencode_stub_ran").write_text("ok\\n", encoding="utf-8")

# Simulate agent-written artifacts (legacy TasksGodzilla-style) so tests validate outputs
# produced by the "agent", not by the test harness.
repo_root = Path(os.getcwd())

if "tasksgodzilla/DISCOVERY" in prompt or "DISCOVERY_SUMMARY.json" in prompt:
    out_dir = repo_root / "tasksgodzilla"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "DISCOVERY.md").write_text("# Discovery\\n\\n- stub\\n", encoding="utf-8")
    (out_dir / "ARCHITECTURE.md").write_text("# Architecture\\n\\n- stub\\n", encoding="utf-8")
    (out_dir / "API_REFERENCE.md").write_text("# API Reference\\n\\n- stub\\n", encoding="utf-8")
    (out_dir / "CI_NOTES.md").write_text("# CI Notes\\n\\n- stub\\n", encoding="utf-8")
    summary = {
        "languages": ["python"],
        "frameworks": [],
        "build_tools": [],
        "lint_tools": [],
        "typecheck_tools": [],
        "test_tools": [],
        "package_managers": [],
        "entrypoints": {"clis": [], "servers": [], "workers": [], "scripts": []},
        "ci": {"github_workflows": [], "gitlab_pipelines": [], "ci_scripts": []},
        "env_vars": [],
        "data_stores": [],
        "external_services": [],
        "notes": [],
    }
    (out_dir / "DISCOVERY_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

if ".protocols/" in prompt and "step-01-setup.md" in prompt:
    # Extract `.protocols/<name>/` from the prompt.
    m = re.search(r"\\.protocols/([^/\\s]+)/", prompt)
    protocol_name = m.group(1) if m else os.environ.get("DEVGODZILLA_E2E_PROTOCOL", "e2e-protocol")
    proto_dir = repo_root / ".protocols" / protocol_name
    proto_dir.mkdir(parents=True, exist_ok=True)
    (proto_dir / "plan.md").write_text(f"# Plan: {protocol_name}\\n", encoding="utf-8")
    (proto_dir / "step-01-setup.md").write_text("# setup\\n", encoding="utf-8")
    (proto_dir / "step-02-implement.md").write_text("# implement\\n", encoding="utf-8")

print(json.dumps({"ok": True, "argv": sys.argv[1:]}))
sys.exit(0)
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PYTHONPATH": str(repo_root),
            "DEVGODZILLA_ENV": "test",
            "DEVGODZILLA_DB_PATH": str(tmp_path / "devgodzilla.sqlite"),
            "DEVGODZILLA_DEFAULT_ENGINE_ID": "opencode",
            "DEVGODZILLA_OPENCODE_MODEL": "zai-coding-plan/glm-4.6",
            "OPENCODE_E2E_LOG": str(opencode_log),
            "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
        }
    )

    git_url = "https://github.com/ilyafedotov-ops/click"
    cloned_repo = tmp_path / "click"
    subprocess.run(  # noqa: S603
        ["git", "clone", "--depth", "1", git_url, str(cloned_repo)],
        cwd=tmp_path,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    base_branch = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=cloned_repo, env=env)

    # Create project pointing to the cloned repo.
    created = json.loads(
        _run_cli(
            "--json",
            "project",
            "create",
            "click-e2e",
            "--repo",
            git_url,
            "--branch",
            base_branch,
            "--local-path",
            str(cloned_repo),
            cwd=tmp_path,
            env=env,
        )
    )
    assert created["success"] is True
    project_id = int(created["project_id"])

    # Discovery artifacts (agent-driven; produces tasksgodzilla/*).
    discovery = json.loads(
        _run_cli("--json", "project", "discover", str(project_id), "--agent", "--pipeline", cwd=tmp_path, env=env)
    )
    assert discovery["success"] is True
    assert discovery["engine_id"] == "opencode"

    tasksgodzilla_dir = cloned_repo / "tasksgodzilla"
    assert (tasksgodzilla_dir / "DISCOVERY.md").exists()
    assert (tasksgodzilla_dir / "DISCOVERY_SUMMARY.json").exists()
    assert json.loads((tasksgodzilla_dir / "DISCOVERY_SUMMARY.json").read_text(encoding="utf-8"))["languages"]

    # Protocol workflow (app-like): create -> ensure worktree -> plan (auto-generates protocol files) -> execute step via opencode.
    proto = json.loads(
        _run_cli(
            "--json",
            "protocol",
            "create",
            str(project_id),
            "e2e-protocol",
            "--description",
            "E2E protocol for verifying worktrees and artifacts",
            "--branch",
            base_branch,
            cwd=tmp_path,
            env=env,
        )
    )
    assert proto["success"] is True
    protocol_run_id = int(proto["protocol_run_id"])

    worktree = json.loads(_run_cli("--json", "protocol", "worktree", str(protocol_run_id), cwd=tmp_path, env=env))
    worktree_path = Path(worktree["worktree_path"])
    assert worktree["branch"]
    assert worktree_path.exists()
    porcelain = _git("worktree", "list", "--porcelain", cwd=cloned_repo, env=env)
    assert f"worktree {worktree_path}" in porcelain

    planned = json.loads(_run_cli("--json", "protocol", "plan", str(protocol_run_id), cwd=tmp_path, env=env))
    assert planned["success"] is True
    assert planned["steps_created"] >= 2

    from devgodzilla.db.database import SQLiteDatabase

    db = SQLiteDatabase(Path(env["DEVGODZILLA_DB_PATH"]))
    db.init_schema()
    run = db.get_protocol_run(protocol_run_id)
    assert run.worktree_path is not None
    assert run.protocol_root is not None
    env["DEVGODZILLA_E2E_PROTOCOL"] = "e2e-protocol"
    protocol_root = Path(run.protocol_root)
    assert protocol_root.exists()
    assert (protocol_root / "plan.md").exists()
    assert len(list(protocol_root.glob("step-*.md"))) >= 2
    assert run.template_config and "protocol_spec" in run.template_config
    protocol_spec = run.template_config["protocol_spec"]
    assert protocol_spec["version"]
    assert len(protocol_spec["steps"]) >= 2
    assert all(step.get("engine_id") == "opencode" for step in protocol_spec["steps"])
    for step in protocol_spec["steps"]:
        prompt_ref = step.get("prompt_ref")
        assert prompt_ref
        assert (Path(run.protocol_root) / prompt_ref).exists()
    steps = db.list_step_runs(protocol_run_id)
    assert len(steps) >= 2

    executed = json.loads(
        _run_cli(
            "--json",
            "step",
            "execute",
            str(steps[0].id),
            "--engine",
            "opencode",
            cwd=tmp_path,
            env=env,
        )
    )
    assert executed["success"] is True
    assert executed["engine_id"] == "opencode"
    assert executed["model"] == "zai-coding-plan/glm-4.6"
    assert executed["status"] == "needs_qa"

    # Validate DevGodzilla wrote execution artifacts (no manual file creation).
    artifacts_dir = Path(run.protocol_root) / ".devgodzilla" / "steps" / str(steps[0].id) / "artifacts"
    assert artifacts_dir.exists()
    assert (artifacts_dir / "execution.json").exists()
    assert (artifacts_dir / "stdout.log").exists()

    assert opencode_log.exists() and opencode_log.stat().st_size > 0
    logged = [json.loads(line) for line in opencode_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any("--model" in entry["argv"] and "zai-coding-plan/glm-4.6" in entry["argv"] for entry in logged)
    assert any("--cwd" in entry["argv"] and str(worktree_path) in entry["argv"] for entry in logged)
