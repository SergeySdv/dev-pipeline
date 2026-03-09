from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from devgodzilla.api.app import app
from devgodzilla.db.database import SQLiteDatabase


def _require_real_speckit_engine() -> tuple[str, str]:
    if os.environ.get("DEVGODZILLA_RUN_E2E_REAL_AGENT") != "1":
        pytest.skip("Set DEVGODZILLA_RUN_E2E_REAL_AGENT=1 to enable real-agent SpecKit tests.")

    engine_id = (os.environ.get("DEVGODZILLA_TEST_SPECKIT_ENGINE_ID") or "opencode").strip()
    model = (
        os.environ.get("DEVGODZILLA_TEST_SPECKIT_MODEL")
        or os.environ.get("DEVGODZILLA_OPENCODE_MODEL")
        or "zai-coding-plan/glm-5"
    ).strip()

    if engine_id != "opencode":
        pytest.skip(f"Real-agent SpecKit lifecycle test currently supports opencode only; got {engine_id!r}.")
    if shutil.which("opencode") is None:
        pytest.skip("opencode is required for real-agent SpecKit tests.")

    return engine_id, model


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=path, check=True)
    (path / "README.md").write_text("# Demo\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        env={
            "GIT_AUTHOR_NAME": "tester",
            "GIT_AUTHOR_EMAIL": "tester@example.com",
            "GIT_COMMITTER_NAME": "tester",
            "GIT_COMMITTER_EMAIL": "tester@example.com",
        },
    )


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
@pytest.mark.integration
def test_project_scoped_speckit_lifecycle_integrates_real_db_and_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests

    engine_id, model = _require_real_speckit_engine()
    db_path = tmp_path / "devgodzilla.sqlite"
    repo_root = tmp_path / "repo"
    _init_git_repo(repo_root)

    monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
    monkeypatch.setenv("DEVGODZILLA_DEFAULT_ENGINE_ID", engine_id)
    monkeypatch.setenv("DEVGODZILLA_SPECKIT_ENGINE_ID", engine_id)
    monkeypatch.setenv("DEVGODZILLA_OPENCODE_MODEL", model)
    _reset_config_for_tests()

    db = SQLiteDatabase(db_path)
    db.init_schema()
    project = db.create_project(
        name="SpecKit Integration Project",
        git_url="https://github.com/example/speckit.git",
        base_branch="main",
        local_path=str(repo_root),
    )

    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            init_resp = client.post(f"/projects/{project.id}/speckit/init")
            assert init_resp.status_code == 200
            assert init_resp.json()["success"] is True

            specify_resp = client.post(
                f"/projects/{project.id}/speckit/specify",
                json={"description": "Add user authentication with OAuth2 support"},
            )
            assert specify_resp.status_code == 200
            specify_data = specify_resp.json()
            assert specify_data["success"] is True
            assert specify_data["spec_run_id"] is not None
            assert specify_data["worktree_path"] is not None

            spec_run_id = int(specify_data["spec_run_id"])
            worktree_path = Path(specify_data["worktree_path"])
            spec_path = Path(specify_data["spec_path"])
            assert worktree_path.exists()
            assert spec_path.exists()
            assert spec_path.is_relative_to(worktree_path)
            spec_content = spec_path.read_text(encoding="utf-8")
            assert "Add user authentication with OAuth2 support" in spec_content
            assert "[Brief Title]" not in spec_content
            assert "[Describe this user journey in plain language]" not in spec_content
            assert "System MUST [specific capability" not in spec_content

            clarify_resp = client.post(
                f"/projects/{project.id}/speckit/clarify",
                json={
                    "spec_path": str(spec_path),
                    "spec_run_id": spec_run_id,
                    "entries": [{"question": "Auth provider?", "answer": "Google OAuth2"}],
                },
            )
            assert clarify_resp.status_code == 200
            assert clarify_resp.json()["success"] is True
            assert clarify_resp.json()["spec_run_id"] == spec_run_id
            assert "Google OAuth2" in spec_path.read_text(encoding="utf-8")

            plan_resp = client.post(
                f"/projects/{project.id}/speckit/plan",
                json={"spec_path": str(spec_path), "spec_run_id": spec_run_id},
            )
            assert plan_resp.status_code == 200
            plan_data = plan_resp.json()
            assert plan_data["success"] is True
            assert plan_data["spec_run_id"] == spec_run_id
            assert plan_data["worktree_path"] == str(worktree_path)
            plan_path = Path(plan_data["plan_path"])
            assert plan_path.exists()
            plan_content = plan_path.read_text(encoding="utf-8")
            assert "[Extract from feature spec:" not in plan_content
            assert "[REMOVE IF UNUSED]" not in plan_content
            assert "NEEDS CLARIFICATION" not in plan_content

            tasks_resp = client.post(
                f"/projects/{project.id}/speckit/tasks",
                json={"plan_path": str(plan_path), "spec_run_id": spec_run_id},
            )
            assert tasks_resp.status_code == 200
            tasks_data = tasks_resp.json()
            assert tasks_data["success"] is True
            assert tasks_data["spec_run_id"] == spec_run_id
            assert tasks_data["worktree_path"] == str(worktree_path)
            tasks_path = Path(tasks_data["tasks_path"])
            assert tasks_path.exists()
            tasks_content = tasks_path.read_text(encoding="utf-8")
            assert "IMPORTANT: The tasks below are SAMPLE TASKS" not in tasks_content
            assert "Initialize [language] project with [framework] dependencies" not in tasks_content
            assert "Contract test for [endpoint]" not in tasks_content

            checklist_resp = client.post(
                f"/projects/{project.id}/speckit/checklist",
                json={"spec_path": str(spec_path), "spec_run_id": spec_run_id},
            )
            assert checklist_resp.status_code == 200
            checklist_data = checklist_resp.json()
            assert checklist_data["success"] is True
            assert checklist_data["spec_run_id"] == spec_run_id
            checklist_path = Path(checklist_data["checklist_path"])
            assert checklist_path.exists()
            checklist_content = checklist_path.read_text(encoding="utf-8")
            assert "Code follows project style guide" not in checklist_content

            analyze_resp = client.post(
                f"/projects/{project.id}/speckit/analyze",
                json={
                    "spec_path": str(spec_path),
                    "plan_path": str(plan_path),
                    "tasks_path": str(tasks_path),
                    "spec_run_id": spec_run_id,
                },
            )
            assert analyze_resp.status_code == 200
            analyze_data = analyze_resp.json()
            assert analyze_data["success"] is True
            assert analyze_data["spec_run_id"] == spec_run_id
            report_path = Path(analyze_data["report_path"])
            assert report_path.exists()
            report_content = report_path.read_text(encoding="utf-8")
            assert "(To be generated)" not in report_content

            implement_resp = client.post(
                f"/projects/{project.id}/speckit/implement",
                json={"spec_path": str(spec_path), "spec_run_id": spec_run_id},
            )
            assert implement_resp.status_code == 200
            implement_data = implement_resp.json()
            assert implement_data["success"] is True
            assert implement_data["spec_run_id"] == spec_run_id
            assert implement_data["worktree_path"] == str(worktree_path)
            assert implement_data["protocol_id"] is not None
            assert implement_data["protocol_root"] is not None
            assert implement_data["step_count"] >= 1
            assert Path(implement_data["metadata_path"]).exists()

        spec_run = db.get_spec_run(spec_run_id)
        assert spec_run.worktree_path == str(worktree_path)
        assert spec_run.protocol_run_id == implement_data["protocol_id"]

        protocol = db.get_protocol_run(implement_data["protocol_id"])
        assert protocol.worktree_path == str(worktree_path)
        assert db.list_step_runs(protocol.id)
    finally:
        app.dependency_overrides.clear()
        _reset_config_for_tests()
