import tempfile
from pathlib import Path

from tasksgodzilla.domain import ProtocolStatus, StepStatus
from tasksgodzilla.services.execution import ExecutionService
from tasksgodzilla.services.quality import QualityService
from tasksgodzilla.storage import Database
from tasksgodzilla.workers.codex_worker import handle_plan_protocol


def test_planning_is_blocked_by_open_blocking_clarification(tmp_path) -> None:
    db = Database(tmp_path / "db.sqlite")
    db.init_schema()
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    project = db.create_project(
        name="demo",
        git_url=str(tmp_path / "repo"),
        base_branch="main",
        ci_provider="github",
        default_models=None,
        project_classification="enterprise-compliance",
        # force strict behaviour for gating
        policy_pack_key="enterprise-compliance",
        policy_pack_version="1.0",
    )
    db.update_project_policy(project.id, policy_enforcement_mode="block")
    run = db.create_protocol_run(
        project_id=project.id,
        protocol_name="0001-demo",
        status=ProtocolStatus.PLANNING,
        base_branch="main",
        worktree_path=None,
        protocol_root=None,
        description="demo",
    )
    # Simulate an unanswered blocking onboarding clarification.
    db.upsert_clarification(
        scope=f"project:{project.id}",
        project_id=project.id,
        key="data_classification",
        question="What data classification applies?",
        applies_to="onboarding",
        blocking=True,
    )

    handle_plan_protocol(run.id, db)

    run_after = db.get_protocol_run(run.id)
    assert run_after.status == ProtocolStatus.BLOCKED
    events = db.list_events(run.id)
    assert any(e.event_type == "planning_blocked_clarifications" for e in events)


def test_execution_is_blocked_by_step_execution_clarification(tmp_path) -> None:
    db = Database(tmp_path / "db2.sqlite")
    db.init_schema()
    project = db.create_project(
        name="demo",
        git_url="git@example.com/demo.git",
        base_branch="main",
        ci_provider="github",
        default_models=None,
    )
    run = db.create_protocol_run(
        project_id=project.id,
        protocol_name="0002-demo",
        status=ProtocolStatus.RUNNING,
        base_branch="main",
        worktree_path=None,
        protocol_root=None,
        description="demo",
    )
    step = db.create_step_run(
        protocol_run_id=run.id,
        step_index=1,
        step_name="01-implement",
        step_type="exec",
        status=StepStatus.RUNNING,
        model=None,
    )
    db.upsert_clarification(
        scope=f"step:{step.id}",
        project_id=project.id,
        protocol_run_id=run.id,
        step_run_id=step.id,
        key="need_user_input",
        question="Please confirm the API contract for this change.",
        applies_to="execution",
        blocking=True,
    )

    ExecutionService(db).execute_step(step.id)

    step_after = db.get_step_run(step.id)
    assert step_after.status == StepStatus.BLOCKED
    events = db.list_events(run.id)
    assert any(e.event_type == "step_blocked_clarifications" for e in events)


def test_qa_is_blocked_by_step_qa_clarification(tmp_path) -> None:
    db = Database(tmp_path / "db3.sqlite")
    db.init_schema()
    project = db.create_project(
        name="demo",
        git_url="git@example.com/demo.git",
        base_branch="main",
        ci_provider="github",
        default_models=None,
    )
    run = db.create_protocol_run(
        project_id=project.id,
        protocol_name="0003-demo",
        status=ProtocolStatus.RUNNING,
        base_branch="main",
        worktree_path=None,
        protocol_root=None,
        description="demo",
    )
    step = db.create_step_run(
        protocol_run_id=run.id,
        step_index=1,
        step_name="01-implement",
        step_type="exec",
        status=StepStatus.NEEDS_QA,
        model=None,
    )
    db.upsert_clarification(
        scope=f"step:{step.id}",
        project_id=project.id,
        protocol_run_id=run.id,
        step_run_id=step.id,
        key="qa_scope",
        question="Confirm whether to require full regression run.",
        applies_to="qa",
        blocking=True,
    )

    QualityService(db=db).run_for_step_run(step.id)

    step_after = db.get_step_run(step.id)
    assert step_after.status == StepStatus.BLOCKED
    events = db.list_events(run.id)
    assert any(e.event_type == "qa_blocked_clarifications" for e in events)
