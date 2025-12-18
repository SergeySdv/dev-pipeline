from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from devgodzilla.db.database import SQLiteDatabase
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.git import GitService
from devgodzilla.services.planning import PlanningService
from devgodzilla.config import load_config


def _init_git_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, check=True)  # noqa: S603
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "tester",
            "GIT_AUTHOR_EMAIL": "tester@example.com",
            "GIT_COMMITTER_NAME": "tester",
            "GIT_COMMITTER_EMAIL": "tester@example.com",
        },
    )


def _write_opencode_stub(bin_dir: Path) -> None:
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
m = re.search(r"\\.protocols/([^/\\s]+)/", prompt)
protocol_name = m.group(1) if m else "auto-proto"
root = Path(os.getcwd())
proto_dir = root / ".protocols" / protocol_name
proto_dir.mkdir(parents=True, exist_ok=True)
(proto_dir / "plan.md").write_text(f"# Plan: {protocol_name}\\n", encoding="utf-8")
(proto_dir / "step-01-setup.md").write_text("# setup\\n", encoding="utf-8")
(proto_dir / "step-02-implement.md").write_text("# implement\\n", encoding="utf-8")
print("ok")
sys.exit(0)
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)


def test_planning_auto_generates_protocol_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    opencode_log = tmp_path / "opencode.jsonl"
    _write_opencode_stub(bin_dir)

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("OPENCODE_E2E_LOG", str(opencode_log))
    monkeypatch.setenv("DEVGODZILLA_AUTO_GENERATE_PROTOCOL", "true")
    monkeypatch.setenv("DEVGODZILLA_DEFAULT_ENGINE_ID", "opencode")
    monkeypatch.setenv("DEVGODZILLA_OPENCODE_MODEL", "zai-coding-plan/glm-4.6")
    monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(tmp_path / "devgodzilla.sqlite"))

    db = SQLiteDatabase(Path(os.environ["DEVGODZILLA_DB_PATH"]))
    db.init_schema()

    project = db.create_project(name="demo", git_url=str(repo), base_branch="main", local_path=str(repo))
    run = db.create_protocol_run(
        project_id=project.id,
        protocol_name="auto-proto",
        status="pending",
        base_branch="main",
        worktree_path=None,
        protocol_root=None,
        description="auto generate protocol files",
    )

    cfg = load_config()
    ctx = ServiceContext(config=cfg)
    planning = PlanningService(ctx, db, git_service=GitService(ctx))
    result = planning.plan_protocol(run.id)

    assert result.success is True
    updated = db.get_protocol_run(run.id)
    assert updated.worktree_path
    assert updated.protocol_root

    protocol_root = Path(updated.protocol_root)
    assert (protocol_root / "plan.md").exists()
    assert len(list(protocol_root.glob("step-*.md"))) >= 2

    steps = db.list_step_runs(run.id)
    assert [s.step_name for s in steps] == ["step-01-setup", "step-02-implement"]

    assert opencode_log.exists()
    lines = [json.loads(l) for l in opencode_log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert any("--model" in entry["argv"] and "zai-coding-plan/glm-4.6" in entry["argv"] for entry in lines)
