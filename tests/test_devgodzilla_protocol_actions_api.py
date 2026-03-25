"""Tests for protocol action API routes."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

try:
    from fastapi.testclient import TestClient
except Exception:
    TestClient = None

from devgodzilla.api.app import app
from devgodzilla.db.database import SQLiteDatabase
from devgodzilla.models.domain import ProtocolStatus, StepStatus
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.execution import ExecutionResult


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
class TestProtocolActionsAPI:
    @pytest.fixture
    def db(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(db_path)
        db.init_schema()
        return db

    @pytest.fixture
    def client(self, db: SQLiteDatabase):
        from devgodzilla.api.dependencies import get_db, get_service_context

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_service_context] = lambda: ServiceContext(
            config=SimpleNamespace(
                windmill_enabled=False,
                windmill_url=None,
                windmill_token=None,
                windmill_workspace="devgodzilla",
            )
        )
        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def sample_protocol(self, db: SQLiteDatabase, tmp_path: Path):
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        project = db.create_project(
            name="Protocol API Project",
            git_url="https://github.com/example/test.git",
            base_branch="main",
            local_path=str(repo_path),
        )
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="test-protocol",
            status=ProtocolStatus.RUNNING,
            base_branch="main",
            worktree_path=str(repo_path),
            protocol_root=str(repo_path),
        )
        first_step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=0,
            step_name="Step 1",
            step_type="exec",
            status=StepStatus.PENDING,
        )
        db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="Step 2",
            step_type="exec",
            status=StepStatus.PENDING,
            depends_on=[first_step.id],
        )
        return run, first_step

    def test_get_next_step_previews_without_execution(self, client, sample_protocol):
        run, first_step = sample_protocol

        with patch("devgodzilla.api.routes.protocols.ExecutionService.execute_step") as execute_step:
            resp = client.get(f"/protocols/{run.id}/next-step")

        assert resp.status_code == 200
        assert resp.json() == {"step_run_id": first_step.id}
        execute_step.assert_not_called()

    def test_run_next_step_executes_next_step_in_local_mode(self, client, sample_protocol):
        run, first_step = sample_protocol

        with patch(
            "devgodzilla.api.routes.protocols.ExecutionService.execute_step",
            return_value=ExecutionResult(success=True, step_run_id=first_step.id, engine_id="stub"),
        ) as execute_step:
            resp = client.post(f"/protocols/{run.id}/actions/run_next_step", json={})

        assert resp.status_code == 200
        assert resp.json() == {"step_run_id": first_step.id}
        execute_step.assert_called_once_with(first_step.id)
