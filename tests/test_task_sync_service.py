
import pytest
import tempfile
import os
from pathlib import Path
from contextlib import contextmanager
from devgodzilla.db.database import SQLiteDatabase
from devgodzilla.services.task_sync import TaskSyncService

@contextmanager
def temp_db_context():
    """Context manager to create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = SQLiteDatabase(db_path)
        db.init_schema()
        yield db

@contextmanager
def temp_file_context(content: str):
    """Context manager to create a temporary file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "tasks.md"
        with open(file_path, "w") as f:
            f.write(content)
        yield file_path

def create_test_project(db: SQLiteDatabase) -> int:
    project = db.create_project(
        name="test-project",
        git_url="https://github.com/test/test",
        base_branch="main"
    )
    return project.id

def create_test_sprint(db: SQLiteDatabase, project_id: int) -> int:
    sprint = db.create_sprint(
        project_id=project_id,
        name="Test Sprint",
        status="active"
    )
    return sprint.id

# Tests for parsing logic
def test_parse_simple_task():
    service = TaskSyncService(None)
    content = "- [ ] Simple Task"
    tasks = service.parse_task_markdown(content)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Simple Task"
    assert tasks[0]["board_status"] == "todo"
    assert tasks[0]["story_points"] is None

def test_parse_completed_task():
    service = TaskSyncService(None)
    content = "- [x] Completed Task"
    tasks = service.parse_task_markdown(content)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Completed Task"
    assert tasks[0]["board_status"] == "done"

def test_parse_points():
    service = TaskSyncService(None)
    content = """
- [ ] Task (3 pts)
- [ ] Another (5 points)
- [ ] Just number (8)
"""
    tasks = service.parse_task_markdown(content)
    assert len(tasks) == 3
    assert tasks[0]["story_points"] == 3
    assert tasks[0]["title"] == "Task"
    
    assert tasks[1]["story_points"] == 5
    assert tasks[1]["title"] == "Another"
    
    assert tasks[2]["story_points"] == 8
    assert tasks[2]["title"] == "Just number"

# Tests for sync logic
@pytest.mark.asyncio
async def test_import_speckit_tasks():
    with temp_db_context() as db:
        project_id = create_test_project(db)
        sprint_id = create_test_sprint(db, project_id)
        
        service = TaskSyncService(db)
        
        content = """
## Feature
- [ ] Task 1 (2 pts)
- [x] Task 2 (1 pt)
        """
        
        with temp_file_context(content) as spec_path:
            tasks = await service.import_speckit_tasks(
                project_id=project_id,
                spec_path=str(spec_path),
                sprint_id=sprint_id
            )
            
            assert len(tasks) == 2
            
            # Check DB
            db_tasks = db.list_tasks(sprint_id=sprint_id)
            assert len(db_tasks) == 2
            
            # Sort by title to ensure consistent indexing
            db_tasks.sort(key=lambda x: x.title)
            
            if db_tasks[0].title == "Task 1":
                t1, t2 = db_tasks[0], db_tasks[1]
            else:
                t1, t2 = db_tasks[1], db_tasks[0]
            
            assert t1.title == "Task 1"
            assert t1.story_points == 2
            assert t1.board_status == "todo"
            
            assert t2.title == "Task 2"
            assert t2.story_points == 1
            assert t2.board_status == "done"
            
            # Verify velocity update
            sprint = db.get_sprint(sprint_id)
            assert sprint.velocity_actual == 1

@pytest.mark.asyncio
async def test_import_overwrite():
    with temp_db_context() as db:
        project_id = create_test_project(db)
        sprint_id = create_test_sprint(db, project_id)
        service = TaskSyncService(db)
        
        # Initial import
        content1 = "- [ ] Task A"
        with temp_file_context(content1) as spec_path:
            await service.import_speckit_tasks(project_id, str(spec_path), sprint_id)
            
        assert len(db.list_tasks(sprint_id=sprint_id)) == 1
        
        # Re-import with overwrite
        content2 = """
- [ ] Task B
- [ ] Task C
        """
        with temp_file_context(content2) as spec_path:
            await service.import_speckit_tasks(
                project_id, 
                str(spec_path), 
                sprint_id,
                overwrite_existing=True
            )
            
        final_tasks = db.list_tasks(sprint_id=sprint_id)
        assert len(final_tasks) == 2
        titles = set(t.title for t in final_tasks)
        assert "Task A" not in titles
        assert "Task B" in titles
        assert "Task C" in titles
