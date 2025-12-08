from unittest.mock import Mock

from tasksgodzilla.jobs import Job
from tasksgodzilla.services.platform import QueueService, TelemetryService


def test_queue_service_enqueue_plan_protocol():
    """Test QueueService.enqueue_plan_protocol."""
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-1", job_type="plan_protocol_job", payload={})
    
    service = QueueService(queue=mock_queue)
    job = service.enqueue_plan_protocol(protocol_run_id=123)
    
    mock_queue.enqueue.assert_called_once_with("plan_protocol_job", {"protocol_run_id": 123})
    assert job.job_id == "job-1"


def test_queue_service_enqueue_execute_step():
    """Test QueueService.enqueue_execute_step."""
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-2", job_type="execute_step_job", payload={})
    
    service = QueueService(queue=mock_queue)
    job = service.enqueue_execute_step(step_run_id=456)
    
    mock_queue.enqueue.assert_called_once_with("execute_step_job", {"step_run_id": 456})
    assert job.job_id == "job-2"


def test_queue_service_enqueue_run_quality():
    """Test QueueService.enqueue_run_quality."""
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-3", job_type="run_quality_job", payload={})
    
    service = QueueService(queue=mock_queue)
    job = service.enqueue_run_quality(step_run_id=789)
    
    mock_queue.enqueue.assert_called_once_with("run_quality_job", {"step_run_id": 789})
    assert job.job_id == "job-3"


def test_queue_service_enqueue_project_setup():
    """Test QueueService.enqueue_project_setup."""
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-4", job_type="project_setup_job", payload={})
    
    service = QueueService(queue=mock_queue)
    job = service.enqueue_project_setup(project_id=111)
    
    mock_queue.enqueue.assert_called_once_with("project_setup_job", {"project_id": 111})
    assert job.job_id == "job-4"


def test_queue_service_enqueue_project_setup_with_protocol():
    """Test QueueService.enqueue_project_setup with protocol_run_id."""
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-5", job_type="project_setup_job", payload={})
    
    service = QueueService(queue=mock_queue)
    job = service.enqueue_project_setup(project_id=111, protocol_run_id=222)
    
    mock_queue.enqueue.assert_called_once_with("project_setup_job", {"project_id": 111, "protocol_run_id": 222})
    assert job.job_id == "job-5"


def test_queue_service_enqueue_open_pr():
    """Test QueueService.enqueue_open_pr."""
    mock_queue = Mock()
    mock_queue.enqueue.return_value = Job(job_id="job-6", job_type="open_pr_job", payload={})
    
    service = QueueService(queue=mock_queue)
    job = service.enqueue_open_pr(protocol_run_id=333)
    
    mock_queue.enqueue.assert_called_once_with("open_pr_job", {"protocol_run_id": 333})
    assert job.job_id == "job-6"


def test_telemetry_service_observe_tokens():
    """Test TelemetryService.observe_tokens delegates to metrics."""
    from unittest.mock import patch
    
    service = TelemetryService()
    
    with patch("tasksgodzilla.services.platform.telemetry.metrics") as mock_metrics:
        service.observe_tokens("planning", "gpt-5.1-high", 1500)
        
        mock_metrics.observe_tokens.assert_called_once_with("planning", "gpt-5.1-high", 1500)
