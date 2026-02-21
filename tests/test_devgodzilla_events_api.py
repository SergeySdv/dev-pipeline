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
def test_events_persist_and_recent(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.services.events import ProtocolStarted, get_event_bus

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
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-proto",
            status="pending",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(repo),
        )

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            get_event_bus().publish(ProtocolStarted(protocol_run_id=run.id, protocol_name=run.protocol_name))

            recent = client.get("/events/recent", params={"protocol_id": run.id, "limit": 10})
            assert recent.status_code == 200
            payload = recent.json()
            assert payload["events"]
            assert any(e["protocol_run_id"] == run.id for e in payload["events"])
            assert "T" in payload["events"][0]["created_at"]

            prot_events = client.get(f"/protocols/{run.id}/events")
            assert prot_events.status_code == 200
            payload_events = prot_events.json()
            assert any(e["event_type"] == "protocol_started" for e in payload_events)
            assert any(e["event_category"] == "planning" for e in payload_events)

            filtered_recent = client.get("/events/recent", params={"protocol_id": run.id, "category": "planning"})
            assert filtered_recent.status_code == 200
            filtered_payload = filtered_recent.json()
            assert filtered_payload["events"]
            assert all(e["event_category"] == "planning" for e in filtered_payload["events"])

            filtered_type = client.get(
                "/events/recent",
                params={"protocol_id": run.id, "event_type": "protocol_started"},
            )
            assert filtered_type.status_code == 200
            type_payload = filtered_type.json()
            assert type_payload["events"]
            assert all(e["event_type"] == "protocol_started" for e in type_payload["events"])


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_api_token_protects_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        repo.mkdir(parents=True, exist_ok=True)

        db = SQLiteDatabase(db_path)
        db.init_schema()
        db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.setenv("DEVGODZILLA_API_TOKEN", "secret")

        with TestClient(app) as client:  # type: ignore[arg-type]
            assert client.get("/health").status_code == 200

            assert client.get("/projects").status_code == 401

            authed = client.get("/projects", headers={"Authorization": "Bearer secret"})
            assert authed.status_code == 200
            assert authed.json()
