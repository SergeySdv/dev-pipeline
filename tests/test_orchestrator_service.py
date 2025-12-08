from pathlib import Path
from unittest.mock import Mock

from tasksgodzilla.domain import ProtocolStatus, StepStatus
from tasksgodzilla.jobs import Job
from tasksgodzilla.services import OrchestratorService
from tasksgodzilla.storage import Database


def test_create_protocol_run(tmp_path):
    """Test creating a protocol run via OrchestratorService."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    
    service = OrchestratorService(db=db)
    run = service.create_protocol_run(
        project_id=project.id,
        protocol_name="test-protocol",
        status=ProtocolStatus.PENDING,
        base_branch="main",
        description="Test protocol",
    )
    
    assert run.id is not None
    assert run.protocol_name == "test-protocol"
    assert run.status == ProtocolStatus.PENDING
    assert run.base_branch == "main"
    
    # Verify it's persisted
    fetched = db.get_protocol_run(run.id)
    assert fetched.protocol_name == "test-protocol"


def test_start_protocol_run_enqueues_planning(tmp_path):
    """Test starting a protocol transitions status and enqueues planning job."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None)
    
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-123", job_type="plan_protocol_job", payload={})
    
    service = OrchestratorService(db=db)
    job = service.start_protocol_run(run.id, queue=mock_queue)
    
    # Verify status transition
    updated_run = db.get_protocol_run(run.id)
    assert updated_run.status == ProtocolStatus.PLANNING
    
    # Verify queue call
    mock_queue.enqueue.assert_called_once_with("plan_protocol_job", {"protocol_run_id": run.id})
    assert job.job_id == "job-123"


def test_start_protocol_run_rejects_invalid_status(tmp_path):
    """Test that starting a protocol fails when status is invalid."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.RUNNING, "main", None, None, None)
    
    mock_queue = Mock()
    service = OrchestratorService(db=db)
    
    try:
        service.start_protocol_run(run.id, queue=mock_queue)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "already running or terminal" in str(e)


def test_enqueue_next_step_selects_pending(tmp_path):
    """Test that enqueue_next_step selects the first pending step."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PLANNED, "main", None, None, None)
    
    step1 = db.create_step_run(run.id, 1, "step-1", "work", StepStatus.PENDING, model=None)
    step2 = db.create_step_run(run.id, 2, "step-2", "work", StepStatus.PENDING, model=None)
    
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-456", job_type="execute_step_job", payload={})
    
    service = OrchestratorService(db=db)
    step, job = service.enqueue_next_step(run.id, queue=mock_queue)
    
    # Should select step1 (first pending)
    assert step.id == step1.id
    assert step.status == StepStatus.RUNNING
    
    # Verify protocol status updated
    updated_run = db.get_protocol_run(run.id)
    assert updated_run.status == ProtocolStatus.RUNNING
    
    # Verify queue call
    mock_queue.enqueue.assert_called_once_with("execute_step_job", {"step_run_id": step1.id})


def test_enqueue_next_step_raises_when_no_pending(tmp_path):
    """Test that enqueue_next_step raises when no pending steps exist."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PLANNED, "main", None, None, None)
    
    db.create_step_run(run.id, 1, "step-1", "work", StepStatus.COMPLETED, model=None)
    
    mock_queue = Mock()
    service = OrchestratorService(db=db)
    
    try:
        service.enqueue_next_step(run.id, queue=mock_queue)
        assert False, "Expected LookupError"
    except LookupError as e:
        assert "No pending or failed steps" in str(e)


def test_retry_latest_step_requeues_failed(tmp_path):
    """Test that retry_latest_step retries the most recent failed step."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.BLOCKED, "main", None, None, None)
    
    step1 = db.create_step_run(run.id, 1, "step-1", "work", StepStatus.COMPLETED, model=None)
    step2 = db.create_step_run(run.id, 2, "step-2", "work", StepStatus.FAILED, model=None)
    step3 = db.create_step_run(run.id, 3, "step-3", "work", StepStatus.PENDING, model=None)
    
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-789", job_type="execute_step_job", payload={})
    
    service = OrchestratorService(db=db)
    step, job = service.retry_latest_step(run.id, queue=mock_queue)
    
    # Should select step2 (most recent failed)
    assert step.id == step2.id
    assert step.status == StepStatus.RUNNING
    assert step.retries == 1
    
    # Verify protocol status updated
    updated_run = db.get_protocol_run(run.id)
    assert updated_run.status == ProtocolStatus.RUNNING


