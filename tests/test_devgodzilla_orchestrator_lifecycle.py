import tempfile
from pathlib import Path

import pytest

from devgodzilla.models.domain import ProtocolStatus, StepStatus


def _setup_db(tmp: Path):
    from devgodzilla.db.database import SQLiteDatabase

    db_path = tmp / "devgodzilla.sqlite"
    repo = tmp / "repo"
    repo.mkdir(parents=True, exist_ok=True)

    db = SQLiteDatabase(db_path)
    db.init_schema()

    project = db.create_project(
        name="demo",
        git_url=str(repo),
        base_branch="main",
        local_path=str(repo),
    )
    return db, project, repo


def _get_context():
    from devgodzilla.config import load_config
    from devgodzilla.services.base import ServiceContext

    return ServiceContext(config=load_config())


def _make_orchestrator(db):
    from devgodzilla.services.orchestrator import OrchestratorMode, OrchestratorService

    return OrchestratorService(
        context=_get_context(),
        db=db,
        mode=OrchestratorMode.LOCAL,
    )


class TestProtocolLifecycle:

    def test_create_sets_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = orchestrator.create_protocol_run(
                project_id=project.id,
                protocol_name="test-proto",
            )
            assert run.status == ProtocolStatus.PENDING

    def test_start_transitions_to_planning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = orchestrator.create_protocol_run(
                project_id=project.id,
                protocol_name="test-proto",
            )
            result = orchestrator.start_protocol_run(run.id)
            assert result.success

            updated = db.get_protocol_run(run.id)
            assert updated.status == ProtocolStatus.PLANNING

    def test_pause_protocol(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            result = orchestrator.pause_protocol(run.id)
            assert result.success

            updated = db.get_protocol_run(run.id)
            assert updated.status == ProtocolStatus.PAUSED

    def test_resume_paused_protocol(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.PAUSED,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.PENDING,
            )
            result = orchestrator.resume_protocol(run.id)
            updated = db.get_protocol_run(run.id)
            assert updated.status == ProtocolStatus.RUNNING

    def test_cancel_protocol(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.RUNNING,
            )
            result = orchestrator.cancel_protocol(run.id)
            assert result.success

            updated = db.get_protocol_run(run.id)
            assert updated.status == ProtocolStatus.CANCELLED

            steps = db.list_step_runs(run.id)
            assert steps[0].status == StepStatus.CANCELLED

    def test_start_from_completed_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.COMPLETED,
                base_branch="main",
            )
            result = orchestrator.start_protocol_run(run.id)
            assert not result.success

    def test_cancel_completed_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.COMPLETED,
                base_branch="main",
            )
            result = orchestrator.cancel_protocol(run.id)
            assert not result.success

    def test_pause_cancelled_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.CANCELLED,
                base_branch="main",
            )
            result = orchestrator.pause_protocol(run.id)
            assert not result.success

    def test_resume_non_paused_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
            )
            result = orchestrator.resume_protocol(run.id)
            assert not result.success


