"""
Tests for Project SpecKit API routes.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

try:
    from fastapi.testclient import TestClient
except Exception:
    TestClient = None

from devgodzilla.api.app import app
from devgodzilla.db.database import SQLiteDatabase


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
class TestProjectSpecKitAPI:
    """Tests for /projects/{project_id}/speckit/* endpoints."""

    @pytest.fixture
    def db(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(db_path)
        db.init_schema()
        return db

    @pytest.fixture
    def client(self, db: SQLiteDatabase):
        from devgodzilla.api.dependencies import get_db

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def sample_project(self, db: SQLiteDatabase, tmp_path: Path):
        project = db.create_project(
            name="SpecKit Test Project",
            git_url="https://github.com/example/test.git",
            base_branch="main",
        )
        # Set a local path for the project
        local_path = tmp_path / "repo"
        local_path.mkdir()
        (local_path / ".git").mkdir()  # Simulate git repo
        db.update_project(project.id, local_path=str(local_path))
        project = db.get_project(project.id)
        return project

    # ==================== Init Tests ====================

    def test_init_project_speckit_default_constitution(
        self, client, sample_project, tmp_path
    ):
        """Test SpecKit initialization with default constitution."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.spec_path = str(tmp_path / "specs" / ".specify")
            mock_result.constitution_hash = "abc123"
            mock_result.error = None
            mock_result.warnings = []
            mock_service.init_project.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(f"/projects/{sample_project.id}/speckit/init")

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["constitution_hash"] == "abc123"

    def test_init_project_speckit_custom_constitution(
        self, client, sample_project, tmp_path
    ):
        """Test SpecKit initialization with custom constitution."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.spec_path = str(tmp_path / "specs")
            mock_result.constitution_hash = "def456"
            mock_result.error = None
            mock_result.warnings = []
            mock_service.init_project.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(
                f"/projects/{sample_project.id}/speckit/init",
                json={"content": "# Custom Constitution\n\n- Rule 1\n- Rule 2"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True

    def test_init_project_speckit_no_local_path(self, client, db):
        """Test init fails when project has no local_path."""
        project = db.create_project(
            name="No Path Project",
            git_url="https://github.com/example/nopath.git",
            base_branch="main",
        )

        resp = client.post(f"/projects/{project.id}/speckit/init")
        assert resp.status_code == 400
        assert "no local path" in resp.json()["detail"].lower()

    # ==================== Constitution Tests ====================

    def test_get_constitution(self, client, sample_project):
        """Test getting project constitution."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_service.get_constitution.return_value = "# Constitution\n\nRules here"
            MockService.return_value = mock_service

            resp = client.get(f"/projects/{sample_project.id}/speckit/constitution")

            assert resp.status_code == 200
            data = resp.json()
            assert "Constitution" in data["content"]

    def test_get_constitution_not_found(self, client, sample_project):
        """Test getting constitution when none exists."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_service.get_constitution.return_value = None
            MockService.return_value = mock_service

            resp = client.get(f"/projects/{sample_project.id}/speckit/constitution")

            assert resp.status_code == 404

    def test_put_constitution(self, client, sample_project, tmp_path):
        """Test updating project constitution."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.spec_path = str(tmp_path / "specs")
            mock_result.constitution_hash = "newhash"
            mock_result.error = None
            mock_service.save_constitution.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.put(
                f"/projects/{sample_project.id}/speckit/constitution",
                json={"content": "# Updated Constitution"},
            )

            assert resp.status_code == 200
            assert resp.json()["success"] is True

    def test_sync_constitution(self, client, sample_project, tmp_path):
        """Test syncing constitution from policy."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.spec_path = str(tmp_path / "specs")
            mock_result.constitution_hash = "synchash"
            mock_result.error = None
            mock_result.warnings = []
            mock_service.save_constitution.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(f"/projects/{sample_project.id}/speckit/constitution/sync")

            assert resp.status_code == 200
            assert resp.json()["success"] is True

    # ==================== Specify Tests ====================

    def test_specify_success(self, client, sample_project, tmp_path):
        """Test successful spec generation."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.spec_path = str(tmp_path / "specs" / "0001-feature")
            mock_result.spec_number = 1
            mock_result.feature_name = "Test Feature"
            mock_result.spec_run_id = 123
            mock_result.worktree_path = str(tmp_path / "worktrees" / "0001")
            mock_result.branch_name = "spec/0001-test-feature"
            mock_result.base_branch = "main"
            mock_result.spec_root = str(tmp_path / "specs")
            mock_result.error = None
            mock_service.run_specify.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(
                f"/projects/{sample_project.id}/speckit/specify",
                json={
                    "description": "Add user authentication with OAuth2",
                    "feature_name": "OAuth Auth",
                    "base_branch": "main",
                },
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["spec_number"] == 1
            assert data["feature_name"] == "Test Feature"
            assert data["spec_run_id"] == 123

    def test_specify_minimal(self, client, sample_project, tmp_path):
        """Test spec generation with minimal parameters."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.spec_path = str(tmp_path / "specs" / "0001")
            mock_result.spec_number = 1
            mock_result.feature_name = "Feature"
            mock_result.spec_run_id = None
            mock_result.worktree_path = None
            mock_result.branch_name = None
            mock_result.base_branch = None
            mock_result.spec_root = str(tmp_path / "specs")
            mock_result.error = None
            mock_service.run_specify.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(
                f"/projects/{sample_project.id}/speckit/specify",
                json={"description": "Minimal spec description"},
            )

            assert resp.status_code == 200
            assert resp.json()["success"] is True

    # ==================== Plan Tests ====================

    def test_plan_success(self, client, sample_project, tmp_path):
        """Test successful plan generation."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.plan_path = str(tmp_path / "specs" / "0001" / "plan.md")
            mock_result.data_model_path = str(tmp_path / "specs" / "0001" / "data-model.md")
            mock_result.contracts_path = str(tmp_path / "specs" / "0001" / "contracts.md")
            mock_result.spec_run_id = 123
            mock_result.worktree_path = str(tmp_path / "worktree")
            mock_result.error = None
            mock_service.run_plan.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(
                f"/projects/{sample_project.id}/speckit/plan",
                json={"spec_path": "specs/0001-feature/spec.md"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["plan_path"] is not None

    # ==================== Tasks Tests ====================

    def test_tasks_success(self, client, sample_project, tmp_path):
        """Test successful tasks generation."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.tasks_path = str(tmp_path / "specs" / "0001" / "tasks.md")
            mock_result.task_count = 5
            mock_result.parallelizable_count = 2
            mock_result.spec_run_id = 123
            mock_result.worktree_path = str(tmp_path / "worktree")
            mock_result.error = None
            mock_service.run_tasks.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(
                f"/projects/{sample_project.id}/speckit/tasks",
                json={"plan_path": "specs/0001-feature/plan.md"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["task_count"] == 5
            assert data["parallelizable_count"] == 2

    # ==================== Clarify Tests ====================

    def test_clarify_success(self, client, sample_project, tmp_path):
        """Test successful clarifications update."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.spec_path = str(tmp_path / "specs" / "0001" / "spec.md")
            mock_result.clarifications_added = 3
            mock_result.spec_run_id = 123
            mock_result.worktree_path = None
            mock_result.error = None
            mock_service.run_clarify.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(
                f"/projects/{sample_project.id}/speckit/clarify",
                json={
                    "spec_path": "specs/0001-feature/spec.md",
                    "entries": [
                        {"question": "What auth method?", "answer": "OAuth2"},
                        {"question": "Which provider?", "answer": "Google"},
                    ],
                    "notes": "Resolved auth questions",
                },
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["clarifications_added"] == 3

    # ==================== Checklist Tests ====================

    def test_checklist_success(self, client, sample_project, tmp_path):
        """Test successful checklist generation."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.checklist_path = str(tmp_path / "specs" / "0001" / "checklist.md")
            mock_result.item_count = 8
            mock_result.spec_run_id = 123
            mock_result.worktree_path = None
            mock_result.error = None
            mock_service.run_checklist.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(
                f"/projects/{sample_project.id}/speckit/checklist",
                json={"spec_path": "specs/0001-feature/spec.md"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["item_count"] == 8

    # ==================== Analyze Tests ====================

    def test_analyze_success(self, client, sample_project, tmp_path):
        """Test successful analysis."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.report_path = str(tmp_path / "specs" / "0001" / "_runtime" / "analysis.md")
            mock_result.spec_run_id = 123
            mock_result.worktree_path = None
            mock_result.error = None
            mock_service.run_analyze.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(
                f"/projects/{sample_project.id}/speckit/analyze",
                json={
                    "spec_path": "specs/0001-feature/spec.md",
                    "plan_path": "specs/0001-feature/plan.md",
                    "tasks_path": "specs/0001-feature/tasks.md",
                },
            )

            assert resp.status_code == 200
            assert resp.json()["success"] is True

    # ==================== Implement Tests ====================

    def test_implement_success(self, client, sample_project, tmp_path):
        """Test successful implementation start."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.run_path = str(tmp_path / "specs" / "0001" / "_runtime" / "runs" / "001")
            mock_result.metadata_path = str(tmp_path / "specs" / "0001" / "_runtime" / "run-001.json")
            mock_result.spec_run_id = 123
            mock_result.worktree_path = str(tmp_path / "worktree")
            mock_result.error = None
            mock_service.run_implement.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(
                f"/projects/{sample_project.id}/speckit/implement",
                json={"spec_path": "specs/0001-feature/spec.md"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["run_path"] is not None

    def test_implement_error(self, client, sample_project):
        """Test implementation with error."""
        with patch("devgodzilla.api.routes.project_speckit.SpecificationService") as MockService:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.run_path = None
            mock_result.metadata_path = None
            mock_result.spec_run_id = None
            mock_result.worktree_path = None
            mock_result.error = "Worktree creation failed"
            mock_service.run_implement.return_value = mock_result
            MockService.return_value = mock_service

            resp = client.post(
                f"/projects/{sample_project.id}/speckit/implement",
                json={"spec_path": "specs/0001-feature/spec.md"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is False
            assert "Worktree creation failed" in data["error"]

    # ==================== Project Not Found Tests ====================

    def test_project_not_found(self, client, db):
        """Test error for non-existent project."""
        # The route raises KeyError which propagates as 500
        # This is a known behavior - we just verify it doesn't crash with 200
        with pytest.raises(Exception):
            client.get("/projects/99999/speckit/constitution")
