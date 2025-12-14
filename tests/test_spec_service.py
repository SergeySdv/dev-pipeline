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
            {"name": "step-1", "description": "First step", "model": "zai-coding-plan/glm-4.6"},
            {"name": "step-2", "description": "Second step"},
        ]
    }
    db.update_protocol_template(run.id, {"protocol_spec": spec}, None)
    
    service = SpecService(db=db)
    
    # Get step-1
    step_spec = service.get_step_spec(run.id, "step-1")
    assert step_spec is not None
    assert step_spec["name"] == "step-1"
    assert step_spec["model"] == "zai-coding-plan/glm-4.6"
    
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


def test_resolve_protocol_paths_with_worktree(tmp_path):
    """Test resolve_protocol_paths when worktree_path is set."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    # Create project and protocol run with worktree_path
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(
        project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None
    )
    db.update_protocol_paths(run.id, str(worktree), None)
    
    service = SpecService(db=db)
    run = db.get_protocol_run(run.id)
    
    workspace_root, protocol_root = service.resolve_protocol_paths(run, project)
    
    assert workspace_root == worktree.resolve()
    assert protocol_root == (worktree / ".protocols" / "test-protocol").resolve()


def test_resolve_protocol_paths_with_local_path(tmp_path):
    """Test resolve_protocol_paths when project has local_path."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    # Create local path
    local_path = tmp_path / "local"
    local_path.mkdir()
    
    project = db.create_project(
        "test-project", "https://github.com/test/repo", "main", "github", {}, local_path=str(local_path)
    )
    run = db.create_protocol_run(
        project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None
    )
    
    service = SpecService(db=db)
    run = db.get_protocol_run(run.id)
    
    workspace_root, protocol_root = service.resolve_protocol_paths(run, project)
    
    assert workspace_root == local_path.resolve()
    assert protocol_root == (local_path / ".protocols" / "test-protocol").resolve()


def test_resolve_protocol_paths_with_protocol_root(tmp_path):
    """Test resolve_protocol_paths when protocol_root is explicitly set."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    # Create paths
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    protocol_root = tmp_path / "custom-protocol"
    protocol_root.mkdir()
    
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(
        project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None
    )
    db.update_protocol_paths(run.id, str(workspace), str(protocol_root))
    
    service = SpecService(db=db)
    run = db.get_protocol_run(run.id)
    
    workspace_root, resolved_protocol_root = service.resolve_protocol_paths(run, project)
    
    assert workspace_root == workspace.resolve()
    assert resolved_protocol_root == protocol_root.resolve()


def test_resolve_step_paths(tmp_path):
    """Test resolve_step_paths resolves prompt and output paths."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    # Create protocol structure
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    protocol_root = workspace / ".protocols" / "test-protocol"
    protocol_root.mkdir(parents=True)
    
    # Create step file
    step_file = protocol_root / "01-step.md"
    step_file.write_text("# Step content", encoding="utf-8")
    
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(
        project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None
    )
    
    # Create spec with step
    spec = {
        "steps": [
            {
                "name": "01-step.md",
                "prompt_ref": "01-step.md",
                "outputs": {"protocol": "01-step.md"},
            }
        ]
    }
    db.update_protocol_template(run.id, {"protocol_spec": spec}, None)
    
    # Create step run
    from tasksgodzilla.domain import StepStatus
    step_run = db.create_step_run(run.id, 1, "01-step.md", "work", StepStatus.PENDING, model=None)
    
    service = SpecService(db=db)
    paths = service.resolve_step_paths(step_run, protocol_root, workspace)
    
    assert "prompt" in paths
    assert paths["prompt"] == step_file.resolve()
    assert "protocol" in paths
    assert paths["protocol"] == step_file.resolve()


