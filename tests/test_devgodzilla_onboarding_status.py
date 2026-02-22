import tempfile
from pathlib import Path
from typing import Any, Optional

import pytest

try:
    from fastapi.testclient import TestClient
    from devgodzilla.api.app import app
except ImportError:
    TestClient = None
    app = None


def _setup_db_and_project(tmp: Path, *, local_path: Optional[str] = None, constitution_hash: Optional[str] = None):
    from devgodzilla.db.database import SQLiteDatabase

    db_path = tmp / "devgodzilla.sqlite"
    db = SQLiteDatabase(db_path)
    db.init_schema()

    project = db.create_project(
        name="demo",
        git_url="https://example.com/repo.git",
        base_branch="main",
        local_path=local_path,
    )
    if constitution_hash:
        db.update_project(project.id, constitution_hash=constitution_hash)
        project = db.get_project(project.id)
    return db, project


def _insert_event(db, project_id: int, event_type: str, message: str = "", protocol_run_id: Optional[int] = None):
    db.append_event(
        protocol_run_id=protocol_run_id,
        event_type=event_type,
        message=message or event_type,
        project_id=project_id,
    )


def _get_onboarding(client, project_id: int) -> dict:
    resp = client.get(f"/projects/{project_id}/onboarding")
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
class TestOnboardingStageStatus:

    def test_repo_pending_by_default(self, monkeypatch, tmp_path):
        db, project = _setup_db_and_project(tmp_path)
        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(tmp_path / "devgodzilla.sqlite"))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                repo_stage = data["stages"][0]
                assert repo_stage["name"] == "Repository Setup"
                assert repo_stage["status"] == "pending"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_repo_running_when_started(self, monkeypatch, tmp_path):
        db, project = _setup_db_and_project(tmp_path)
        _insert_event(db, project.id, "onboarding_started")
        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(tmp_path / "devgodzilla.sqlite"))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                assert data["stages"][0]["status"] == "running"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_repo_completed_when_has_local_path(self, monkeypatch, tmp_path):
        db, project = _setup_db_and_project(tmp_path, local_path="/tmp/repo")
        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(tmp_path / "devgodzilla.sqlite"))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                assert data["stages"][0]["status"] == "completed"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_discovery_skipped(self, monkeypatch, tmp_path):
        db, project = _setup_db_and_project(tmp_path, local_path="/tmp/repo", constitution_hash="abc123")
        _insert_event(db, project.id, "discovery_skipped")
        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(tmp_path / "devgodzilla.sqlite"))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                discovery = next(s for s in data["stages"] if s["name"] == "Discovery")
                assert discovery["status"] == "skipped"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_discovery_running(self, monkeypatch, tmp_path):
        db, project = _setup_db_and_project(tmp_path, local_path="/tmp/repo", constitution_hash="abc123")
        _insert_event(db, project.id, "discovery_started")
        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(tmp_path / "devgodzilla.sqlite"))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                discovery = next(s for s in data["stages"] if s["name"] == "Discovery")
                assert discovery["status"] == "running"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_discovery_failed(self, monkeypatch, tmp_path):
        db, project = _setup_db_and_project(tmp_path, local_path="/tmp/repo", constitution_hash="abc123")
        _insert_event(db, project.id, "discovery_failed")
        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(tmp_path / "devgodzilla.sqlite"))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                discovery = next(s for s in data["stages"] if s["name"] == "Discovery")
                assert discovery["status"] == "failed"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_discovery_completed(self, monkeypatch, tmp_path):
        db, project = _setup_db_and_project(tmp_path, local_path="/tmp/repo", constitution_hash="abc123")
        _insert_event(db, project.id, "discovery_started")
        _insert_event(db, project.id, "discovery_completed")
        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(tmp_path / "devgodzilla.sqlite"))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                discovery = next(s for s in data["stages"] if s["name"] == "Discovery")
                assert discovery["status"] == "completed"
        finally:
            app.dependency_overrides.pop(get_db, None)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
