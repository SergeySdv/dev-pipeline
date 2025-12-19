
import pytest
import tempfile
import os
from pathlib import Path
from contextlib import contextmanager
from fastapi.testclient import TestClient
from devgodzilla.api.app import app
from devgodzilla.db.database import SQLiteDatabase
from devgodzilla.api.dependencies import get_db, require_api_token
from devgodzilla.models.domain import Project, Sprint

@contextmanager
def temp_db_context():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_api.db"
        db = SQLiteDatabase(str(db_path))
        db.init_schema()
        yield db

@pytest.fixture
def client_with_db():
    with temp_db_context() as db:
        # Override DB dependency
        app.dependency_overrides[get_db] = lambda: db
        # Override Auth to bypass token check
        app.dependency_overrides[require_api_token] = lambda: {"sub": "test"}
        
        client = TestClient(app)
        yield client, db
        app.dependency_overrides.clear()

def test_import_tasks_api(client_with_db):
    client, db = client_with_db
    
    # 1. Create project & sprint via DB directly
    project = db.create_project("test-proj", "git", "main")
    sprint = db.create_sprint(project.id, "Sprint 1", status="active")
    
    # 2. Create a SpecKit file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] Imported Task (5 pts)")
        spec_path = f.name
        
    try:
        # 3. Call API
        # Note: We pass absolute path to temp file
        response = client.post(
            f"/sprints/{sprint.id}/actions/import-tasks",
            json={"spec_path": spec_path, "overwrite_existing": False}
        )
        
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        assert data["tasks_synced"] == 1
        assert data["sprint_id"] == sprint.id
        
        # 4. Verify in DB
        tasks = db.list_tasks(sprint_id=sprint.id)
        assert len(tasks) == 1
        assert tasks[0].title == "Imported Task"
        assert tasks[0].story_points == 5
        
    finally:
        if os.path.exists(spec_path):
            os.unlink(spec_path)

def test_import_tasks_sprint_not_found(client_with_db):
    client, db = client_with_db
    response = client.post(
        "/sprints/999/actions/import-tasks",
        json={"spec_path": "/tmp/dummy"}
    )
    assert response.status_code == 404
