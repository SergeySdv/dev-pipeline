from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock

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
def test_list_step_runs_syncs_windmill_status(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.api.routes import steps as steps_route
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.windmill.client import JobStatus

    class FakeWindmill:
        def get_job(self, _job_id: str):
            return type(
                "Job",
                (),
                {
                    "status": JobStatus.COMPLETED,
                    "started_at": "2026-03-09T00:00:00Z",
                    "completed_at": "2026-03-09T00:01:00Z",
                    "result": {"ok": True},
                    "error": None,
                },
            )()

        def close(self):
            return None

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
            status="queued",
            run_kind="engine",
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
            windmill_job_id="wm-1",
        )
        monkeypatch.setattr(steps_route, "_build_windmill_client", lambda: FakeWindmill())

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(f"/steps/{step.id}/runs")
                assert response.status_code == 200
                payload = response.json()
                assert payload[0]["status"] == "succeeded"
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


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_retry_latest_step_uses_orchestrator_without_leaving_manual_pending_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db, get_service_context
    from devgodzilla.api.routes import protocols as protocols_route
    from devgodzilla.config import _reset_config_for_tests, load_config
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.services.base import ServiceContext

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
            status="blocked",
            base_branch="main",
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=0,
            step_name="step-01-demo",
            step_type="execute",
            status="blocked",
            assigned_agent="opencode",
        )

        calls: list[int] = []

        fake_orchestrator = Mock()

        def fake_retry_step(step_run_id: int):
            calls.append(step_run_id)
            db.update_protocol_status(run.id, "running")
            db.update_step_status(step_run_id, "running", retries=1)
            return type("Result", (), {"success": True, "error": None, "message": "retry started"})()

        fake_orchestrator.retry_step.side_effect = fake_retry_step
        monkeypatch.setattr(protocols_route, "_build_orchestrator", lambda ctx, db_dep: fake_orchestrator)

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_service_context] = lambda: ServiceContext(config=load_config())
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.post(f"/protocols/{run.id}/actions/retry_latest")
                assert response.status_code == 200
                payload = response.json()
                assert payload["step_run_id"] == step.id
                assert payload["step_name"] == step.step_name
                assert payload["message"] == "retry started"
                assert payload["retries"] == 1
                assert calls == [step.id]
                assert db.get_protocol_run(run.id).status == "running"
                assert db.get_step_run(step.id).status == "running"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_retry_latest_step_recovers_blocked_protocol_with_runnable_pending_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db, get_service_context
    from devgodzilla.api.routes import protocols as protocols_route
    from devgodzilla.config import _reset_config_for_tests, load_config
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.services.base import ServiceContext

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
            status="blocked",
            base_branch="main",
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=0,
            step_name="step-01-demo",
            step_type="execute",
            status="pending",
            assigned_agent="opencode",
        )
        db.update_step_status(step.id, "pending", retries=1)
        db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-02-demo",
            step_type="execute",
            status="pending",
            assigned_agent="opencode",
            depends_on=[step.id],
        )

        fake_orchestrator = Mock()
        calls: list[int] = []

        def fake_run_step(step_run_id: int):
            calls.append(step_run_id)
            db.update_step_status(step_run_id, "running", retries=1)
            return type("Result", (), {"success": True, "error": None, "message": "resumed pending step"})()

        fake_orchestrator.run_step.side_effect = fake_run_step
        monkeypatch.setattr(protocols_route, "_build_orchestrator", lambda ctx, db_dep: fake_orchestrator)

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_service_context] = lambda: ServiceContext(config=load_config())
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.post(f"/protocols/{run.id}/actions/retry_latest")
                assert response.status_code == 200
                payload = response.json()
                assert payload["step_run_id"] == step.id
                assert payload["step_name"] == step.step_name
                assert payload["message"] == "resumed pending step"
                assert payload["retries"] == 1
                assert calls == [step.id]
                assert db.get_protocol_run(run.id).status == "running"
                assert db.get_step_run(step.id).status == "running"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()