class TestOnboardingOverallStatus:

    def _setup(self, monkeypatch, tmp_path, *, local_path=None, constitution_hash=None):
        db, project = _setup_db_and_project(tmp_path, local_path=local_path, constitution_hash=constitution_hash)
        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(tmp_path / "devgodzilla.sqlite"))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        return db, project

    def test_failed_overrides_all(self, monkeypatch, tmp_path):
        db, project = self._setup(monkeypatch, tmp_path, local_path="/tmp/repo", constitution_hash="abc")
        _insert_event(db, project.id, "discovery_failed")

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                assert data["status"] == "failed"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_running_when_any_running(self, monkeypatch, tmp_path):
        db, project = self._setup(monkeypatch, tmp_path, local_path="/tmp/repo", constitution_hash="abc")
        _insert_event(db, project.id, "discovery_started")

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                assert data["status"] == "running"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_completed_when_all_completed_or_skipped(self, monkeypatch, tmp_path):
        db, project = self._setup(monkeypatch, tmp_path, local_path="/tmp/repo", constitution_hash="abc")
        _insert_event(db, project.id, "onboarding_repo_ready")
        _insert_event(db, project.id, "onboarding_speckit_initialized")
        _insert_event(db, project.id, "discovery_completed")

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                assert data["status"] == "completed"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_pending_default(self, monkeypatch, tmp_path):
        db, project = self._setup(monkeypatch, tmp_path)

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                assert data["status"] == "pending"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_blocked_with_blocking_clarifications(self, monkeypatch, tmp_path):
        db, project = self._setup(monkeypatch, tmp_path, local_path="/tmp/repo", constitution_hash="abc")
        _insert_event(db, project.id, "discovery_completed")

        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="test",
            status="running",
            base_branch="main",
        )
        db.upsert_clarification(
            scope="project",
            project_id=project.id,
            protocol_run_id=run.id,
            key="test-clarification",
            question="What auth method?",
            blocking=True,
        )

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                assert data["status"] == "blocked"
                assert data["blocking_clarifications"] > 0
        finally:
            app.dependency_overrides.pop(get_db, None)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
class TestOnboardingEdgeCases:

    def _setup(self, monkeypatch, tmp_path, *, local_path=None, constitution_hash=None):
        db, project = _setup_db_and_project(tmp_path, local_path=local_path, constitution_hash=constitution_hash)
        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(tmp_path / "devgodzilla.sqlite"))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        return db, project

    def test_failed_plus_blocked_gives_failed_priority(self, monkeypatch, tmp_path):
        db, project = self._setup(monkeypatch, tmp_path, local_path="/tmp/repo", constitution_hash="abc")
        _insert_event(db, project.id, "onboarding_failed")
        _insert_event(db, project.id, "discovery_completed")

        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="test",
            status="running",
            base_branch="main",
        )
        db.upsert_clarification(
            scope="project",
            project_id=project.id,
            protocol_run_id=run.id,
            key="blocker",
            question="Blocker?",
            blocking=True,
        )

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                assert data["status"] == "failed"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_discovery_skipped_plus_all_completed_gives_completed(self, monkeypatch, tmp_path):
        db, project = self._setup(monkeypatch, tmp_path, local_path="/tmp/repo", constitution_hash="abc")
        _insert_event(db, project.id, "onboarding_repo_ready")
        _insert_event(db, project.id, "onboarding_speckit_initialized")
        _insert_event(db, project.id, "discovery_skipped")

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                assert data["status"] == "completed"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_clarifications_pending_when_repo_pending(self, monkeypatch, tmp_path):
        db, project = self._setup(monkeypatch, tmp_path)

        from devgodzilla.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                data = _get_onboarding(client, project.id)
                clarifications = next(s for s in data["stages"] if s["name"] == "Clarifications")
                assert clarifications["status"] == "pending"
        finally:
            app.dependency_overrides.pop(get_db, None)
