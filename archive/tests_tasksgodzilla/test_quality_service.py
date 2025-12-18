from pathlib import Path
from unittest.mock import Mock, patch

from tasksgodzilla.domain import ProtocolStatus, StepStatus
from tasksgodzilla.services import QualityService
from tasksgodzilla.storage import Database


def test_run_for_step_run_service_exists(tmp_path):
    """Test that QualityService can be instantiated and has run_for_step_run method."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    service = QualityService(db=db)
    
    # Verify service has the run_for_step_run method
    assert hasattr(service, "run_for_step_run")
    assert callable(service.run_for_step_run)


def test_run_for_step_run_requires_db(tmp_path):
    """Test that run_for_step_run raises when db is not set."""
    service = QualityService(db=None)
    
    try:
        service.run_for_step_run(123)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "db is required" in str(e)


def test_evaluate_step_calls_run_quality_check(tmp_path, monkeypatch):
    """Test that evaluate_step calls run_quality_check with correct parameters."""
    protocol_root = tmp_path / "protocol"
    protocol_root.mkdir()
    (protocol_root / "step-1.md").write_text("# Step 1\n\nContent.", encoding="utf-8")
    
    workspace_root = tmp_path
    (workspace_root / "prompts").mkdir()
    (workspace_root / "prompts" / "quality-validator.prompt.md").write_text("QA prompt", encoding="utf-8")
    
    # Mock the config
    mock_config = Mock()
    mock_config.qa_model = "zai-coding-plan/glm-4.6"
    mock_config.max_tokens_per_step = 100000
    mock_config.max_tokens_per_protocol = 500000
    mock_config.token_budget_mode = "warn"
    
    monkeypatch.setattr("tasksgodzilla.services.quality.load_config", lambda: mock_config)
    
    service = QualityService()
    
    with patch("tasksgodzilla.services.quality.run_quality_check") as mock_qa:
        mock_qa.return_value = Mock(verdict="pass", report="All good")
        
        result = service.evaluate_step(
            protocol_root=protocol_root,
            step_filename="step-1.md",
            sandbox="read-only",
        )
        
        # Verify call
        assert mock_qa.called
        call_args = mock_qa.call_args
        assert call_args[1]["protocol_root"] == protocol_root
        assert call_args[1]["step_file"] == protocol_root / "step-1.md"
        assert call_args[1]["model"] == "zai-coding-plan/glm-4.6"
        assert call_args[1]["sandbox"] == "read-only"


def test_evaluate_step_uses_default_model(tmp_path, monkeypatch):
    """Test that evaluate_step uses default_model when config has no qa_model."""
    protocol_root = tmp_path / "protocol"
    protocol_root.mkdir()
    (protocol_root / "step-1.md").write_text("# Step 1\n\nContent.", encoding="utf-8")
    
    workspace_root = tmp_path
    (workspace_root / "prompts").mkdir()
    (workspace_root / "prompts" / "quality-validator.prompt.md").write_text("QA prompt", encoding="utf-8")
    
    # Mock the config with no qa_model
    mock_config = Mock()
    mock_config.qa_model = None
    mock_config.max_tokens_per_step = 100000
    mock_config.max_tokens_per_protocol = 500000
    mock_config.token_budget_mode = "warn"
    
    monkeypatch.setattr("tasksgodzilla.services.quality.load_config", lambda: mock_config)
    
    service = QualityService(default_model="custom-model")
    
    with patch("tasksgodzilla.services.quality.run_quality_check") as mock_qa:
        mock_qa.return_value = Mock(verdict="pass", report="All good")
        
        service.evaluate_step(
            protocol_root=protocol_root,
            step_filename="step-1.md",
        )
        
        # Verify custom model was used
        call_args = mock_qa.call_args
        assert call_args[1]["model"] == "custom-model"
