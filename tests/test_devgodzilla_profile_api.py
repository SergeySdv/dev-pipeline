"""
Tests for profile API endpoint.
"""

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
def test_profile_includes_env_identity_and_recent_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        repo.mkdir(parents=True, exist_ok=True)

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="created",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(repo / ".protocols" / "demo-protocol"),
        )
        db.append_event(
            protocol_run_id=protocol.id,
            project_id=project.id,
            event_type="step_started",
            message="Step execution started",
        )

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        monkeypatch.setenv("DEVGODZILLA_USER_NAME", "Ilya")
        monkeypatch.setenv("DEVGODZILLA_USER_EMAIL", "ilya@example.com")

        with TestClient(app) as client:  # type: ignore[arg-type]
            response = client.get("/profile")
            assert response.status_code == 200
            payload = response.json()

        assert payload["name"] == "Ilya"
        assert payload["email"] == "ilya@example.com"
        assert payload["activity"]
        assert payload["activity"][0]["action"] == "Step Started"
        assert "Step execution started" in payload["activity"][0]["target"]
