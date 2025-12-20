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
def test_protocol_from_spec_creates_runtime_steps(monkeypatch: pytest.MonkeyPatch) -> None:
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

        spec_dir = repo / "specs" / "001-feature"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "spec.md").write_text("# Feature 001\n", encoding="utf-8")
        (spec_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (spec_dir / "tasks.md").write_text(
            "\n".join([
                "# Task List: Feature 001",
                "",
                "## Phase 1: Setup",
                "- [ ] Initialize scaffolding",
                "",
                "## Phase 2: Implementation",
                "- [ ] Implement feature core",
            ]) + "\n",
            encoding="utf-8",
        )

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            resp = client.post(
                "/protocols/from-spec",
                json={
                    "project_id": project.id,
                    "spec_path": str(spec_dir / "spec.md"),
                    "tasks_path": str(spec_dir / "tasks.md"),
                },
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["success"] is True
            assert payload["protocol"] is not None
            assert payload["step_count"] == 2

        run = db.get_protocol_run(payload["protocol"]["id"])
        assert run.protocol_root
        assert run.protocol_root.endswith("specs/001-feature/_runtime")
        runtime_root = repo / "specs" / "001-feature" / "_runtime"
        assert (runtime_root / "plan.md").exists()
        step_files = sorted(runtime_root.glob("step-*.md"))
        assert len(step_files) == 2

        steps = db.list_step_runs(run.id)
        assert [s.step_name for s in steps] == ["step-01-phase-1-setup", "step-02-phase-2-implementation"]