def test_pause_resume_cancel_transitions(tmp_path):
    """Test pause, resume, and cancel lifecycle transitions."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.RUNNING, "main", None, None, None)
    
    service = OrchestratorService(db=db)
    
    # Pause
    paused = service.pause_protocol(run.id)
    assert paused.status == ProtocolStatus.PAUSED
    
    # Resume
    resumed = service.resume_protocol(run.id)
    assert resumed.status == ProtocolStatus.RUNNING
    
    # Cancel
    cancelled = service.cancel_protocol(run.id)
    assert cancelled.status == ProtocolStatus.CANCELLED


def test_cancel_protocol_cancels_in_flight_steps(tmp_path):
    """Test that cancelling a protocol also cancels in-flight steps."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.RUNNING, "main", None, None, None)
    
    step1 = db.create_step_run(run.id, 1, "step-1", "work", StepStatus.COMPLETED, model=None)
    step2 = db.create_step_run(run.id, 2, "step-2", "work", StepStatus.RUNNING, model=None)
    step3 = db.create_step_run(run.id, 3, "step-3", "work", StepStatus.PENDING, model=None)
    
    service = OrchestratorService(db=db)
    service.cancel_protocol(run.id)
    
    # Verify step statuses
    updated_step1 = db.get_step_run(step1.id)
    updated_step2 = db.get_step_run(step2.id)
    updated_step3 = db.get_step_run(step3.id)
    
    assert updated_step1.status == StepStatus.COMPLETED  # Unchanged
    assert updated_step2.status == StepStatus.CANCELLED
    assert updated_step3.status == StepStatus.CANCELLED


def test_run_step_transitions_and_enqueues(tmp_path):
    """Test that run_step transitions a step to RUNNING and enqueues execution."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PLANNED, "main", None, None, None)
    step = db.create_step_run(run.id, 1, "step-1", "work", StepStatus.PENDING, model=None)
    
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-abc", job_type="execute_step_job", payload={})
    
    service = OrchestratorService(db=db)
    job = service.run_step(step.id, queue=mock_queue)
    
    # Verify step status
    updated_step = db.get_step_run(step.id)
    assert updated_step.status == StepStatus.RUNNING
    
    # Verify protocol status
    updated_run = db.get_protocol_run(run.id)
    assert updated_run.status == ProtocolStatus.RUNNING
    
    # Verify queue call
    mock_queue.enqueue.assert_called_once_with("execute_step_job", {"step_run_id": step.id})


def test_run_step_qa_transitions_and_enqueues(tmp_path):
    """Test that run_step_qa transitions a step to NEEDS_QA and enqueues QA job."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.RUNNING, "main", None, None, None)
    step = db.create_step_run(run.id, 1, "step-1", "work", StepStatus.RUNNING, model=None)
    
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-qa", job_type="run_quality_job", payload={})
    
    service = OrchestratorService(db=db)
    job = service.run_step_qa(step.id, queue=mock_queue)
    
    # Verify step status
    updated_step = db.get_step_run(step.id)
    assert updated_step.status == StepStatus.NEEDS_QA
    
    # Verify queue call
    mock_queue.enqueue.assert_called_once_with("run_quality_job", {"step_run_id": step.id})


def test_trigger_step_inline_fallback(tmp_path, monkeypatch):
    """Test that trigger_step falls back to inline execution when no queue is unavailable."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.RUNNING, "main", None, None, None)
    step = db.create_step_run(run.id, 1, "step-1", "work", StepStatus.PENDING, model=None)

    # Mock handler and config
    mock_handle_exec = Mock()
    monkeypatch.setattr("tasksgodzilla.workers.codex_worker.handle_execute_step", mock_handle_exec)
    
    # Mock config to have no Redis
    mock_config = Mock(redis_url=None)
    monkeypatch.setattr("tasksgodzilla.services.orchestrator.load_config", Mock(return_value=mock_config))

    service = OrchestratorService(db=db)
    result = service.trigger_step(step.id, run.id, source="test", inline_depth=0)

    assert result == {"inline": True, "target_step_id": step.id}
    
    # Verify handler called
    # We can't easily assert call args on local import unless we mock the module?
    # monkeypatching tasksgodzilla.workers.codex_worker.handle_execute_step works 
    # because the function imports from that module.
    mock_handle_exec.assert_called_once()
    
    # Verify status updated
    updated_step = db.get_step_run(step.id)
    assert updated_step.status == StepStatus.RUNNING
    assert updated_step.summary == "Triggered (inline)"

