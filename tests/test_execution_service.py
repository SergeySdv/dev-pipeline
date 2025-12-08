from pathlib import Path
from unittest.mock import patch

from tasksgodzilla.domain import ProtocolStatus, StepStatus
from tasksgodzilla.services import ExecutionService
from tasksgodzilla.storage import Database


def test_execute_step_delegates_to_worker(tmp_path):
    """Test that execute_step delegates to the existing worker implementation."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.RUNNING, "main", None, None, None)
    step = db.create_step_run(run.id, 1, "step-1", "work", StepStatus.RUNNING, model=None)
    
    service = ExecutionService(db=db)
    
    with patch("tasksgodzilla.services.execution.handle_execute_step") as mock_handle:
        service.execute_step(step.id, job_id="test-job-456")
        
        # Verify delegation
        mock_handle.assert_called_once_with(step.id, db, job_id="test-job-456")


def test_execute_step_without_job_id(tmp_path):
    """Test that execute_step works without a job_id."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.RUNNING, "main", None, None, None)
    step = db.create_step_run(run.id, 1, "step-1", "work", StepStatus.RUNNING, model=None)
    
    service = ExecutionService(db=db)
    
    with patch("tasksgodzilla.services.execution.handle_execute_step") as mock_handle:
        service.execute_step(step.id)
        
        # Verify delegation with None job_id
        mock_handle.assert_called_once_with(step.id, db, job_id=None)