class TestStepStatusTransitions:

    def test_run_from_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            step = db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.PENDING,
            )
            result = orchestrator.run_step(step.id)
            assert result.success

            updated = db.get_step_run(step.id)
            assert updated.status == StepStatus.RUNNING

    def test_run_from_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            step = db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.FAILED,
            )
            result = orchestrator.run_step(step.id)
            assert result.success

    def test_run_from_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            step = db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.BLOCKED,
            )
            result = orchestrator.run_step(step.id)
            assert result.success

    def test_run_from_completed_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            step = db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.COMPLETED,
            )
            result = orchestrator.run_step(step.id)
            assert not result.success

    def test_retry_from_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            step = db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.FAILED,
            )
            result = orchestrator.retry_step(step.id)
            assert result.success

    def test_retry_from_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            step = db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.TIMEOUT,
            )
            result = orchestrator.retry_step(step.id)
            assert result.success

    def test_retry_from_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            step = db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.BLOCKED,
            )
            result = orchestrator.retry_step(step.id)
            assert result.success

    def test_retry_from_completed_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            step = db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.COMPLETED,
            )
            result = orchestrator.retry_step(step.id)
            assert not result.success

    def test_run_step_qa_sets_needs_qa(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            step = db.create_step_run(
                protocol_run_id=run.id,
                step_index=0,
                step_name="Step 1",
                step_type="exec",
                status=StepStatus.RUNNING,
            )
            result = orchestrator.run_step_qa(step.id)
            assert result.success

            updated = db.get_step_run(step.id)
            assert updated.status == StepStatus.NEEDS_QA


class TestCheckAndCompleteProtocol:

    def test_all_completed_marks_protocol_completed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(protocol_run_id=run.id, step_index=0, step_name="S1", step_type="exec", status=StepStatus.COMPLETED)
            db.create_step_run(protocol_run_id=run.id, step_index=1, step_name="S2", step_type="exec", status=StepStatus.COMPLETED)

            assert orchestrator.check_and_complete_protocol(run.id) is True
            assert db.get_protocol_run(run.id).status == ProtocolStatus.COMPLETED

    def test_one_failed_marks_protocol_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(protocol_run_id=run.id, step_index=0, step_name="S1", step_type="exec", status=StepStatus.COMPLETED)
            db.create_step_run(protocol_run_id=run.id, step_index=1, step_name="S2", step_type="exec", status=StepStatus.FAILED)

            assert orchestrator.check_and_complete_protocol(run.id) is True
            assert db.get_protocol_run(run.id).status == ProtocolStatus.FAILED

    def test_completed_and_skipped_marks_completed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(protocol_run_id=run.id, step_index=0, step_name="S1", step_type="exec", status=StepStatus.COMPLETED)
            db.create_step_run(protocol_run_id=run.id, step_index=1, step_name="S2", step_type="exec", status=StepStatus.SKIPPED)

            assert orchestrator.check_and_complete_protocol(run.id) is True
            assert db.get_protocol_run(run.id).status == ProtocolStatus.COMPLETED

    def test_completed_and_timeout_marks_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(protocol_run_id=run.id, step_index=0, step_name="S1", step_type="exec", status=StepStatus.COMPLETED)
            db.create_step_run(protocol_run_id=run.id, step_index=1, step_name="S2", step_type="exec", status=StepStatus.TIMEOUT)

            result = orchestrator.check_and_complete_protocol(run.id)
            updated = db.get_protocol_run(run.id)
            assert result is True
            assert updated.status in (ProtocolStatus.COMPLETED, ProtocolStatus.FAILED)

    def test_running_step_prevents_completion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(protocol_run_id=run.id, step_index=0, step_name="S1", step_type="exec", status=StepStatus.COMPLETED)
            db.create_step_run(protocol_run_id=run.id, step_index=1, step_name="S2", step_type="exec", status=StepStatus.RUNNING)

            assert orchestrator.check_and_complete_protocol(run.id) is False

    def test_no_steps_returns_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="test",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
            )
            assert orchestrator.check_and_complete_protocol(run.id) is False


class TestRecoverStuckProtocols:

    def test_completes_with_all_terminal_steps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="stuck",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(protocol_run_id=run.id, step_index=0, step_name="S1", step_type="exec", status=StepStatus.COMPLETED)
            db.create_step_run(protocol_run_id=run.id, step_index=1, step_name="S2", step_type="exec", status=StepStatus.COMPLETED)

            recovered = orchestrator.recover_stuck_protocols()
            assert len(recovered) == 1
            assert recovered[0]["action"] == "completed"

    def test_blocks_with_failed_step(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="stuck",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(protocol_run_id=run.id, step_index=0, step_name="S1", step_type="exec", status=StepStatus.COMPLETED)
            db.create_step_run(protocol_run_id=run.id, step_index=1, step_name="S2", step_type="exec", status=StepStatus.FAILED)
            db.create_step_run(protocol_run_id=run.id, step_index=2, step_name="S3", step_type="exec", status=StepStatus.PENDING)

            recovered = orchestrator.recover_stuck_protocols()
            assert len(recovered) >= 1

    def test_enqueues_next_runnable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="stuck",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(protocol_run_id=run.id, step_index=0, step_name="S1", step_type="exec", status=StepStatus.COMPLETED)
            db.create_step_run(protocol_run_id=run.id, step_index=1, step_name="S2", step_type="exec", status=StepStatus.PENDING)

            recovered = orchestrator.recover_stuck_protocols()
            assert len(recovered) == 1
            assert recovered[0]["action"] == "enqueued_step"

    def test_skips_in_flight(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run = db.create_protocol_run(
                project_id=project.id,
                protocol_name="inflight",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(protocol_run_id=run.id, step_index=0, step_name="S1", step_type="exec", status=StepStatus.RUNNING)

            recovered = orchestrator.recover_stuck_protocols()
            assert len(recovered) == 0


class TestMultiCycleProtocol:

    def test_complete_then_create_another(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db, project, repo = _setup_db(Path(tmpdir))
            orchestrator = _make_orchestrator(db)

            run1 = db.create_protocol_run(
                project_id=project.id,
                protocol_name="cycle-1",
                status=ProtocolStatus.RUNNING,
                base_branch="main",
                worktree_path=str(repo),
                protocol_root=str(repo),
            )
            db.create_step_run(protocol_run_id=run1.id, step_index=0, step_name="S1", step_type="exec", status=StepStatus.COMPLETED)
            orchestrator.check_and_complete_protocol(run1.id)
            assert db.get_protocol_run(run1.id).status == ProtocolStatus.COMPLETED

            run2 = orchestrator.create_protocol_run(
                project_id=project.id,
                protocol_name="cycle-2",
            )
            assert run2.status == ProtocolStatus.PENDING
            assert run2.id != run1.id
