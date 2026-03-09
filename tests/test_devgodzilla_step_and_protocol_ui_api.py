from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
    from devgodzilla.api.app import app
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore
    app = None  # type: ignore


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_list_step_runs_returns_job_runs_for_step(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="running",
            base_branch="main",
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="completed",
            assigned_agent="opencode",
        )
        db.create_job_run(
            run_id="run-step-1",
            job_type="execute",
            status="succeeded",
            run_kind="engine",
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(f"/steps/{step.id}/runs")
                assert response.status_code == 200
                payload = response.json()
                assert len(payload) == 1
                assert payload[0]["run_id"] == "run-step-1"
                assert payload[0]["step_run_id"] == step.id
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_get_protocol_sprint_filters_protocol_linked_tasks_without_db_specific_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        sprint = db.create_sprint(project.id, "Sprint 1", status="active")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="running",
            base_branch="main",
        )
        db.create_task(
            project_id=project.id,
            title="Linked task",
            sprint_id=sprint.id,
            protocol_run_id=run.id,
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(f"/protocols/{run.id}/sprint")
                assert response.status_code == 200
                payload = response.json()
                assert payload is not None
                assert payload["id"] == sprint.id
                assert payload["name"] == "Sprint 1"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()