def test_resolve_output_paths(tmp_path):
    """Test resolve_output_paths handles various output configurations."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    # Create protocol structure
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    protocol_root = workspace / ".protocols" / "test-protocol"
    protocol_root.mkdir(parents=True)
    
    service = SpecService(db=db)
    
    # Test simple string outputs
    step_spec = {
        "outputs": {
            "protocol": "step.md",
            "log": "log.txt",
        }
    }
    
    outputs = service.resolve_output_paths(step_spec, protocol_root, workspace)
    
    assert "protocol" in outputs
    assert "log" in outputs
    assert outputs["protocol"] == (protocol_root / "step.md").resolve()
    assert outputs["log"] == (protocol_root / "log.txt").resolve()


def test_resolve_output_paths_empty(tmp_path):
    """Test resolve_output_paths with no outputs."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    protocol_root = workspace / ".protocols" / "test-protocol"
    protocol_root.mkdir(parents=True)
    
    service = SpecService(db=db)
    
    step_spec = {"outputs": {}}
    outputs = service.resolve_output_paths(step_spec, protocol_root, workspace)
    
    assert outputs == {}


def test_build_from_codemachine_config(tmp_path):
    """Test building spec from CodeMachine config."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    project = db.create_project("test-project", "https://github.com/test/repo", "main", "github", {})
    run = db.create_protocol_run(
        project.id, "test-protocol", ProtocolStatus.PENDING, "main", None, None, None
    )
    
    # Create a minimal mock config with empty agents list
    class MockConfig:
        def __init__(self):
            self.main_agents = []
            self.sub_agents = []
            self.modules = []
            self.template = {}
            self.placeholders = {}
    
    config = MockConfig()
    
    service = SpecService(db=db)
    spec = service.build_from_codemachine_config(run.id, config)
    
    # Verify spec was created (even if empty)
    assert "steps" in spec
    assert len(spec["steps"]) == 0
    
    # Verify it was persisted
    updated_run = db.get_protocol_run(run.id)
    assert updated_run.template_config is not None
    assert "protocol_spec" in updated_run.template_config


def test_sync_step_runs_from_protocol(tmp_path):
    """Test syncing step runs from protocol directory."""
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
    created = service.sync_step_runs_from_protocol(protocol_root, run.id)
    
    # Verify step runs were created
    assert created == 2
    step_runs = db.list_step_runs(run.id)
    assert len(step_runs) == 2
    assert step_runs[0].step_name == "01-first-step.md"
    assert step_runs[1].step_name == "02-second-step.md"


def test_append_protocol_log(tmp_path):
    """Test appending to protocol log."""
    protocol_root = tmp_path / "protocol"
    protocol_root.mkdir()
    log_path = protocol_root / "log.md"
    log_path.write_text("# Log\n\n", encoding="utf-8")
    
    db = Database(tmp_path / "test.db")
    db.init_schema()
    service = SpecService(db=db)
    
    # Append a message
    service.append_protocol_log(protocol_root, "Test message")
    
    # Verify it was appended
    log_content = log_path.read_text(encoding="utf-8")
    assert "Test message" in log_content
    assert "# Log" in log_content  # Original content preserved


def test_append_protocol_log_missing_file(tmp_path):
    """Test appending to protocol log when log.md doesn't exist."""
    protocol_root = tmp_path / "protocol"
    protocol_root.mkdir()
    
    db = Database(tmp_path / "test.db")
    db.init_schema()
    service = SpecService(db=db)
    
    # Should not raise an error
    service.append_protocol_log(protocol_root, "Test message")
    
    # Log file should not be created
    log_path = protocol_root / "log.md"
    assert not log_path.exists()


def test_infer_step_type(tmp_path):
    """Test inferring step type from filename."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    service = SpecService(db=db)
    
    # Test setup step
    assert service.infer_step_type("00-setup.md") == "setup"
    assert service.infer_step_type("setup-environment.md") == "setup"
    
    # Test QA step
    assert service.infer_step_type("qa-validation.md") == "qa"
    assert service.infer_step_type("01-qa.md") == "qa"
    
    # Test work step
    assert service.infer_step_type("01-implement-feature.md") == "work"
    assert service.infer_step_type("02-test.md") == "work"
