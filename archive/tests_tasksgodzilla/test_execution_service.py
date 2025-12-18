from pathlib import Path
from unittest.mock import patch, MagicMock

from tasksgodzilla.domain import ProtocolStatus, StepStatus
from tasksgodzilla.services import ExecutionService
from tasksgodzilla.storage import Database


def test_execute_step_service_exists(tmp_path):
    """Test that ExecutionService can be instantiated and has execute_step method."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    service = ExecutionService(db=db)
    
    # Verify service has the execute_step method
    assert hasattr(service, "execute_step")
    assert callable(service.execute_step)


def test_execute_step_requires_database(tmp_path):
    """Test that ExecutionService requires a database."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    service = ExecutionService(db=db)
    
    # Verify service has database
    assert service.db is not None
    assert service.db == db


def test_execute_step_blocks_when_policy_enforcement_is_block(tmp_path):
    db = Database(tmp_path / "test.db")
    db.init_schema()

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)

    project = db.create_project(
        name="demo",
        git_url=str(repo_root),
        base_branch="main",
        ci_provider=None,
        default_models=None,
        secrets=None,
        local_path=str(repo_root),
    )
    db.update_project_policy(
        project.id,
        policy_pack_key="beginner-guided",
        policy_pack_version="1.0",
        policy_enforcement_mode="block",
    )

    run = db.create_protocol_run(
        project_id=project.id,
        protocol_name="0001-demo",
        status=ProtocolStatus.RUNNING,
        base_branch="main",
        worktree_path=str(repo_root),
        protocol_root=str(repo_root / ".protocols" / "0001-demo"),
        description="demo",
    )
    # Ensure protocol root exists but required check scripts are missing -> blocking findings.
    (repo_root / ".protocols" / "0001-demo").mkdir(parents=True, exist_ok=True)

    step = db.create_step_run(
        protocol_run_id=run.id,
        step_index=1,
        step_name="01-implement",
        step_type="work",
        status=StepStatus.RUNNING,
        model=None,
    )

    service = ExecutionService(db=db)
    service.execute_step(step.id, job_id="job-1")

    step_after = db.get_step_run(step.id)
    run_after = db.get_protocol_run(run.id)
    assert step_after.status == StepStatus.BLOCKED
    assert run_after.status == ProtocolStatus.BLOCKED
