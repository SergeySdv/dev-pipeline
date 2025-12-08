from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from tasksgodzilla.logging import get_logger
from tasksgodzilla.storage import BaseDatabase
from tasksgodzilla.domain import ProtocolRun, ProtocolStatus, StepRun, StepStatus
from tasksgodzilla.jobs import BaseQueue, Job
from tasksgodzilla.workers.codex_worker import (
    handle_plan_protocol,
    handle_execute_step,
    handle_open_pr,
    sync_step_runs_from_protocol,
)

log = get_logger(__name__)


@dataclass
class OrchestratorService:
    """High-level orchestration facade over existing worker flows.

    For now this is a thin wrapper around the Codex worker helpers. Over time it
    can absorb lifecycle and policy decisions while workers become simple job
    adapters.
    """

    db: BaseDatabase

    def create_protocol_run(
        self,
        project_id: int,
        protocol_name: str,
        status: str,
        base_branch: str,
        *,
        worktree_path: Optional[str] = None,
        protocol_root: Optional[str] = None,
        description: Optional[str] = None,
        template_config: Optional[dict] = None,
        template_source: Optional[dict] = None,
    ) -> ProtocolRun:
        """Create a new ProtocolRun row.

        This is a thin wrapper over `BaseDatabase.create_protocol_run` so that
        API/CLI layers can depend on the orchestrator service instead of the DB
        interface directly.
        """
        run = self.db.create_protocol_run(
            project_id=project_id,
            protocol_name=protocol_name,
            status=status,
            base_branch=base_branch,
            worktree_path=worktree_path,
            protocol_root=protocol_root,
            description=description,
            template_config=template_config,
            template_source=template_source,
        )
        log.info(
            "orchestrator_protocol_created",
            extra={"protocol_run_id": run.id, "project_id": project_id, "protocol_name": protocol_name},
        )
        return run

    def start_protocol_run(self, protocol_run_id: int, queue: BaseQueue) -> Job:
        """Transition a protocol to PLANNING and enqueue the planning job.

        Raises ValueError when the protocol is not in a state that can be started.
        """
        run = self.db.get_protocol_run(protocol_run_id)
        if run.status not in (ProtocolStatus.PENDING, ProtocolStatus.PLANNED, ProtocolStatus.PAUSED):
            raise ValueError("Protocol already running or terminal")
        self.db.update_protocol_status(protocol_run_id, ProtocolStatus.PLANNING, expected_status=run.status)
        job = queue.enqueue("plan_protocol_job", {"protocol_run_id": protocol_run_id})
        log.info(
            "orchestrator_plan_enqueued",
            extra={"protocol_run_id": protocol_run_id, "job_id": job.job_id},
        )
        return job

    def enqueue_next_step(self, protocol_run_id: int, queue: BaseQueue) -> Tuple[StepRun, Job]:
        """Select the next runnable step, mark it running, and enqueue execution.

        Returns the updated StepRun and Job. Raises LookupError when no suitable
        step exists, and ValueError when the step state changes concurrently.
        """
        steps = self.db.list_step_runs(protocol_run_id)
        target = next(
            (s for s in steps if s.status in (StepStatus.PENDING, StepStatus.BLOCKED, StepStatus.FAILED)),
            None,
        )
        if not target:
            raise LookupError("No pending or failed steps to run")
        step = self.db.update_step_status(target.id, StepStatus.RUNNING, expected_status=target.status)
        self.db.update_protocol_status(protocol_run_id, ProtocolStatus.RUNNING)
        job = queue.enqueue("execute_step_job", {"step_run_id": step.id})
        log.info(
            "orchestrator_step_enqueued",
            extra={"protocol_run_id": protocol_run_id, "step_run_id": step.id, "job_id": job.job_id},
        )
        return step, job

    def retry_latest_step(self, protocol_run_id: int, queue: BaseQueue) -> Tuple[StepRun, Job]:
        """Retry the most recent failed or blocked step and enqueue execution.

        Returns the updated StepRun and Job. Raises LookupError when no suitable
        step exists, and ValueError when the step state changes concurrently.
        """
        steps = self.db.list_step_runs(protocol_run_id)
        target = next(
            (s for s in reversed(steps) if s.status in (StepStatus.FAILED, StepStatus.BLOCKED)),
            None,
        )
        if not target:
            raise LookupError("No failed or blocked steps to retry")
        step = self.db.update_step_status(
            target.id,
            StepStatus.RUNNING,
            retries=target.retries + 1,
            expected_status=target.status,
        )
        self.db.update_protocol_status(protocol_run_id, ProtocolStatus.RUNNING)
        job = queue.enqueue("execute_step_job", {"step_run_id": step.id})
        log.info(
            "orchestrator_step_retry_enqueued",
            extra={"protocol_run_id": protocol_run_id, "step_run_id": step.id, "job_id": job.job_id, "retries": step.retries},
        )
        return step, job

    def plan_protocol(self, protocol_run_id: int, job_id: Optional[str] = None) -> None:
        """Plan a protocol run by delegating to the Codex worker."""
        log.info("orchestrator_plan_protocol", extra={"protocol_run_id": protocol_run_id, "job_id": job_id})
        handle_plan_protocol(protocol_run_id, self.db, job_id=job_id)

    def execute_step(self, step_run_id: int, job_id: Optional[str] = None) -> None:
        """Execute a single step via the existing worker implementation."""
        log.info("orchestrator_execute_step", extra={"step_run_id": step_run_id, "job_id": job_id})
        handle_execute_step(step_run_id, self.db, job_id=job_id)

    def run_step(self, step_run_id: int, queue: BaseQueue) -> Job:
        """Transition a step to RUNNING and enqueue execution."""
        step = self.db.get_step_run(step_run_id)
        if step.status not in (StepStatus.PENDING, StepStatus.BLOCKED, StepStatus.FAILED):
            raise ValueError("Step already running or completed")
        step = self.db.update_step_status(step.id, StepStatus.RUNNING, expected_status=step.status)
        self.db.update_protocol_status(step.protocol_run_id, ProtocolStatus.RUNNING)
        job = queue.enqueue("execute_step_job", {"step_run_id": step.id})
        log.info(
            "orchestrator_step_run_enqueued",
            extra={"protocol_run_id": step.protocol_run_id, "step_run_id": step.id, "job_id": job.job_id},
        )
        return job

    def run_step_qa(self, step_run_id: int, queue: BaseQueue) -> Job:
        """Transition a step to NEEDS_QA and enqueue a QA job."""
        step = self.db.get_step_run(step_run_id)
        if step.status in (StepStatus.COMPLETED, StepStatus.CANCELLED):
            raise ValueError("Step already completed or cancelled")
        step = self.db.update_step_status(step.id, StepStatus.NEEDS_QA, expected_status=step.status)
        job = queue.enqueue("run_quality_job", {"step_run_id": step.id})
        log.info(
            "orchestrator_step_qa_enqueued",
            extra={"protocol_run_id": step.protocol_run_id, "step_run_id": step.id, "job_id": job.job_id},
        )
        return job

    def pause_protocol(self, protocol_run_id: int) -> ProtocolRun:
        """Pause a protocol run when it is not terminal."""
        run = self.db.get_protocol_run(protocol_run_id)
        if run.status in (ProtocolStatus.CANCELLED, ProtocolStatus.COMPLETED, ProtocolStatus.FAILED):
            raise ValueError("Protocol already terminal")
        return self.db.update_protocol_status(protocol_run_id, ProtocolStatus.PAUSED, expected_status=run.status)

    def resume_protocol(self, protocol_run_id: int) -> ProtocolRun:
        """Resume a paused protocol run."""
        run = self.db.get_protocol_run(protocol_run_id)
        if run.status != ProtocolStatus.PAUSED:
            raise ValueError("Protocol is not paused")
        return self.db.update_protocol_status(protocol_run_id, ProtocolStatus.RUNNING, expected_status=run.status)

    def cancel_protocol(self, protocol_run_id: int) -> ProtocolRun:
        """Cancel a protocol and mark in-flight steps as cancelled when appropriate."""
        run = self.db.get_protocol_run(protocol_run_id)
        if run.status == ProtocolStatus.CANCELLED:
            return run
        updated = self.db.update_protocol_status(protocol_run_id, ProtocolStatus.CANCELLED, expected_status=run.status)
        steps = self.db.list_step_runs(protocol_run_id)
        for step in steps:
            if step.status in (StepStatus.PENDING, StepStatus.RUNNING, StepStatus.NEEDS_QA):
                try:
                    self.db.update_step_status(
                        step.id,
                        StepStatus.CANCELLED,
                        summary="Cancelled with protocol",
                        expected_status=step.status,
                    )
                except Exception:
                    continue
        return updated

    def open_protocol_pr(self, protocol_run_id: int, job_id: Optional[str] = None) -> None:
        """Open PR/MR for a protocol using the existing worker implementation."""
        handle_open_pr(protocol_run_id, self.db, job_id=job_id)

    def enqueue_open_protocol_pr(self, protocol_run_id: int, queue: BaseQueue) -> Job:
        """Enqueue an open_pr job for the protocol."""
        job = queue.enqueue("open_pr_job", {"protocol_run_id": protocol_run_id})
        log.info(
            "orchestrator_open_pr_enqueued",
            extra={"protocol_run_id": protocol_run_id, "job_id": job.job_id},
        )
        return job

    def sync_steps_from_protocol(self, protocol_run_id: int, protocol_root: Path) -> int:
        """Ensure StepRun rows exist for each protocol step file."""
        return sync_step_runs_from_protocol(protocol_root, protocol_run_id, self.db)
