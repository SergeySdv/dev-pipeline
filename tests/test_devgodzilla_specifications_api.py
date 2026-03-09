from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

try:
    from fastapi.testclient import TestClient
except Exception:
    TestClient = None

from devgodzilla.api.app import app
from devgodzilla.db.database import SQLiteDatabase


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_specification_content_includes_analysis_markdown(tmp_path: Path) -> None:
    db = SQLiteDatabase(tmp_path / "test.db")
    db.init_schema()

    project = db.create_project(
        name="Spec Review Project",
        git_url="https://github.com/example/spec-review.git",
        base_branch="main",
    )
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    db.update_project(project.id, local_path=str(repo_root))

    spec_dir = repo_root / "specs" / "0001-review-ready"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (spec_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (spec_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    (spec_dir / "checklist.md").write_text("# Checklist\n", encoding="utf-8")
    (spec_dir / "analysis.md").write_text("# Analysis\n\nReady for review.\n", encoding="utf-8")

    from devgodzilla.api.dependencies import get_db

    app.dependency_overrides[get_db] = lambda: db
    try:
        with patch(
            "devgodzilla.api.routes.specifications.SpecificationService.list_specs",
            return_value=[
                {
                    "id": 77,
                    "spec_run_id": 77,
                    "name": "review-ready",
                    "path": "specs/0001-review-ready",
                    "spec_path": "specs/0001-review-ready/spec.md",
                    "plan_path": "specs/0001-review-ready/plan.md",
                    "tasks_path": "specs/0001-review-ready/tasks.md",
                    "checklist_path": "specs/0001-review-ready/checklist.md",
                    "analysis_path": "specs/0001-review-ready/analysis.md",
                    "implement_path": "specs/0001-review-ready/_runtime",
                    "has_spec": True,
                    "has_plan": True,
                    "has_tasks": True,
                }
            ],
        ):
            with TestClient(app) as client:
                response = client.get("/specifications/77/content")

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_content"] == "# Analysis\n\nReady for review.\n"
    finally:
        app.dependency_overrides.clear()
