from pathlib import Path

from tasksgodzilla.domain import ProtocolStatus
from tasksgodzilla.services import SpecService
from tasksgodzilla.storage import Database


def test_build_from_protocol_files(tmp_path):
    """Test building a spec from protocol step files."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None)
    
    # Create a protocol directory with step files
    protocol_root = tmp_path / "protocol"
    protocol_root.mkdir()
    (protocol_root / "01-first-step.md").write_text("# First Step\n\nDo something.", encoding="utf-8")
    (protocol_root / "02-second-step.md").write_text("# Second Step\n\nDo more.", encoding="utf-8")
    
    service = SpecService(db=db)
    spec = service.build_from_protocol_files(run.id, protocol_root)
    
    # Verify spec structure
    assert "steps" in spec
    assert len(spec["steps"]) == 2
    assert spec["steps"][0]["name"] == "01-first-step.md"
    assert spec["steps"][1]["name"] == "02-second-step.md"
    
    # Verify it's persisted in template_config
    updated_run = db.get_protocol_run(run.id)
    assert updated_run.template_config is not None
    assert "protocol_spec" in updated_run.template_config
    assert updated_run.template_config["protocol_spec"]["steps"] == spec["steps"]


def test_validate_and_update_meta(tmp_path):
    """Test validating a spec and updating meta fields."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    
    # Create protocol with a valid spec
    protocol_root = tmp_path / "protocol"
    protocol_root.mkdir()
    (protocol_root / "01-step.md").write_text("# Step\n\nContent.", encoding="utf-8")
    
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None)
    
    service = SpecService(db=db)
    spec = service.build_from_protocol_files(run.id, protocol_root)
    
    # Validate
    errors = service.validate_and_update_meta(run.id, protocol_root)
    
    # Should have no errors for a simple valid spec
    assert isinstance(errors, list)
    
    # Verify meta was updated
    updated_run = db.get_protocol_run(run.id)
    assert updated_run.template_config is not None
    assert "spec_meta" in updated_run.template_config
    assert updated_run.template_config["spec_meta"]["status"] in ["valid", "invalid"]


def test_ensure_step_runs_creates_missing(tmp_path):
    """Test that ensure_step_runs creates StepRun rows from spec."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None)
    
    # Create a spec manually
    spec = {
        "steps": [
            {"name": "step-1", "description": "First step"},
            {"name": "step-2", "description": "Second step"},
        ]
    }
    db.update_protocol_template(run.id, {"protocol_spec": spec}, None)
    
    service = SpecService(db=db)
    created = service.ensure_step_runs(run.id)
    
    # Should create 2 step runs
    assert created == 2
    
    steps = db.list_step_runs(run.id)
    assert len(steps) == 2
    assert steps[0].step_name == "step-1"
    assert steps[1].step_name == "step-2"
    
    # Running again should create 0 (already exist)
    created_again = service.ensure_step_runs(run.id)
    assert created_again == 0


def test_ensure_step_runs_skips_existing(tmp_path):
    """Test that ensure_step_runs skips already-existing steps."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None)
    
    # Create one step manually
    from tasksgodzilla.domain import StepStatus
    db.create_step_run(run.id, 1, "step-1", "work", StepStatus.PENDING, model=None)
    
    # Create a spec with 2 steps
    spec = {
        "steps": [
            {"name": "step-1", "description": "First step"},
            {"name": "step-2", "description": "Second step"},
        ]
    }
    db.update_protocol_template(run.id, {"protocol_spec": spec}, None)
    
    service = SpecService(db=db)
    created = service.ensure_step_runs(run.id)
    
    # Should only create step-2
    assert created == 1
    
    steps = db.list_step_runs(run.id)
    assert len(steps) == 2


def test_get_step_spec_returns_entry(tmp_path):
    """Test that get_step_spec retrieves a single step spec entry."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None)
    
    # Create a spec
    spec = {
        "steps": [
            {"name": "step-1", "description": "First step", "model": "gpt-5.1-high"},
            {"name": "step-2", "description": "Second step"},
        ]
    }
    db.update_protocol_template(run.id, {"protocol_spec": spec}, None)
    
    service = SpecService(db=db)
    
    # Get step-1
    step_spec = service.get_step_spec(run.id, "step-1")
    assert step_spec is not None
    assert step_spec["name"] == "step-1"
    assert step_spec["model"] == "gpt-5.1-high"
    
    # Get non-existent step
    missing = service.get_step_spec(run.id, "step-99")
    assert missing is None


def test_ensure_step_runs_returns_zero_when_no_spec(tmp_path):
    """Test that ensure_step_runs returns 0 when no spec exists."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None)
    
    service = SpecService(db=db)
    created = service.ensure_step_runs(run.id)
    
    assert created == 0
