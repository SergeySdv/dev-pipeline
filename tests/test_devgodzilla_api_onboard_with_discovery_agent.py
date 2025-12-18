import os
import subprocess
import tempfile
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
    from devgodzilla.api.app import app
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore
    app = None  # type: ignore


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True)  # noqa: S603
    (path / "README.md").write_text("demo", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        ["git", "commit", "-m", "init"],
        cwd=path,
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
import sys
from pathlib import Path

_ = sys.stdin.read()
repo_root = Path(os.getcwd())
out_dir = repo_root / "tasksgodzilla"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "DISCOVERY.md").write_text("# Discovery\\n", encoding="utf-8")
(out_dir / "DISCOVERY_SUMMARY.json").write_text(json.dumps({"languages": ["python"]}), encoding="utf-8")
(out_dir / "ARCHITECTURE.md").write_text("# Architecture\\n", encoding="utf-8")
(out_dir / "API_REFERENCE.md").write_text("# API Reference\\n", encoding="utf-8")
(out_dir / "CI_NOTES.md").write_text("# CI Notes\\n", encoding="utf-8")
print("ok")
sys.exit(0)
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_api_onboard_can_run_discovery_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        _init_repo(repo)

        bin_dir = tmp / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        _write_opencode_stub(bin_dir)

        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_DEFAULT_ENGINE_ID", "opencode")
        monkeypatch.setenv("DEVGODZILLA_OPENCODE_MODEL", "zai-coding-plan/glm-4.6")

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )

        with TestClient(app) as client:  # type: ignore[arg-type]
            resp = client.post(
                f"/projects/{project.id}/actions/onboard",
                json={
                    "branch": "main",
                    "clone_if_missing": False,
                    "run_discovery_agent": True,
                    "discovery_pipeline": True,
                    "discovery_engine_id": "opencode",
                    "discovery_model": "zai-coding-plan/glm-4.6",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["discovery_success"] is True
            assert data["discovery_missing_outputs"] == []

        assert (repo / "tasksgodzilla" / "DISCOVERY.md").exists()
        assert (repo / "tasksgodzilla" / "DISCOVERY_SUMMARY.json").exists()

