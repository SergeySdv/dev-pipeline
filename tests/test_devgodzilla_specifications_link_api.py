"""
Tests for specification <-> sprint link API behavior.
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
def test_link_and_unlink_specification_sprint_persists(monkeypatch: pytest.MonkeyPatch) -> None:
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
        sprint = db.create_sprint(project_id=project.id, name="Sprint 1")

        spec_dir = repo / "specs" / "001-feature-alpha"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Feature Alpha")

        spec_run = db.create_spec_run(
            project_id=project.id,
            spec_name="001-feature-alpha",
            status="draft",
            base_branch="main",
            spec_root=str(spec_dir),
            spec_path=str(spec_file),
        )

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            before = client.get(f"/specifications?project_id={project.id}")
            assert before.status_code == 200
            before_item = next(
                item for item in before.json()["items"] if item["id"] == spec_run.id
            )
            assert before_item["sprint_id"] is None

            link = client.post(
                f"/specifications/{spec_run.id}/link-sprint",
                json={"sprint_id": sprint.id},
            )
            assert link.status_code == 200
            link_payload = link.json()
            assert link_payload["success"] is True
            assert link_payload["persisted"] is True
            assert link_payload["sprint_id"] == sprint.id

            filtered = client.get(f"/specifications?sprint_id={sprint.id}")
            assert filtered.status_code == 200
            filtered_items = filtered.json()["items"]
            assert any(item["id"] == spec_run.id for item in filtered_items)

            linked = client.get(f"/specifications?project_id={project.id}")
            assert linked.status_code == 200
            linked_item = next(
                item for item in linked.json()["items"] if item["id"] == spec_run.id
            )
            assert linked_item["sprint_id"] == sprint.id
            assert linked_item["sprint_name"] == "Sprint 1"

            unlink = client.post(
                f"/specifications/{spec_run.id}/link-sprint",
                json={"sprint_id": None},
            )
            assert unlink.status_code == 200
            assert unlink.json()["persisted"] is True

            after_unlink = client.get(f"/specifications?sprint_id={sprint.id}")
            assert after_unlink.status_code == 200
            assert all(item["id"] != spec_run.id for item in after_unlink.json()["items"])
