from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Tuple

from devgodzilla.api import schemas
from devgodzilla.logging import get_logger
from devgodzilla.models.domain import StepRun, StepStatus
from devgodzilla.services.base import Service, ServiceContext
from devgodzilla.services.agent_config import AgentConfigService
from devgodzilla.services.execution import ExecutionService
from devgodzilla.services.git import GitService
from devgodzilla.services.policy import PolicyService
from devgodzilla.services.quality import QAResult, QualityService
from devgodzilla.services.spec_to_protocol import SpecToProtocolService
from devgodzilla.services.specification import SpecificationService
from devgodzilla.services.workspace_paths import (
    WorkspacePathError,
    resolve_protocol_root,
    resolve_workspace_root,
)

logger = get_logger(__name__)


class TaskCycleError(RuntimeError):
    """Raised when a task-cycle action cannot be completed safely."""


class TaskCycleService(Service):
    RUNTIME_KEY = "task_cycle"
    LIFECYCLE_ACTIVE = "active"
    LIFECYCLE_ARCHIVED = "archived"
    LIFECYCLE_CANCELED = "canceled"
    STATUS_QUEUED = "queued"
    STATUS_CONTEXT_READY = "context_ready"
    STATUS_PLAN_READY = "plan_ready"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_AWAITING_REVIEW = "awaiting_review"
    STATUS_NEEDS_REWORK = "needs_rework"
    STATUS_NEEDS_REFACTOR = "needs_refactor"
    STATUS_READY_FOR_PR = "ready_for_pr"
    STATUS_PR_READY = "pr_ready"
    STATUS_BLOCKED = "blocked"
    MAX_PLAN_TOUCHED_FILES = 8
    MAX_CHANGED_FILES = 8
    MAX_PUBLIC_API_SURFACE_FILES = 2
    MAX_PYTHON_MODULE_LINES = 1500
    MAX_PYTHON_FUNCTION_LINES = 80
    MAX_PYTHON_FUNCTION_ARGS = 6
    MAX_PYTHON_NESTING_DEPTH = 4
    STAGES: Tuple[Tuple[str, str], ...] = (
        ("build_context", "Build Context"),
        ("plan", "Plan"),
        ("implement", "Implement"),
        ("review", "Review"),
        ("qa", "QA"),
        ("refactor", "Refactor"),
        ("pr_ready", "PR Ready"),
    )

    def __init__(self, context: ServiceContext, db) -> None:
        super().__init__(context)
        self.db = db

    def _append_project_event(
        self,
        project_id: int,
        *,
        event_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        protocol_run_id: Optional[int] = None,
        step_run_id: Optional[int] = None,
    ) -> None:
        try:
            self.db.append_event(
                protocol_run_id=protocol_run_id,
                project_id=project_id,
                step_run_id=step_run_id,
                event_type=event_type,
                message=message,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning(
                "task_cycle_event_append_failed",
                extra={"project_id": project_id, "event_type": event_type, "error": str(exc)},
            )

    def list_work_items(
        self,
        project_id: int,
        *,
        protocol_run_id: Optional[int] = None,
        lifecycle: str = "active",
    ) -> List[schemas.WorkItemOut]:
        lifecycle_filter = (lifecycle or "active").strip().lower()
        allowed_filters = {"active", "all", self.LIFECYCLE_ARCHIVED, self.LIFECYCLE_CANCELED}
        if lifecycle_filter not in allowed_filters:
            raise TaskCycleError(f"Unknown lifecycle filter: {lifecycle}")
        if protocol_run_id is not None:
            run = self.db.get_protocol_run(protocol_run_id)
            if run.project_id != project_id:
                raise TaskCycleError("Protocol run does not belong to the requested project")
            runs = [run]
        else:
            runs = [run for run in self.db.list_protocol_runs(project_id) if self._is_task_cycle_run(run)]

        items: List[schemas.WorkItemOut] = []
        for run in runs:
            for step in self.db.list_step_runs(run.id):
                item = self.get_work_item(step.id)
                if lifecycle_filter == "active" and item.lifecycle_state != self.LIFECYCLE_ACTIVE:
                    continue
                if lifecycle_filter in {self.LIFECYCLE_ARCHIVED, self.LIFECYCLE_CANCELED}:
                    if item.lifecycle_state != lifecycle_filter:
                        continue
                items.append(item)
        return sorted(items, key=lambda item: (item.protocol_run_id, item.id))

    def get_work_item(self, step_run_id: int) -> schemas.WorkItemOut:
        step, run, project = self._load_work_item(step_run_id)
        return self._build_work_item_response(step, run, project)

    def get_work_item_runtime(self, step_run_id: int) -> schemas.WorkItemRuntimeOut:
        step, run, project = self._load_work_item(step_run_id)
        work_item = self._build_work_item_response(step, run, project)
        runtime = self._build_runtime_projection(step, run, project, work_item)
        return runtime

    def _build_work_item_response(self, step: StepRun, run, project) -> schemas.WorkItemOut:
        state = self._task_cycle_state(step, project)
        blocking_clarifications = self._blocking_clarifications(project.id, run.id, step.id)
        stage_overview = self._build_stage_overview(
            step,
            run,
            project,
            state=state,
            blocking_clarifications=blocking_clarifications,
        )
        return schemas.WorkItemOut(
            id=step.id,
            project_id=project.id,
            protocol_run_id=run.id,
            title=step.step_name,
            status=str(state["status"]),
            lifecycle_state=str(state["lifecycle_state"]),
            lifecycle_reason=self._string_or_none(state.get("lifecycle_reason")),
            context_status=str(state["context_status"]),
            plan_status=str(state["plan_status"]),
            review_status=str(state["review_status"]),
            qa_status=str(state["qa_status"]),
            refactor_status=str(state["refactor_status"]),
            owner_agent=self._string_or_none(state.get("owner_agent")) or step.assigned_agent,
            helper_agents=self._string_list(state.get("helper_agents")),
            task_dir=self._string_or_none(state.get("task_dir")),
            artifact_refs=schemas.WorkItemArtifactRefsOut(**self._artifact_refs(project, step)),
            depends_on=list(step.depends_on or []),
            pr_ready=bool(state.get("pr_ready", False)),
            blocking_clarifications=blocking_clarifications,
            blocking_policy_findings=int(state.get("blocking_policy_findings", 0) or 0),
            iteration_count=int(state.get("iteration_count", 0) or 0),
            max_iterations=int(state.get("max_iterations", self.config.task_cycle_max_iterations) or self.config.task_cycle_max_iterations),
            summary=step.summary,
            active_stage=stage_overview["active_stage"],
            active_stage_label=stage_overview["active_stage_label"],
            active_stage_status=stage_overview["active_stage_status"],
            latest_completed_stage=stage_overview["latest_completed_stage"],
            latest_artifact_summary=stage_overview["latest_artifact_summary"],
            blocking_reason=stage_overview["blocking_reason"],
            progress_summary=stage_overview["progress_summary"],
        )

    def start_brownfield_run(
        self,
        project_id: int,
        request: schemas.BrownfieldRunRequest,
    ) -> schemas.BrownfieldRunOut:
        project = self.db.get_project(project_id)
        if not project.local_path:
            raise TaskCycleError("Project has no local path")
        resolved_owner_agent = self._resolve_owner_agent(project.id, request.owner_agent)
        protocol_name = self._brownfield_protocol_name(request)
        existing_run = self._find_reusable_brownfield_run(project_id, protocol_name, request.output_mode)
        if existing_run is not None:
            existing_items = self.list_work_items(project_id, protocol_run_id=existing_run.id)
            next_work_item_id = next((item.id for item in existing_items if not item.pr_ready), None)
            return schemas.BrownfieldRunOut(
                success=True,
                project_id=project_id,
                output_mode=request.output_mode,
                protocol=schemas.ProtocolOut.model_validate(existing_run),
                work_items=existing_items,
                next_work_item_id=next_work_item_id,
                warnings=["Reusing existing brownfield run"],
            )
        protocol_run = self.db.create_protocol_run(
            project_id=project_id,
            protocol_name=protocol_name,
            status="planning",
            base_branch=request.branch or project.base_branch or "main",
            worktree_path=project.local_path,
            description=request.feature_request,
        )
        helper_agents = request.helper_agents if (request.allow_helper_agents or request.helper_agents) else []
        protocol_metadata = {
            "task_cycle": request.output_mode == "task_cycle",
            "brownfield_output_mode": request.output_mode,
            "brownfield_bootstrap_status": "queued",
            "brownfield_bootstrap_stage": "queued",
            "feature_name": request.feature_name,
            "feature_request_preview": (request.feature_request or "")[:200],
        }
        protocol_run = self.db.update_protocol_windmill(protocol_run.id, speckit_metadata=protocol_metadata)

        step = self.db.create_step_run(
            protocol_run_id=protocol_run.id,
            step_index=1,
            step_name=self._brownfield_step_name(protocol_name),
            step_type="execute",
            status="pending",
            assigned_agent=resolved_owner_agent,
        )
        step = self.db.update_step_run(step.id, summary=request.feature_request[:1000])
        self._seed_task_cycle_metadata(
            protocol_run.id,
            owner_agent=resolved_owner_agent,
            helper_agents=helper_agents,
        )
        self._set_brownfield_bootstrap_state(
            protocol_run_id=protocol_run.id,
            step_run_id=step.id,
            project_id=project_id,
            stage="queued",
            status="queued",
            message="Brownfield run queued",
        )
        work_item = self.get_work_item(step.id)
        return schemas.BrownfieldRunOut(
            success=True,
            project_id=project_id,
            output_mode=request.output_mode,
            protocol=schemas.ProtocolOut.model_validate(protocol_run),
            work_items=[work_item],
            next_work_item_id=work_item.id,
            warnings=[],
        )

    def run_brownfield_bootstrap(
        self,
        project_id: int,
        request: schemas.BrownfieldRunRequest,
        *,
        protocol_run_id: int,
        step_run_id: int,
    ) -> None:
        project = self.db.get_project(project_id)
        protocol_run = self.db.get_protocol_run(protocol_run_id)
        resolved_owner_agent = self._resolve_owner_agent(project.id, request.owner_agent)
        helper_agents = request.helper_agents if (request.allow_helper_agents or request.helper_agents) else []
        spec_service = SpecificationService(self.context, self.db)
        protocol_service = SpecToProtocolService(self.context, self.db)
        event_metadata = {
            "feature_name": request.feature_name,
            "feature_request_preview": (request.feature_request or "")[:200],
            "output_mode": request.output_mode,
            "branch": request.branch,
            "protocol_run_id": protocol_run_id,
            "step_run_id": step_run_id,
        }
        self._append_project_event(
            project_id,
            event_type="brownfield_run_started",
            message=f"Starting brownfield run: {(request.feature_name or request.feature_request[:60]).strip()}",
            metadata=event_metadata,
            protocol_run_id=protocol_run_id,
            step_run_id=step_run_id,
        )

        try:
            self._append_project_event(
                project_id,
                event_type="brownfield_specify_started",
                message="Starting brownfield specify stage",
                metadata=event_metadata,
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
            )
            self._set_brownfield_bootstrap_state(
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
                project_id=project_id,
                stage="specify",
                status="running",
                message="Bootstrapping brownfield run: specify",
            )
            specify = spec_service.run_specify(
                project.local_path,
                request.feature_request,
                feature_name=request.feature_name,
                base_branch=request.branch,
                project_id=project_id,
            )
            if not specify.success or not specify.spec_path:
                error = specify.error or "Spec generation failed"
                self._mark_brownfield_bootstrap_failed(
                    project_id,
                    protocol_run_id=protocol_run_id,
                    step_run_id=step_run_id,
                    stage="specify",
                    error=error,
                    metadata={**event_metadata, "spec_run_id": specify.spec_run_id},
                )
                return
            self._append_project_event(
                project_id,
                event_type="brownfield_specify_completed",
                message="Brownfield specify stage completed",
                metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "spec_path": specify.spec_path},
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
            )

            self._append_project_event(
                project_id,
                event_type="brownfield_plan_started",
                message="Starting brownfield plan stage",
                metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "spec_path": specify.spec_path},
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
            )
            self._set_brownfield_bootstrap_state(
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
                project_id=project_id,
                stage="plan",
                status="running",
                message="Bootstrapping brownfield run: plan",
                spec_run_id=specify.spec_run_id,
            )
            plan = spec_service.run_plan(
                project.local_path,
                specify.spec_path,
                spec_run_id=specify.spec_run_id,
                project_id=project_id,
            )
            if not plan.success or not plan.plan_path:
                error = plan.error or "Plan generation failed"
                self._mark_brownfield_bootstrap_failed(
                    project_id,
                    protocol_run_id=protocol_run_id,
                    step_run_id=step_run_id,
                    stage="plan",
                    error=error,
                    metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "spec_path": specify.spec_path},
                )
                return
            self._append_project_event(
                project_id,
                event_type="brownfield_plan_completed",
                message="Brownfield plan stage completed",
                metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "plan_path": plan.plan_path},
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
            )

            self._append_project_event(
                project_id,
                event_type="brownfield_tasks_started",
                message="Starting brownfield tasks stage",
                metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "plan_path": plan.plan_path},
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
            )
            self._set_brownfield_bootstrap_state(
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
                project_id=project_id,
                stage="tasks",
                status="running",
                message="Bootstrapping brownfield run: tasks",
                spec_run_id=specify.spec_run_id,
            )
            tasks = spec_service.run_tasks(
                project.local_path,
                plan.plan_path,
                spec_run_id=specify.spec_run_id,
                project_id=project_id,
            )
            if not tasks.success or not tasks.tasks_path:
                error = tasks.error or "Task generation failed"
                self._mark_brownfield_bootstrap_failed(
                    project_id,
                    protocol_run_id=protocol_run_id,
                    step_run_id=step_run_id,
                    stage="tasks",
                    error=error,
                    metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "plan_path": plan.plan_path},
                )
                return
            self._append_project_event(
                project_id,
                event_type="brownfield_tasks_completed",
                message="Brownfield tasks stage completed",
                metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "tasks_path": tasks.tasks_path},
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
            )

            if request.output_mode in {"task_cycle", "protocol"}:
                self._append_project_event(
                    project_id,
                    event_type="brownfield_protocol_seed_started",
                    message="Starting brownfield protocol seed stage",
                    metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "tasks_path": tasks.tasks_path},
                    protocol_run_id=protocol_run_id,
                    step_run_id=step_run_id,
                )
                self._set_brownfield_bootstrap_state(
                    protocol_run_id=protocol_run_id,
                    step_run_id=step_run_id,
                    project_id=project_id,
                    stage="protocol_seed",
                    status="running",
                    message="Bootstrapping brownfield run: protocol seed",
                    spec_run_id=specify.spec_run_id,
                )
                protocol = protocol_service.create_protocol_from_spec(
                    project_id=project_id,
                    spec_path=specify.spec_path,
                    tasks_path=tasks.tasks_path,
                    protocol_name=protocol_run.protocol_name,
                    spec_run_id=specify.spec_run_id,
                    protocol_run_id=protocol_run_id,
                    overwrite=True,
                    collapse_to_single_step=request.output_mode == "task_cycle",
                )
                if not protocol.success or not protocol.protocol_run_id:
                    error = protocol.error or "Protocol creation failed"
                    self._mark_brownfield_bootstrap_failed(
                        project_id,
                        protocol_run_id=protocol_run_id,
                        step_run_id=step_run_id,
                        stage="protocol_seed",
                        error=error,
                        metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "tasks_path": tasks.tasks_path},
                    )
                    return
                protocol_run = self.db.get_protocol_run(protocol_run_id)
                protocol_metadata = dict(protocol_run.speckit_metadata or {})
                protocol_metadata.update(
                    {
                        "task_cycle": request.output_mode == "task_cycle",
                        "brownfield_output_mode": request.output_mode,
                        "brownfield_bootstrap_status": "completed",
                        "brownfield_bootstrap_stage": "completed",
                        "spec_run_id": specify.spec_run_id,
                        "spec_path": specify.spec_path,
                        "plan_path": plan.plan_path,
                        "tasks_path": tasks.tasks_path,
                    }
                )
                self.db.update_protocol_windmill(protocol_run_id, speckit_metadata=protocol_metadata)
                self._seed_task_cycle_metadata(
                    protocol_run_id,
                    owner_agent=resolved_owner_agent,
                    helper_agents=helper_agents,
                )
                self._append_project_event(
                    project_id,
                    event_type="brownfield_protocol_seed_completed",
                    message="Brownfield protocol seed stage completed",
                    metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "tasks_path": tasks.tasks_path},
                    protocol_run_id=protocol_run_id,
                    step_run_id=step_run_id,
                )

            self._set_brownfield_bootstrap_state(
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
                project_id=project_id,
                stage="completed",
                status="completed",
                message="Brownfield bootstrap completed",
                spec_run_id=specify.spec_run_id,
            )
            if request.output_mode == "task_cycle":
                self._prepare_bootstrapped_task_cycle_item(
                    step_run_id=step_run_id,
                    protocol_run_id=protocol_run_id,
                    project_id=project_id,
                )
                if self._task_cycle_autonomous_enabled(project):
                    self._run_work_item_autonomously(
                        step_run_id=step_run_id,
                        protocol_run_id=protocol_run_id,
                        project_id=project_id,
                    )
            self._append_project_event(
                project_id,
                event_type="brownfield_run_completed",
                message="Brownfield run completed",
                metadata={**event_metadata, "spec_run_id": specify.spec_run_id, "next_work_item_id": step_run_id},
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
            )
        except Exception as exc:
            self._mark_brownfield_bootstrap_failed(
                project_id,
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
                stage="internal",
                error=str(exc),
                metadata=event_metadata,
            )

    def _task_cycle_autonomous_enabled(self, project) -> bool:
        value = getattr(project, "task_cycle_autonomous", None)
        return False if value is None else bool(value)

    def _run_work_item_autonomously(
        self,
        *,
        step_run_id: int,
        protocol_run_id: int,
        project_id: int,
    ) -> None:
        step = self.db.get_step_run(step_run_id)
        run = self.db.get_protocol_run(protocol_run_id)
        project = self.db.get_project(project_id)
        if not self._task_cycle_autonomous_enabled(project):
            return

        event_metadata = {
            "protocol_run_id": protocol_run_id,
            "step_run_id": step_run_id,
        }
        self._append_project_event(
            project_id,
            event_type="brownfield_task_cycle_autonomous_started",
            message="Autonomous brownfield task-cycle execution started",
            metadata=event_metadata,
            protocol_run_id=protocol_run_id,
            step_run_id=step_run_id,
        )

        try:
            work_item = self.get_work_item(step_run_id)
            loop_limit = max(int(self.config.task_cycle_max_iterations or 1), 1) + 2
            for _ in range(loop_limit):
                if work_item.lifecycle_state != self.LIFECYCLE_ACTIVE or work_item.pr_ready:
                    break
                if work_item.context_status != "ready":
                    work_item = self.build_context(step_run_id, refresh=False)
                    if work_item.context_status != "ready":
                        break
                    continue
                if work_item.plan_status != "ready":
                    work_item = self.plan(step_run_id, refresh=False)
                    if work_item.plan_status != "ready":
                        break
                    continue
                if work_item.status in {self.STATUS_BLOCKED, self.STATUS_NEEDS_REWORK}:
                    break
                if work_item.review_status == "needs_refactor" and work_item.qa_status == "passed":
                    work_item = self.refactor(step_run_id, owner_agent=work_item.owner_agent)
                    continue
                if work_item.status in {self.STATUS_QUEUED, self.STATUS_CONTEXT_READY, self.STATUS_PLAN_READY}:
                    work_item = self.implement(step_run_id, owner_agent=work_item.owner_agent)
                    continue
                if work_item.status in {
                    self.STATUS_AWAITING_REVIEW,
                    self.STATUS_READY_FOR_PR,
                    self.STATUS_NEEDS_REFACTOR,
                } or work_item.review_status in {"pending", "needs_refactor"}:
                    work_item, review = self.review(step_run_id)
                    if review.verdict == "failed":
                        break
                    qa_out = self.qa(step_run_id)
                    work_item = qa_out.work_item
                    if work_item.qa_status != "passed":
                        break
                    if work_item.review_status == "needs_refactor":
                        continue
                    work_item = self.mark_pr_ready(step_run_id)
                    break
                if work_item.status == self.STATUS_PR_READY:
                    break
                break

            final_item = self.get_work_item(step_run_id)
            self._append_project_event(
                project_id,
                event_type=(
                    "brownfield_task_cycle_autonomous_completed"
                    if final_item.pr_ready
                    else "brownfield_task_cycle_autonomous_blocked"
                ),
                message=(
                    "Autonomous brownfield task-cycle completed"
                    if final_item.pr_ready
                    else "Autonomous brownfield task-cycle paused for operator attention"
                ),
                metadata={
                    **event_metadata,
                    "status": final_item.status,
                    "active_stage": final_item.active_stage,
                    "blocking_reason": final_item.blocking_reason,
                },
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
            )
        except Exception as exc:
            self._append_project_event(
                project_id,
                event_type="brownfield_task_cycle_autonomous_failed",
                message="Autonomous brownfield task-cycle failed",
                metadata={**event_metadata, "error": str(exc)},
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
            )

    def _brownfield_protocol_name(self, request: schemas.BrownfieldRunRequest) -> str:
        raw = (
            self._string_or_none(request.protocol_name)
            or self._string_or_none(request.feature_name)
            or (request.feature_request or "").strip()[:50]
            or "brownfield-task"
        )
        return self._slugify(raw) or "brownfield-task"

    def _brownfield_step_name(self, protocol_name: str) -> str:
        return f"step-01-{self._slugify(protocol_name) or 'brownfield-task'}"

    def _find_reusable_brownfield_run(self, project_id: int, protocol_name: str, output_mode: str):
        for run in self.db.list_protocol_runs(project_id):
            metadata = dict(run.speckit_metadata or {})
            if run.protocol_name != protocol_name:
                continue
            if (metadata.get("brownfield_output_mode") or "task_cycle") != output_mode:
                continue
            if run.status in {"failed", "completed", "cancelled"}:
                continue
            if metadata.get("task_cycle") or metadata.get("brownfield_output_mode"):
                return run
        return None

    def _set_brownfield_bootstrap_state(
        self,
        *,
        protocol_run_id: int,
        step_run_id: int,
        project_id: int,
        stage: str,
        status: str,
        message: str,
        spec_run_id: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        protocol_run = self.db.get_protocol_run(protocol_run_id)
        protocol_metadata = dict(protocol_run.speckit_metadata or {})
        protocol_metadata.update(
            {
                "task_cycle": bool(protocol_metadata.get("task_cycle")),
                "brownfield_bootstrap_stage": stage,
                "brownfield_bootstrap_status": status,
                "brownfield_bootstrap_error": error,
            }
        )
        if spec_run_id is not None:
            protocol_metadata["spec_run_id"] = spec_run_id
        self.db.update_protocol_windmill(protocol_run_id, speckit_metadata=protocol_metadata)

        step = self.db.get_step_run(step_run_id)
        project = self.db.get_project(project_id)
        state = self._task_cycle_state(step, project)
        state["bootstrap_stage"] = stage
        state["bootstrap_status"] = status
        state["bootstrap_error"] = error
        if spec_run_id is not None:
            state["spec_run_id"] = spec_run_id
        if status == "failed":
            state["status"] = self.STATUS_BLOCKED
            state["last_failure_source"] = "bootstrap"
        elif status in {"queued", "running"}:
            state["status"] = self.STATUS_QUEUED
            state["last_failure_source"] = None
        self._persist_task_cycle_state(step, state)
        self.db.update_step_run(step_run_id, summary=message)

    def _mark_brownfield_bootstrap_failed(
        self,
        project_id: int,
        *,
        protocol_run_id: int,
        step_run_id: int,
        stage: str,
        error: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        failure_metadata = {**(metadata or {}), "stage": stage, "error": error}
        self._set_brownfield_bootstrap_state(
            protocol_run_id=protocol_run_id,
            step_run_id=step_run_id,
            project_id=project_id,
            stage=stage,
            status="failed",
            message=f"Brownfield bootstrap failed during {stage}: {error}",
            spec_run_id=failure_metadata.get("spec_run_id"),
            error=error,
        )
        self.db.update_protocol_status(protocol_run_id, "failed")
        self._append_project_event(
            project_id,
            event_type=f"brownfield_{stage}_failed",
            message=f"Brownfield {stage} failed: {error}",
            metadata=failure_metadata,
            protocol_run_id=protocol_run_id,
            step_run_id=step_run_id,
        )
        self._append_project_event(
            project_id,
            event_type="brownfield_run_failed",
            message=f"Brownfield run failed during {stage}: {error}",
            metadata=failure_metadata,
            protocol_run_id=protocol_run_id,
            step_run_id=step_run_id,
        )

    def build_context(self, step_run_id: int, *, refresh: bool = False) -> schemas.WorkItemOut:
        step, run, project = self._load_work_item(step_run_id)
        self._ensure_work_item_active(step, project)
        self._ensure_bootstrap_ready(step, project)
        task_dir = self._task_dir(project, step)
        refs = self._artifact_refs(project, step)
        context_json = Path(refs["context_pack_json"])
        plan_json = Path(refs["plan_pack_json"])

        if context_json.exists() and not refresh:
            state = self._task_cycle_state(step, project)
            state["context_status"] = "ready"
            state["plan_status"] = self._default_plan_status(refs, current_state=state)
            state["status"] = state["status"] if state["status"] != self.STATUS_QUEUED else self.STATUS_CONTEXT_READY
            self._persist_task_cycle_state(step, state)
            return self.get_work_item(step.id)

        workspace_root = self._workspace_root(run, project)
        protocol_root = self._protocol_root(run, workspace_root)
        step_prompt_path = protocol_root / f"{step.step_name}.md"
        plan_path = protocol_root / "plan.md"
        step_text = step_prompt_path.read_text(encoding="utf-8") if step_prompt_path.exists() else (step.summary or "")
        plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""

        manifests = self._discover_manifest_files(workspace_root)
        style_guides = self._discover_style_guides(workspace_root)
        path_refs = self._extract_path_references(step_text, plan_text)
        code_refs = self._discover_code_files(workspace_root, step, path_refs)
        required_files = self._curate_required_files(
            workspace_root,
            protocol_root,
            step_prompt_path,
            plan_path,
            path_refs,
            code_refs,
        )
        entry_points = self._entry_points(workspace_root, protocol_root, step_prompt_path, plan_path, required_files)
        acceptance_criteria = self._extract_acceptance_criteria(step_text)
        review_focus = acceptance_criteria[:3] if acceptance_criteria else [f"Validate implementation for {step.step_name}"]
        goal = self._extract_goal(step_text, step)
        test_commands = self._detect_test_commands(workspace_root)
        open_questions = self._context_open_questions(entry_points, required_files, test_commands)
        clarifications = self._ensure_context_clarifications(
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
            title=step.step_name,
            open_questions=open_questions,
        )

        payload: Dict[str, Any] = {
            "context_version": "1",
            "mode": "incremental_context_refresh" if refresh else "fresh_context",
            "work_item_id": f"step-{step.id}",
            "project_id": project.id,
            "protocol_run_id": run.id,
            "step_run_id": step.id,
            "title": step.step_name,
            "goal": goal,
            "acceptance_criteria": acceptance_criteria,
            "status": "context_ready",
            "repo_root": str(workspace_root),
            "base_branch": run.base_branch,
            "entry_points": entry_points,
            "required_files": required_files,
            "candidate_files": required_files,
            "code_context_files": code_refs,
            "allowed_files": [item["path"] for item in required_files[:8]],
            "forbidden_paths": self._forbidden_paths(workspace_root),
            "example_files": [item["path"] for item in code_refs[:3]],
            "contracts": [],
            "types": [],
            "schemas": [],
            "manifest_files": manifests,
            "style_guides": style_guides,
            "test_commands": test_commands,
            "review_focus": review_focus,
            "architecture_notes": self._architecture_notes(required_files, code_refs),
            "risks": self._derive_risks(step, required_files),
            "assumptions": [],
            "open_questions": open_questions,
            "clarification_refs": clarifications,
            "dependencies": list(step.depends_on or []),
            "artifact_refs": refs,
            "generated_at": self._now_iso(),
        }

        task_dir.mkdir(parents=True, exist_ok=True)
        context_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        Path(refs["context_pack_md"]).write_text(self._render_context_markdown(payload), encoding="utf-8")

        state = self._task_cycle_state(step, project)
        state["context_status"] = "needs_clarification" if open_questions else "ready"
        state["plan_status"] = self._default_plan_status(refs, current_state=state)
        if state["status"] == self.STATUS_QUEUED:
            state["status"] = self.STATUS_CONTEXT_READY
        self._persist_task_cycle_state(step, state)
        return self.get_work_item(step.id)

    def plan(self, step_run_id: int, *, refresh: bool = False) -> schemas.WorkItemOut:
        step, run, project = self._load_work_item(step_run_id)
        self._ensure_work_item_active(step, project)
        self._ensure_bootstrap_ready(step, project)
        self.build_context(step.id, refresh=False)
        refs = self._artifact_refs(project, step)
        plan_json = Path(refs["plan_pack_json"])
        if plan_json.exists() and not refresh:
            state = self._task_cycle_state(step, project)
            state["plan_status"] = self._default_plan_status(refs, current_state=state)
            if state["status"] in {self.STATUS_QUEUED, self.STATUS_CONTEXT_READY} and state["plan_status"] == "ready":
                state["status"] = self.STATUS_PLAN_READY
            elif state["plan_status"] == "needs_split":
                state["status"] = self.STATUS_BLOCKED
                state["last_failure_source"] = "plan"
            self._persist_task_cycle_state(step, state)
            return self.get_work_item(step.id)

        context_pack = self._read_json(Path(refs["context_pack_json"]))
        if not context_pack:
            raise TaskCycleError("Build context before generating a plan")

        protocol_root = self._protocol_root(run, self._workspace_root(run, project))
        source_plan_path = protocol_root / "plan.md"
        plan_source_text = source_plan_path.read_text(encoding="utf-8") if source_plan_path.exists() else ""
        candidate_files = self._string_list(
            [item.get("path") for item in context_pack.get("candidate_files", []) if isinstance(item, dict)]
        )
        required_files = self._string_list(
            [item.get("path") for item in context_pack.get("required_files", []) if isinstance(item, dict)]
        )
        files_to_modify = [
            path
            for path in dict.fromkeys(required_files + candidate_files)
            if path
            and not path.endswith(".md")
            and not path.endswith(".json")
            and not path.startswith("specs/")
        ][:8]
        api_surface_files = self._api_surface_files(files_to_modify)
        scope_blocking_findings = self._plan_scope_blocking_findings(
            files_to_modify=files_to_modify,
            public_api_changes=api_surface_files,
        )

        plan_payload: Dict[str, Any] = {
            "plan_version": "1",
            "work_item_id": step.id,
            "protocol_run_id": run.id,
            "project_id": project.id,
            "title": step.step_name,
            "goal": context_pack.get("goal") or step.summary or step.step_name,
            "acceptance_criteria": context_pack.get("acceptance_criteria") or [],
            "files_to_modify": files_to_modify,
            "files_to_create": [],
            "public_api_changes": api_surface_files,
            "data_model_changes": [],
            "test_plan": context_pack.get("test_commands") or [],
            "rollback_risks": context_pack.get("risks") or [],
            "scope_assessment": {
                "touched_file_count": len(files_to_modify),
                "context_candidate_count": len(candidate_files),
                "public_api_surface_count": len(api_surface_files),
                "status": "needs_split" if scope_blocking_findings else "bounded",
                "blocking_findings": scope_blocking_findings,
                "limits": {
                    "max_touched_files": self.MAX_PLAN_TOUCHED_FILES,
                    "max_public_api_surface_files": self.MAX_PUBLIC_API_SURFACE_FILES,
                },
            },
            "constraints": {
                "allowed_files": context_pack.get("allowed_files") or files_to_modify,
                "forbidden_paths": context_pack.get("forbidden_paths") or [],
                "example_files": context_pack.get("example_files") or [],
            },
            "source_refs": {
                "context_pack_json": refs["context_pack_json"],
                "protocol_plan_md": str(source_plan_path) if source_plan_path.exists() else None,
                "step_prompt": next(
                    (
                        item.get("path")
                        for item in context_pack.get("entry_points", [])
                        if isinstance(item, dict) and str(item.get("path", "")).endswith(".md")
                    ),
                    None,
                ),
            },
            "notes": self._plan_notes_from_source(plan_source_text),
            "generated_at": self._now_iso(),
        }

        task_dir = Path(refs["task_dir"])
        task_dir.mkdir(parents=True, exist_ok=True)
        Path(refs["plan_pack_json"]).write_text(json.dumps(plan_payload, indent=2), encoding="utf-8")
        Path(refs["plan_pack_md"]).write_text(self._render_plan_markdown(plan_payload), encoding="utf-8")

        state = self._task_cycle_state(step, project)
        state["plan_status"] = "needs_split" if scope_blocking_findings else "ready"
        if scope_blocking_findings:
            state["status"] = self.STATUS_BLOCKED
            state["last_failure_source"] = "plan"
        elif state["status"] in {self.STATUS_QUEUED, self.STATUS_CONTEXT_READY, self.STATUS_BLOCKED}:
            state["status"] = self.STATUS_PLAN_READY
            state["last_failure_source"] = None
        self._persist_task_cycle_state(step, state)
        return self.get_work_item(step.id)

    def implement(self, step_run_id: int, *, owner_agent: Optional[str] = None) -> schemas.WorkItemOut:
        step, run, project = self._load_work_item(step_run_id)
        state = self._task_cycle_state(step, project)
        self._ensure_work_item_active(step, project, state=state)
        self._ensure_bootstrap_ready(step, project, state=state)
        if state.get("context_status") != "ready":
            raise TaskCycleError("Build context before implementation")
        if state.get("plan_status") != "ready" or not Path(self._artifact_refs(project, step)["plan_pack_json"]).exists():
            raise TaskCycleError("Generate a plan before implementation")
        implement_override = self._resolve_stage_assignment(project.id, "task_cycle_implement")
        resolved_owner_agent = self._resolve_owner_agent(
            project.id,
            owner_agent
            or implement_override.get("agent_id")
            or self._string_or_none(state.get("owner_agent"))
            or step.assigned_agent,
        )
        if resolved_owner_agent and resolved_owner_agent != step.assigned_agent:
            self.db.update_step_assigned_agent(step.id, resolved_owner_agent)
            step = self.db.get_step_run(step.id)

        iterations = int(state.get("iteration_count", 0) or 0)
        max_iterations = int(state.get("max_iterations", self.config.task_cycle_max_iterations) or self.config.task_cycle_max_iterations)
        if iterations >= max_iterations:
            state["status"] = self.STATUS_BLOCKED
            state["last_failure_source"] = "iteration_limit"
            self._persist_task_cycle_state(step, state)
            raise TaskCycleError(f"Max task-cycle iterations reached ({max_iterations})")

        state["iteration_count"] = iterations + 1
        state["max_iterations"] = max_iterations
        state["owner_agent"] = resolved_owner_agent or step.assigned_agent or state.get("owner_agent")
        state["status"] = self.STATUS_IN_PROGRESS
        state["review_status"] = "pending"
        state["qa_status"] = "pending"
        state["refactor_status"] = "not_needed"
        state["refactor_started_at"] = None
        state["refactor_completed_at"] = None
        state["pr_ready"] = False
        state["active_stage_override"] = {
            "stage": "implement",
            **implement_override,
        }
        self._persist_task_cycle_state(step, state)

        execution = ExecutionService(self.context, self.db)
        result = execution.execute_step(step.id)
        step = self.db.get_step_run(step.id)
        state = self._task_cycle_state(step, project)

        if not result.success or step.status in (StepStatus.FAILED, StepStatus.TIMEOUT, StepStatus.BLOCKED):
            state["status"] = self.STATUS_NEEDS_REWORK
            state["last_failure_source"] = "implement"
            self._write_rework_pack(
                project=project,
                run=run,
                step=step,
                source="implement",
                findings=[result.error or f"Implementation ended in {step.status}"],
            )
        else:
            # Task-cycle QA is an explicit stage with its own persisted artifacts.
            state["qa_status"] = "pending"
            state["status"] = self.STATUS_AWAITING_REVIEW
            state["last_failure_source"] = None
        self._persist_task_cycle_state(step, state)
        return self.get_work_item(step.id)

    def refactor(self, step_run_id: int, *, owner_agent: Optional[str] = None) -> schemas.WorkItemOut:
        step, run, project = self._load_work_item(step_run_id)
        state = self._task_cycle_state(step, project)
        self._ensure_work_item_active(step, project, state=state)
        self._ensure_bootstrap_ready(step, project, state=state)
        if state.get("plan_status") != "ready":
            raise TaskCycleError("Generate a bounded plan before running refactor")
        if state.get("review_status") != "needs_refactor":
            raise TaskCycleError("Review must require refactor before running this stage")
        if state.get("qa_status") != "passed":
            raise TaskCycleError("QA must pass before running refactor")

        implement_override = self._resolve_stage_assignment(project.id, "task_cycle_implement")
        resolved_owner_agent = self._resolve_owner_agent(
            project.id,
            owner_agent
            or implement_override.get("agent_id")
            or self._string_or_none(state.get("owner_agent"))
            or step.assigned_agent,
        )
        if resolved_owner_agent and resolved_owner_agent != step.assigned_agent:
            self.db.update_step_assigned_agent(step.id, resolved_owner_agent)
            step = self.db.get_step_run(step.id)

        iterations = int(state.get("iteration_count", 0) or 0)
        max_iterations = int(state.get("max_iterations", self.config.task_cycle_max_iterations) or self.config.task_cycle_max_iterations)
        if iterations >= max_iterations:
            state["status"] = self.STATUS_BLOCKED
            state["last_failure_source"] = "iteration_limit"
            self._persist_task_cycle_state(step, state)
            raise TaskCycleError(f"Max task-cycle iterations reached ({max_iterations})")

        state["iteration_count"] = iterations + 1
        state["max_iterations"] = max_iterations
        state["owner_agent"] = resolved_owner_agent or step.assigned_agent or state.get("owner_agent")
        state["status"] = self.STATUS_IN_PROGRESS
        state["refactor_status"] = "in_progress"
        state["pr_ready"] = False
        state["active_stage_override"] = {
            "stage": "implement",
            **implement_override,
        }
        state["refactor_started_at"] = self._now_iso()
        self._persist_task_cycle_state(step, state)

        execution = ExecutionService(self.context, self.db)
        result = execution.execute_step(step.id)
        step = self.db.get_step_run(step.id)
        state = self._task_cycle_state(step, project)

        if not result.success or step.status in (StepStatus.FAILED, StepStatus.TIMEOUT, StepStatus.BLOCKED):
            state["status"] = self.STATUS_NEEDS_REFACTOR
            state["refactor_status"] = "failed"
            state["last_failure_source"] = "refactor"
            state["refactor_completed_at"] = self._now_iso()
            self._write_rework_pack(
                project=project,
                run=run,
                step=step,
                source="refactor",
                findings=[result.error or f"Refactor ended in {step.status}"],
            )
        else:
            state["status"] = self.STATUS_AWAITING_REVIEW
            state["review_status"] = "pending"
            state["qa_status"] = "pending"
            state["refactor_status"] = "completed"
            state["last_failure_source"] = None
            state["refactor_completed_at"] = self._now_iso()
            self._clear_rework_pack(self._artifact_refs(project, step))
        self._persist_task_cycle_state(step, state)
        return self.get_work_item(step.id)

    def review(self, step_run_id: int) -> Tuple[schemas.WorkItemOut, schemas.WorkItemReviewOut]:
        step, run, project = self._load_work_item(step_run_id)
        self._ensure_work_item_active(step, project)
        self._ensure_bootstrap_ready(step, project)
        self.build_context(step.id, refresh=False)
        self.plan(step.id, refresh=False)
        refs = self._artifact_refs(project, step)
        task_dir = Path(refs["task_dir"])
        context_pack = self._read_json(Path(refs["context_pack_json"]))
        plan_pack = self._read_json(Path(refs["plan_pack_json"]))
        blocking_findings: List[str] = []
        maintainability_findings: List[str] = []
        warnings: List[str] = []

        step_artifacts_dir = Path(refs["step_artifacts_dir"])
        if not Path(refs["context_pack_json"]).exists():
            blocking_findings.append("Missing context_pack.json")
        if not Path(refs["plan_pack_json"]).exists():
            blocking_findings.append("Missing plan_pack.json")
        if not step_artifacts_dir.exists():
            blocking_findings.append("Missing step artifacts directory")
        if step_artifacts_dir.exists() and not any(step_artifacts_dir.iterdir()):
            warnings.append("Step artifacts directory is empty")
        if step.status in (StepStatus.FAILED, StepStatus.TIMEOUT, StepStatus.BLOCKED):
            blocking_findings.append(f"Step is not in a reviewable state: {step.status}")

        for item in context_pack.get("manifest_files", []):
            path = self._resolve_workspace_path(Path(context_pack["repo_root"]), item.get("path"))
            if path is None or not path.exists():
                warnings.append(f"Referenced manifest missing: {item.get('path')}")
        for item in context_pack.get("style_guides", []):
            path = self._resolve_workspace_path(Path(context_pack["repo_root"]), item.get("path"))
            if path is None or not path.exists():
                warnings.append(f"Referenced style guide missing: {item.get('path')}")
        if not context_pack.get("test_commands"):
            warnings.append("ContextPack does not define test commands")
        if not plan_pack.get("files_to_modify"):
            warnings.append("Plan pack does not define files_to_modify")
        plan_scope = plan_pack.get("scope_assessment") if isinstance(plan_pack.get("scope_assessment"), dict) else {}
        for finding in plan_scope.get("blocking_findings", []) if isinstance(plan_scope, dict) else []:
            if isinstance(finding, str) and finding not in blocking_findings:
                blocking_findings.append(finding)
        scope_blockers, scope_warnings, structure_findings, scope_analysis = self._review_scope_findings(
            step=step,
            run=run,
            project=project,
            context_pack=context_pack,
            plan_pack=plan_pack,
        )
        blocking_findings.extend(scope_blockers)
        warnings.extend(scope_warnings)
        maintainability_findings.extend(structure_findings)
        artifact_errors, artifact_warnings = self._validate_implement_artifacts(step)
        blocking_findings.extend(artifact_errors)
        warnings.extend(artifact_warnings)

        blocking_policy_findings = self._evaluate_blocking_policy_findings(step.id, run, project)
        if blocking_policy_findings:
            blocking_findings.append(f"Policy findings require attention ({blocking_policy_findings})")

        verdict = "passed"
        summary = "Review passed"
        if blocking_findings:
            verdict = "failed"
            summary = f"Review failed with {len(blocking_findings)} blocking findings"
        elif maintainability_findings:
            verdict = "needs_refactor"
            summary = f"Review requires refactor for {len(maintainability_findings)} maintainability finding(s)"
        elif warnings:
            verdict = "passed_with_debt"
            summary = f"Review passed with {len(warnings)} maintainability warning(s)"

        report = {
            "work_item_id": step.id,
            "protocol_run_id": run.id,
            "project_id": project.id,
            "verdict": verdict,
            "summary": summary,
            "blocking_findings": blocking_findings,
            "maintainability_findings": maintainability_findings,
            "warnings": warnings,
            "scope_analysis": scope_analysis,
            "checked_at": self._now_iso(),
            "context_pack_json": refs["context_pack_json"],
        }
        task_dir.mkdir(parents=True, exist_ok=True)
        Path(refs["review_report_json"]).write_text(json.dumps(report, indent=2), encoding="utf-8")
        Path(refs["review_report_md"]).write_text(self._render_review_markdown(report), encoding="utf-8")

        state = self._task_cycle_state(step, project)
        state["review_status"] = verdict
        state["blocking_policy_findings"] = blocking_policy_findings
        if verdict in {"passed", "passed_with_debt"}:
            if state.get("refactor_status") in {"required", "in_progress", "failed", "completed"}:
                state["refactor_status"] = "completed"
            state["status"] = (
                self.STATUS_READY_FOR_PR if state.get("qa_status") == "passed" else self.STATUS_AWAITING_REVIEW
            )
            state["last_failure_source"] = None
            self._clear_rework_pack(refs)
        elif verdict == "needs_refactor":
            state["refactor_status"] = "required"
            state["status"] = (
                self.STATUS_NEEDS_REFACTOR if state.get("qa_status") == "passed" else self.STATUS_AWAITING_REVIEW
            )
            state["last_failure_source"] = None
            self._write_rework_pack(
                project=project,
                run=run,
                step=step,
                source="review",
                findings=maintainability_findings,
                warnings=warnings,
            )
        else:
            state["status"] = self.STATUS_NEEDS_REWORK
            state["last_failure_source"] = "review"
            state["refactor_status"] = "not_needed"
            self._write_rework_pack(
                project=project,
                run=run,
                step=step,
                source="review",
                findings=blocking_findings,
                warnings=warnings,
            )
        self._persist_task_cycle_state(step, state)

        return self.get_work_item(step.id), schemas.WorkItemReviewOut(
            verdict=verdict,
            summary=summary,
            blocking_findings=blocking_findings,
            maintainability_findings=maintainability_findings,
            warnings=warnings,
            scope_analysis=scope_analysis,
        )

    def qa(self, step_run_id: int, *, gates: Optional[List[str]] = None) -> schemas.WorkItemQAOut:
        step, run, project = self._load_work_item(step_run_id)
        refs = self._artifact_refs(project, step)
        state = self._task_cycle_state(step, project)
        self._ensure_work_item_active(step, project, state=state)
        self._ensure_bootstrap_ready(step, project, state=state)
        qa_override = self._resolve_stage_assignment(project.id, "task_cycle_qa")
        step_artifacts_dir = Path(refs["step_artifacts_dir"])
        context_pack_json = Path(refs["context_pack_json"])
        plan_pack_json = Path(refs["plan_pack_json"])
        if not context_pack_json.exists():
            raise TaskCycleError("Build context before running QA")
        if not plan_pack_json.exists():
            raise TaskCycleError("Generate a plan before running QA")
        if step.status in (StepStatus.FAILED, StepStatus.TIMEOUT, StepStatus.BLOCKED):
            raise TaskCycleError(f"Step is not in a QA-ready state: {step.status}")
        if state.get("review_status") not in {"passed", "passed_with_debt", "needs_refactor"}:
            raise TaskCycleError("Review must pass before running QA")
        if not step_artifacts_dir.exists() or not any(step_artifacts_dir.iterdir()):
            raise TaskCycleError("Implementation artifacts are missing; run Implement successfully before QA")
        artifact_errors, _artifact_warnings = self._validate_implement_artifacts(step)
        if artifact_errors:
            raise TaskCycleError(f"Implementation artifacts are incomplete: {'; '.join(artifact_errors)}")
        gate_map = {
            "lint": __import__("devgodzilla.qa.gates", fromlist=["LintGate"]).LintGate,
            "type": __import__("devgodzilla.qa.gates", fromlist=["TypeGate"]).TypeGate,
            "test": __import__("devgodzilla.qa.gates", fromlist=["TestGate"]).TestGate,
        }

        quality = QualityService(self.context, self.db)
        gates_to_run = None
        if gates is not None:
            unknown = [gate for gate in gates if gate not in gate_map]
            if unknown:
                raise TaskCycleError(f"Unknown QA gates: {', '.join(unknown)}")
            gates_to_run = [gate_map[gate]() for gate in gates]
        else:
            gates_to_run = [gate_map["lint"](), gate_map["type"](), gate_map["test"]()]

        # Task-cycle explicit gate selection should stay deterministic.
        # Brownfield task-cycle QA defaults to deterministic repository checks.
        skip_gates = ["prompt_qa"]
        runtime_options = {}
        if qa_override.get("reasoning_effort"):
            runtime_options["reasoning_effort"] = qa_override["reasoning_effort"]
        qa_result = quality.run_qa(
            step.id,
            gates=gates_to_run,
            skip_gates=skip_gates,
            engine_id=qa_override.get("agent_id"),
            model=qa_override.get("model_override"),
            runtime_options=runtime_options or None,
        )
        task_dir = Path(refs["task_dir"])
        task_dir.mkdir(parents=True, exist_ok=True)
        qa_json_path = Path(refs["test_report_json"])
        qa_md_path = Path(refs["test_report_md"])
        qa_report = self._serialize_qa_report(
            qa_result,
            deterministic_default=gates is None,
            requested_gates=gates if gates is not None else ["lint", "type", "test"],
            prompt_gate_included=False,
        )
        qa_json_path.write_text(json.dumps(qa_report, indent=2), encoding="utf-8")
        qa_md_path.write_text(self._render_qa_markdown(qa_report), encoding="utf-8")
        quality.persist_verdict(qa_result, step.id, report_path=qa_md_path)

        qa_out = schemas.QAResultOut(
            verdict=self._map_qa_verdict(qa_result.verdict.value),
            summary=qa_report["summary"],
            gates=[
                schemas.QAGateOut(
                    id=result["id"],
                    name=result["name"],
                    status=result["status"],
                    findings=[
                        schemas.QAFindingOut(
                            severity=finding["severity"],
                            message=finding["message"],
                            file=finding.get("file"),
                            line=finding.get("line"),
                            rule_id=finding.get("rule_id"),
                            suggestion=finding.get("suggestion"),
                        )
                        for finding in result["findings"]
                    ],
                )
                for result in qa_report["gates"]
            ],
        )

        state["qa_status"] = qa_out.verdict
        if qa_out.verdict == "passed":
            if state.get("review_status") == "needs_refactor":
                state["status"] = self.STATUS_NEEDS_REFACTOR
                state["refactor_status"] = "required"
            else:
                state["status"] = (
                    self.STATUS_READY_FOR_PR
                    if state.get("review_status") in {"passed", "passed_with_debt"}
                    else self.STATUS_AWAITING_REVIEW
                )
            state["last_failure_source"] = None
            if state.get("review_status") != "needs_refactor":
                self._clear_rework_pack(refs)
        else:
            state["status"] = self.STATUS_NEEDS_REWORK
            state["last_failure_source"] = "qa"
            state["refactor_status"] = "not_needed"
            findings = [
                finding.message
                for gate in qa_out.gates
                for finding in gate.findings
                if finding.severity in {"error", "warning"}
            ]
            self._write_rework_pack(
                project=project,
                run=run,
                step=step,
                source="qa",
                findings=findings,
                warnings=[],
            )
        self._persist_task_cycle_state(step, state)

        return schemas.WorkItemQAOut(work_item=self.get_work_item(step.id), qa=qa_out)

    def mark_pr_ready(self, step_run_id: int) -> schemas.WorkItemOut:
        step, run, project = self._load_work_item(step_run_id)
        self._ensure_work_item_active(step, project)
        self._ensure_bootstrap_ready(step, project)
        self.build_context(step.id, refresh=False)
        self.plan(step.id, refresh=False)
        state = self._task_cycle_state(step, project)
        refs = self._artifact_refs(project, step)
        blocking_clarifications = self._blocking_clarifications(project.id, run.id, step.id)
        blocking_policy_findings = self._evaluate_blocking_policy_findings(step.id, run, project)
        qa_report = self._read_json(Path(refs["test_report_json"]))
        artifact_errors, _artifact_warnings = self._validate_implement_artifacts(step)

        required_paths = [
            refs["context_pack_json"],
            refs["plan_pack_json"],
            refs["review_report_json"],
            refs["test_report_json"],
        ]
        missing = [path for path in required_paths if not Path(path).exists()]
        if missing:
            raise TaskCycleError(f"Missing required artifacts: {', '.join(missing)}")
        if state.get("review_status") not in {"passed", "passed_with_debt"}:
            raise TaskCycleError("Review must pass before marking PR-ready")
        if state.get("qa_status") != "passed":
            raise TaskCycleError("QA must pass before marking PR-ready")
        if state.get("refactor_status") in {"required", "in_progress", "failed"}:
            raise TaskCycleError("Required refactor must complete before marking PR-ready")
        if artifact_errors:
            raise TaskCycleError(f"Implementation artifacts are incomplete: {'; '.join(artifact_errors)}")
        if not self._qa_report_has_real_gates(qa_report):
            raise TaskCycleError("QA must include at least one deterministic repository gate before marking PR-ready")
        if blocking_clarifications:
            raise TaskCycleError("Blocking clarifications must be resolved before marking PR-ready")
        if blocking_policy_findings:
            raise TaskCycleError("Blocking policy findings must be resolved before marking PR-ready")

        workspace_root = self._workspace_root(run, project)
        commit_scope = self._build_pr_commit_scope(step=step, run=run, project=project)
        changed_files = commit_scope["staged_files"]
        if not changed_files:
            excluded = commit_scope["excluded_generated_files"]
            detail = (
                f" after excluding generated paths ({', '.join(excluded[:5])})"
                if excluded
                else ""
            )
            raise TaskCycleError(f"No product files remain for PR creation{detail}")
        precommit_report = self._run_pr_ready_precommit(
            workspace_root,
            changed_files=changed_files,
        )
        if precommit_report["status"] == "failed":
            findings = self._string_list(precommit_report.get("findings")) or [str(precommit_report.get("summary") or "Pre-commit validation failed")]
            warnings = self._string_list(precommit_report.get("warnings"))
            pr_ready_report = self._build_pr_ready_report(
                step=step,
                run=run,
                project=project,
                precommit_report=precommit_report,
                pr_result=None,
                commit_scope=commit_scope,
            )
            self._write_pr_ready_report(refs, pr_ready_report)
            self._write_rework_pack(
                project=project,
                run=run,
                step=step,
                source="pr_ready",
                findings=findings,
                warnings=warnings,
            )
            state["pr_ready"] = False
            state["status"] = self.STATUS_NEEDS_REWORK
            state["last_failure_source"] = "pr_ready"
            state["blocking_policy_findings"] = blocking_policy_findings
            self._persist_task_cycle_state(step, state)
            return self.get_work_item(step.id)

        pr_result = self._open_task_cycle_pr(
            run,
            project,
            workspace_root=workspace_root,
            changed_files=changed_files,
        )
        pr_ready_report = self._build_pr_ready_report(
            step=step,
            run=run,
            project=project,
            precommit_report=precommit_report,
            pr_result=pr_result,
            commit_scope=commit_scope,
        )
        self._write_pr_ready_report(refs, pr_ready_report)
        if not pr_result.get("success"):
            raise TaskCycleError(str(pr_result.get("message") or "Failed to push branch or create pull request"))

        state["pr_ready"] = True
        state["status"] = self.STATUS_PR_READY
        state["blocking_policy_findings"] = blocking_policy_findings
        state["last_failure_source"] = None
        self._clear_rework_pack(refs)
        self._persist_task_cycle_state(step, state)
        return self.get_work_item(step.id)

    def archive_work_item(self, step_run_id: int, *, reason: Optional[str] = None) -> schemas.WorkItemOut:
        step, _run, project = self._load_work_item(step_run_id)
        state = self._task_cycle_state(step, project)
        if state.get("lifecycle_state") == self.LIFECYCLE_CANCELED:
            raise TaskCycleError("Canceled work items cannot be archived")
        state["lifecycle_state"] = self.LIFECYCLE_ARCHIVED
        state["lifecycle_reason"] = self._string_or_none(reason) or "Archived from task-cycle UI"
        state["lifecycle_changed_at"] = self._now_iso()
        self._persist_task_cycle_state(step, state)
        return self.get_work_item(step.id)

    def cancel_work_item(self, step_run_id: int, *, reason: Optional[str] = None) -> schemas.WorkItemOut:
        step, _run, project = self._load_work_item(step_run_id)
        state = self._task_cycle_state(step, project)
        if state.get("lifecycle_state") == self.LIFECYCLE_ARCHIVED:
            raise TaskCycleError("Archived work items cannot be canceled")
        if state.get("pr_ready"):
            raise TaskCycleError("PR-ready work items cannot be canceled")
        state["lifecycle_state"] = self.LIFECYCLE_CANCELED
        state["lifecycle_reason"] = self._string_or_none(reason) or "Canceled from task-cycle UI"
        state["lifecycle_changed_at"] = self._now_iso()
        self._persist_task_cycle_state(step, state)
        return self.get_work_item(step.id)

    def reassign_owner(self, step_run_id: int, owner_agent: str) -> schemas.WorkItemOut:
        step, _run, project = self._load_work_item(step_run_id)
        state = self._task_cycle_state(step, project)
        self._ensure_work_item_active(step, project, state=state)
        resolved_owner_agent = self._resolve_owner_agent(project.id, owner_agent)
        if not resolved_owner_agent:
            raise TaskCycleError("Owner agent is required")
        if resolved_owner_agent != step.assigned_agent:
            self.db.update_step_assigned_agent(step.id, resolved_owner_agent)
            step = self.db.get_step_run(step.id)
        state["owner_agent"] = resolved_owner_agent
        self._persist_task_cycle_state(step, state)
        return self.get_work_item(step.id)

    def _load_work_item(self, step_run_id: int):
        step = self.db.get_step_run(step_run_id)
        run = self.db.get_protocol_run(step.protocol_run_id)
        project = self.db.get_project(run.project_id)
        step, run = self._reconcile_brownfield_work_item(step, run, project)
        return step, run, project

    def _prepare_bootstrapped_task_cycle_item(
        self,
        *,
        step_run_id: int,
        protocol_run_id: int,
        project_id: int,
    ) -> None:
        try:
            self.build_context(step_run_id, refresh=False)
            self.plan(step_run_id, refresh=False)
        except Exception as exc:
            step = self.db.get_step_run(step_run_id)
            project = self.db.get_project(project_id)
            state = self._task_cycle_state(step, project)
            state["status"] = self.STATUS_BLOCKED
            state["last_failure_source"] = "bootstrap_prepare"
            self._persist_task_cycle_state(step, state)
            self.db.update_step_run(
                step_run_id,
                summary=f"Brownfield bootstrap completed; task-cycle preparation failed: {exc}",
            )
            self._append_project_event(
                project_id,
                event_type="brownfield_task_cycle_prepare_failed",
                message=f"Brownfield task-cycle preparation failed: {exc}",
                metadata={
                    "protocol_run_id": protocol_run_id,
                    "step_run_id": step_run_id,
                    "error": str(exc),
                },
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
            )

    def _reconcile_brownfield_work_item(self, step: StepRun, run, project):
        metadata = dict(run.speckit_metadata or {})
        if not (metadata.get("task_cycle") or metadata.get("brownfield_output_mode") == "task_cycle"):
            return step, run

        current_state = self._task_cycle_state(step, project)
        bootstrap_status = self._string_or_none(current_state.get("bootstrap_status")) or self._string_or_none(
            metadata.get("brownfield_bootstrap_status")
        )
        needs_completion_reconcile = bootstrap_status in {"queued", "running"}
        needs_protocol_root_reconcile = not self._resolve_existing_repo_path(
            self._workspace_root(run, project),
            run.protocol_root or metadata.get("protocol_root"),
        )
        if not needs_completion_reconcile and not needs_protocol_root_reconcile:
            return step, run

        workspace_root = self._workspace_root(run, project)
        inferred_paths = self._infer_protocol_paths(run, step, workspace_root)
        protocol_root = inferred_paths.get("protocol_root")
        step_prompt_path = inferred_paths.get("step_prompt_path")
        tasks_path = inferred_paths.get("tasks_path")
        runtime_ready = bool(protocol_root and step_prompt_path and Path(step_prompt_path).exists() and tasks_path and Path(tasks_path).exists())

        changed = False
        protocol_root_value = self._protocol_root_value(workspace_root, protocol_root) if protocol_root else None
        if protocol_root_value and run.protocol_root != protocol_root_value:
            self.db.update_protocol_paths(
                run.id,
                worktree_path=str(workspace_root),
                protocol_root=protocol_root_value,
            )
            changed = True

        updated_metadata = dict(metadata)
        if protocol_root_value and updated_metadata.get("protocol_root") != protocol_root_value:
            updated_metadata["protocol_root"] = protocol_root_value
            changed = True
        for key in ("spec_path", "plan_path", "tasks_path"):
            value = inferred_paths.get(key)
            if value and updated_metadata.get(key) != str(value):
                updated_metadata[key] = str(value)
                changed = True

        if runtime_ready and bootstrap_status in {"queued", "running"}:
            updated_metadata["brownfield_bootstrap_stage"] = "completed"
            updated_metadata["brownfield_bootstrap_status"] = "completed"
            updated_metadata["brownfield_bootstrap_error"] = None
            current_state["bootstrap_stage"] = "completed"
            current_state["bootstrap_status"] = "completed"
            current_state["bootstrap_error"] = None
            self._persist_task_cycle_state(step, current_state)
            if run.status == "planning":
                self.db.update_protocol_status(run.id, "planned")
            self.db.update_step_run(step.id, summary="Brownfield bootstrap completed")
            changed = True

        if changed:
            self.db.update_protocol_windmill(run.id, speckit_metadata=updated_metadata)
            step = self.db.get_step_run(step.id)
            run = self.db.get_protocol_run(run.id)
        return step, run

    def _task_cycle_state(self, step: StepRun, project) -> Dict[str, Any]:
        runtime_state = dict(step.runtime_state or {})
        current = dict(runtime_state.get(self.RUNTIME_KEY) or {})
        refs = self._artifact_refs(project, step)
        default_plan_status = self._default_plan_status(refs, current_state=current)
        state = {
            "status": current.get("status", self.STATUS_QUEUED),
            "lifecycle_state": current.get("lifecycle_state", self.LIFECYCLE_ACTIVE),
            "lifecycle_reason": current.get("lifecycle_reason"),
            "context_status": current.get("context_status", "ready" if Path(refs["context_pack_json"]).exists() else "missing"),
            "plan_status": current.get("plan_status", default_plan_status),
            "review_status": current.get("review_status", "pending"),
            "qa_status": current.get("qa_status", "pending"),
            "refactor_status": current.get("refactor_status", "not_needed"),
            "pr_ready": bool(current.get("pr_ready", False)),
            "owner_agent": current.get("owner_agent") or step.assigned_agent,
            "helper_agents": self._string_list(current.get("helper_agents")),
            "iteration_count": int(current.get("iteration_count", 0) or 0),
            "max_iterations": int(current.get("max_iterations", self.config.task_cycle_max_iterations) or self.config.task_cycle_max_iterations),
            "task_dir": refs["task_dir"],
            "artifact_refs": refs,
            "blocking_policy_findings": int(current.get("blocking_policy_findings", 0) or 0),
            "last_failure_source": current.get("last_failure_source"),
            "lifecycle_changed_at": current.get("lifecycle_changed_at"),
            "bootstrap_stage": current.get("bootstrap_stage"),
            "bootstrap_status": current.get("bootstrap_status"),
            "bootstrap_error": current.get("bootstrap_error"),
            "spec_run_id": current.get("spec_run_id"),
            "refactor_started_at": current.get("refactor_started_at"),
            "refactor_completed_at": current.get("refactor_completed_at"),
        }
        return state

    def _ensure_work_item_active(self, step: StepRun, project, *, state: Optional[Dict[str, Any]] = None) -> None:
        current = state or self._task_cycle_state(step, project)
        lifecycle_state = self._string_or_none(current.get("lifecycle_state")) or self.LIFECYCLE_ACTIVE
        if lifecycle_state == self.LIFECYCLE_ARCHIVED:
            raise TaskCycleError("Archived work items are read-only")
        if lifecycle_state == self.LIFECYCLE_CANCELED:
            raise TaskCycleError("Canceled work items are read-only")

    def _ensure_bootstrap_ready(self, step: StepRun, project, *, state: Optional[Dict[str, Any]] = None) -> None:
        current = state or self._task_cycle_state(step, project)
        bootstrap_status = self._string_or_none(current.get("bootstrap_status"))
        if bootstrap_status in {"queued", "running"}:
            stage = self._string_or_none(current.get("bootstrap_stage")) or "bootstrap"
            raise TaskCycleError(f"Brownfield bootstrap is still running ({stage})")
        if bootstrap_status == "failed":
            detail = self._string_or_none(current.get("bootstrap_error")) or "Brownfield bootstrap failed"
            raise TaskCycleError(detail)

    def _is_task_cycle_run(self, run) -> bool:
        metadata = dict(run.speckit_metadata or {})
        if metadata.get("task_cycle") or metadata.get("brownfield_output_mode") == "task_cycle":
            return True
        for step in self.db.list_step_runs(run.id):
            runtime_state = dict(step.runtime_state or {})
            if self.RUNTIME_KEY in runtime_state:
                return True
        return False

    def _persist_task_cycle_state(self, step: StepRun, state: Dict[str, Any]) -> StepRun:
        runtime_state = dict(step.runtime_state or {})
        runtime_state[self.RUNTIME_KEY] = state
        return self.db.update_step_run(step.id, runtime_state=runtime_state)

    def _artifact_refs(self, project, step: StepRun) -> Dict[str, str]:
        task_dir = self._task_dir(project, step)
        refs = {
            "task_dir": str(task_dir),
            "context_pack_json": str(task_dir / "context_pack.json"),
            "context_pack_md": str(task_dir / "context_pack.md"),
            "plan_pack_json": str(task_dir / "plan_pack.json"),
            "plan_pack_md": str(task_dir / "plan_pack.md"),
            "review_report_json": str(task_dir / "review_report.json"),
            "review_report_md": str(task_dir / "review_report.md"),
            "test_report_json": str(task_dir / "test_report.json"),
            "test_report_md": str(task_dir / "test_report.md"),
            "pr_ready_report_json": str(task_dir / "pr_ready_report.json"),
            "pr_ready_report_md": str(task_dir / "pr_ready_report.md"),
            "rework_pack_json": str(task_dir / "rework_pack.json"),
            "step_artifacts_dir": str(self._step_artifacts_dir(step)),
        }
        return refs

    def read_artifact_content(self, step_run_id: int, artifact_key: str, *, max_bytes: int = 200_000) -> schemas.ArtifactContentOut:
        step, _run, project = self._load_work_item(step_run_id)
        refs = self._artifact_refs(project, step)
        if artifact_key not in refs:
            raise TaskCycleError(f"Unknown task-cycle artifact: {artifact_key}")
        path = Path(refs[artifact_key])
        if not path.exists() or not path.is_file():
            raise TaskCycleError(f"Artifact not found: {artifact_key}")

        max_bytes = max(1, min(int(max_bytes), 2_000_000))
        raw = path.read_bytes()
        truncated = len(raw) > max_bytes
        if truncated:
            raw = raw[:max_bytes]

        try:
            content = raw.decode("utf-8")
        except Exception:
            content = raw.decode("utf-8", errors="replace")

        return schemas.ArtifactContentOut(
            id=artifact_key,
            name=path.name,
            type=self._artifact_type_from_name(path.name),
            content=content,
            truncated=truncated,
        )

    def _build_runtime_projection(
        self,
        step: StepRun,
        run,
        project,
        work_item: schemas.WorkItemOut,
    ) -> schemas.WorkItemRuntimeOut:
        state = self._task_cycle_state(step, project)
        blocking_clarifications = self._blocking_clarifications(project.id, run.id, step.id)
        stage_runs = self._build_stage_runs(
            step,
            run,
            project,
            state=state,
            blocking_clarifications=blocking_clarifications,
        )
        active_stage_run = next(
            (stage_run for stage_run in stage_runs if stage_run.status not in {"completed", "skipped"}),
            stage_runs[-1],
        )
        latest_completed_stage = next(
            (stage_run.stage_id for stage_run in reversed(stage_runs) if stage_run.status == "completed"),
            None,
        )
        latest_artifacts = sorted(
            [artifact for stage_run in stage_runs for artifact in stage_run.artifacts if artifact.exists],
            key=lambda artifact: artifact.created_at or "",
            reverse=True,
        )[:8]
        blocking_reasons = self._blocking_reasons(
            work_item,
            state=state,
            stage_runs=stage_runs,
        )
        active_agents = [agent for agent in active_stage_run.agent_assignments if agent.status == "running"]
        if not active_agents and active_stage_run.agent_assignments:
            active_agents = active_stage_run.agent_assignments
        windmill = self._windmill_projection(run, step)

        activity = self._build_activity_feed(
            work_item,
            stage_runs=stage_runs,
            latest_artifacts=latest_artifacts,
            windmill=windmill,
            blocking_reasons=blocking_reasons,
        )
        progress_summary = (
            active_stage_run.summary
            or work_item.progress_summary
            or f"{active_stage_run.stage_name} is {active_stage_run.status.replace('_', ' ')}"
        )

        return schemas.WorkItemRuntimeOut(
            work_item=work_item,
            active_stage=active_stage_run.stage_id,
            active_stage_label=active_stage_run.stage_name,
            active_stage_status=active_stage_run.status,
            latest_completed_stage=latest_completed_stage,
            progress_summary=progress_summary,
            blocking_reasons=blocking_reasons,
            active_agents=active_agents,
            stage_runs=stage_runs,
            latest_artifacts=latest_artifacts,
            activity=activity,
            windmill=windmill,
        )

    def _build_stage_overview(
        self,
        step: StepRun,
        run,
        project,
        *,
        state: Optional[Dict[str, Any]] = None,
        blocking_clarifications: Optional[int] = None,
    ) -> Dict[str, Optional[str]]:
        current_state = state or self._task_cycle_state(step, project)
        current_blocking_clarifications = (
            blocking_clarifications
            if blocking_clarifications is not None
            else self._blocking_clarifications(project.id, run.id, step.id)
        )
        stage_runs = self._build_stage_runs(
            step,
            run,
            project,
            state=current_state,
            blocking_clarifications=current_blocking_clarifications,
        )
        active_stage = next(
            (stage_run for stage_run in stage_runs if stage_run.status not in {"completed", "skipped"}),
            stage_runs[-1],
        )
        latest_completed_stage = next(
            (stage_run.stage_name for stage_run in reversed(stage_runs) if stage_run.status == "completed"),
            None,
        )
        latest_artifact = next(
            (
                artifact
                for artifact in sorted(
                    [artifact for stage_run in stage_runs for artifact in stage_run.artifacts if artifact.exists],
                    key=lambda artifact: artifact.created_at or "",
                    reverse=True,
                )
            ),
            None,
        )
        work_item = schemas.WorkItemOut(
            id=step.id,
            project_id=project.id,
            protocol_run_id=run.id,
            title=step.step_name,
            status=str(current_state["status"]),
            lifecycle_state=str(current_state["lifecycle_state"]),
            lifecycle_reason=self._string_or_none(current_state.get("lifecycle_reason")),
            context_status=str(current_state["context_status"]),
            plan_status=str(current_state["plan_status"]),
            review_status=str(current_state["review_status"]),
            qa_status=str(current_state["qa_status"]),
            refactor_status=str(current_state["refactor_status"]),
            owner_agent=self._string_or_none(current_state.get("owner_agent")) or step.assigned_agent,
            helper_agents=self._string_list(current_state.get("helper_agents")),
            task_dir=self._string_or_none(current_state.get("task_dir")),
            artifact_refs=schemas.WorkItemArtifactRefsOut(**self._artifact_refs(project, step)),
            depends_on=list(step.depends_on or []),
            pr_ready=bool(current_state.get("pr_ready", False)),
            blocking_clarifications=int(current_blocking_clarifications or 0),
            blocking_policy_findings=int(current_state.get("blocking_policy_findings", 0) or 0),
            iteration_count=int(current_state.get("iteration_count", 0) or 0),
            max_iterations=int(current_state.get("max_iterations", self.config.task_cycle_max_iterations) or self.config.task_cycle_max_iterations),
            summary=step.summary,
        )
        blocking_reasons = self._blocking_reasons(work_item, state=current_state, stage_runs=stage_runs)
        return {
            "active_stage": active_stage.stage_id,
            "active_stage_label": active_stage.stage_name,
            "active_stage_status": active_stage.status,
            "latest_completed_stage": latest_completed_stage,
            "latest_artifact_summary": (
                f"{self._stage_name(latest_artifact.stage_id)}: {latest_artifact.name}" if latest_artifact else None
            ),
            "blocking_reason": blocking_reasons[0] if blocking_reasons else None,
            "progress_summary": active_stage.summary or f"{active_stage.stage_name} is {active_stage.status.replace('_', ' ')}",
        }

    def _build_stage_runs(
        self,
        step: StepRun,
        run,
        project,
        *,
        state: Optional[Dict[str, Any]] = None,
        blocking_clarifications: Optional[int] = None,
    ) -> List[schemas.WorkItemStageRunOut]:
        current_state = state or self._task_cycle_state(step, project)
        current_blocking_clarifications = (
            blocking_clarifications
            if blocking_clarifications is not None
            else self._blocking_clarifications(project.id, run.id, step.id)
        )
        refs = self._artifact_refs(project, step)
        context_pack = self._read_json(Path(refs["context_pack_json"]))
        plan_pack = self._read_json(Path(refs["plan_pack_json"]))
        review_report = self._read_json(Path(refs["review_report_json"]))
        qa_report = self._read_json(Path(refs["test_report_json"]))
        pr_ready_report = self._read_json(Path(refs["pr_ready_report_json"]))
        rework_pack = self._read_json(Path(refs["rework_pack_json"]))
        step_job_runs = self.db.list_job_runs(step_run_id=step.id, limit=50)
        latest_job_run = step_job_runs[0] if step_job_runs else None
        implement_artifacts = self._runtime_stage_artifacts(step, project, stage_id="implement")

        context_status = self._context_stage_status(
            current_state=current_state,
            blocking_clarifications=current_blocking_clarifications,
            context_exists=Path(refs["context_pack_json"]).exists(),
        )
        plan_status = self._plan_stage_status(
            current_state=current_state,
            context_status=context_status,
            plan_exists=Path(refs["plan_pack_json"]).exists(),
        )
        implement_status = self._implement_stage_status(
            step=step,
            current_state=current_state,
            implement_artifacts=implement_artifacts,
        )
        review_status = self._review_stage_status(
            current_state=current_state,
            plan_status=plan_status,
            implement_status=implement_status,
            review_report=review_report,
        )
        qa_status = self._qa_stage_status(
            current_state=current_state,
            review_status=review_status,
            qa_report=qa_report,
        )
        refactor_status = self._refactor_stage_status(
            current_state=current_state,
            review_status=review_status,
            qa_status=qa_status,
        )
        pr_ready_status = self._pr_ready_stage_status(
            current_state=current_state,
            review_status=review_status,
            qa_status=qa_status,
            refactor_status=refactor_status,
        )

        stage_statuses = {
            "build_context": context_status,
            "plan": plan_status,
            "implement": implement_status,
            "review": review_status,
            "qa": qa_status,
            "refactor": refactor_status,
            "pr_ready": pr_ready_status,
        }

        stage_runs: List[schemas.WorkItemStageRunOut] = []
        for order, (stage_id, stage_name) in enumerate(self.STAGES, start=1):
            stage_runs.append(
                schemas.WorkItemStageRunOut(
                    stage_id=stage_id,
                    stage_name=stage_name,
                    order=order,
                    status=stage_statuses[stage_id],
                    mode=self._stage_mode(stage_id, context_pack),
                    summary=self._stage_summary(
                        stage_id,
                        status=stage_statuses[stage_id],
                        step=step,
                        current_state=current_state,
                        context_pack=context_pack,
                        plan_pack=plan_pack,
                        review_report=review_report,
                        qa_report=qa_report,
                        pr_ready_report=pr_ready_report,
                        rework_pack=rework_pack,
                    ),
                    started_at=self._stage_started_at(stage_id, step, latest_job_run),
                    finished_at=self._stage_finished_at(
                        stage_id,
                        refs=refs,
                        latest_job_run=latest_job_run,
                        current_state=current_state,
                    ),
                    agent_assignments=self._stage_agents(
                        stage_id,
                        project_id=project.id,
                        owner_agent=self._string_or_none(current_state.get("owner_agent")) or step.assigned_agent,
                        helper_agents=self._string_list(current_state.get("helper_agents")),
                        stage_status=stage_statuses[stage_id],
                        active_stage=next(
                            (
                                candidate_stage_id
                                for candidate_stage_id, status in stage_statuses.items()
                                if status not in {"completed", "skipped"}
                            ),
                            "pr_ready",
                        ),
                    ),
                    artifacts=self._runtime_stage_artifacts(
                        step,
                        project,
                        stage_id=stage_id,
                        rework_source=self._string_or_none(rework_pack.get("source")),
                    ),
                    blocking_reasons=self._stage_blocking_reasons(
                        stage_id,
                        current_state=current_state,
                        blocking_clarifications=current_blocking_clarifications,
                        review_report=review_report,
                        qa_report=qa_report,
                        pr_ready_report=pr_ready_report,
                    ),
                    windmill_job_id=latest_job_run.windmill_job_id if stage_id == "implement" and latest_job_run else None,
                    windmill_module_id=self._job_run_module_id(latest_job_run) if stage_id in {"implement", "refactor"} else None,
                    run_ids=[job.run_id for job in step_job_runs] if stage_id in {"implement", "refactor"} else [],
                )
            )
        return stage_runs

    def _context_stage_status(self, *, current_state: Dict[str, Any], blocking_clarifications: int, context_exists: bool) -> str:
        bootstrap_status = self._string_or_none(current_state.get("bootstrap_status"))
        if bootstrap_status == "running":
            return "running"
        if bootstrap_status == "failed":
            return "failed"
        if current_state.get("context_status") == "needs_clarification" or blocking_clarifications:
            return "waiting_for_clarification"
        if context_exists:
            return "completed"
        return "pending"

    def _implement_stage_status(
        self,
        *,
        step: StepRun,
        current_state: Dict[str, Any],
        implement_artifacts: List[schemas.WorkItemRuntimeArtifactOut],
    ) -> str:
        if step.status == StepStatus.RUNNING or current_state.get("status") == self.STATUS_IN_PROGRESS:
            return "running"
        if step.status in (StepStatus.FAILED, StepStatus.TIMEOUT, StepStatus.BLOCKED):
            return "failed" if current_state.get("last_failure_source") == "implement" else "blocked"
        if any(artifact.exists for artifact in implement_artifacts):
            return "completed"
        return "pending"

    def _plan_stage_status(
        self,
        *,
        current_state: Dict[str, Any],
        context_status: str,
        plan_exists: bool,
    ) -> str:
        plan_status = self._string_or_none(current_state.get("plan_status"))
        if plan_status == "needs_split":
            return "failed"
        if plan_status in {"ready", "legacy"} or (plan_exists and plan_status != "needs_split"):
            return "completed"
        if context_status == "completed":
            return "pending"
        return "pending"

    def _review_stage_status(
        self,
        *,
        current_state: Dict[str, Any],
        plan_status: str,
        implement_status: str,
        review_report: Dict[str, Any],
    ) -> str:
        verdict = self._string_or_none(current_state.get("review_status")) or self._string_or_none(review_report.get("verdict"))
        if verdict in {"passed", "passed_with_debt", "needs_refactor"}:
            if int(current_state.get("blocking_policy_findings", 0) or 0) > 0:
                return "blocked"
            return "completed"
        if verdict in {"failed", "warning"}:
            return "failed"
        if plan_status != "completed":
            return "pending"
        if implement_status == "completed":
            return "pending"
        return "pending"

    def _qa_stage_status(
        self,
        *,
        current_state: Dict[str, Any],
        review_status: str,
        qa_report: Dict[str, Any],
    ) -> str:
        verdict = self._string_or_none(current_state.get("qa_status")) or self._string_or_none(qa_report.get("verdict"))
        if verdict == "passed":
            return "completed"
        if verdict in {"failed", "warning"}:
            return "failed"
        if review_status == "completed":
            return "pending"
        return "pending"

    def _refactor_stage_status(
        self,
        *,
        current_state: Dict[str, Any],
        review_status: str,
        qa_status: str,
    ) -> str:
        refactor_status = self._string_or_none(current_state.get("refactor_status")) or "not_needed"
        if refactor_status == "completed":
            return "completed"
        if refactor_status == "failed":
            return "failed"
        if refactor_status == "in_progress":
            return "running"
        if refactor_status == "required" or self._string_or_none(current_state.get("review_status")) == "needs_refactor":
            if qa_status != "completed":
                return "blocked"
            return "pending"
        if review_status == "completed":
            return "skipped"
        return "pending"

    def _pr_ready_stage_status(
        self,
        *,
        current_state: Dict[str, Any],
        review_status: str,
        qa_status: str,
        refactor_status: str,
    ) -> str:
        if bool(current_state.get("pr_ready")):
            return "completed"
        if current_state.get("last_failure_source") == "pr_ready":
            return "failed"
        if review_status == "completed" and qa_status == "completed" and refactor_status in {"completed", "skipped"}:
            return "pending"
        return "pending"

    def _stage_mode(self, stage_id: str, context_pack: Dict[str, Any]) -> Optional[str]:
        if stage_id != "build_context":
            return None
        return self._string_or_none(context_pack.get("mode"))

    def _stage_summary(
        self,
        stage_id: str,
        *,
        status: str,
        step: StepRun,
        current_state: Dict[str, Any],
        context_pack: Dict[str, Any],
        plan_pack: Dict[str, Any],
        review_report: Dict[str, Any],
        qa_report: Dict[str, Any],
        pr_ready_report: Dict[str, Any],
        rework_pack: Dict[str, Any],
    ) -> str:
        if stage_id == "build_context":
            bootstrap_status = self._string_or_none(current_state.get("bootstrap_status"))
            if bootstrap_status == "running":
                stage = self._string_or_none(current_state.get("bootstrap_stage")) or "bootstrap"
                return f"Bootstrapping brownfield run: {stage.replace('_', ' ')}"
            if bootstrap_status == "failed":
                return self._string_or_none(current_state.get("bootstrap_error")) or "Brownfield bootstrap failed"
            if status == "waiting_for_clarification":
                return "Context pack is ready, but blocking clarifications must be resolved"
            goal = self._string_or_none(context_pack.get("goal"))
            return goal or ("Context pack ready" if status == "completed" else "Context pack not built yet")
        if stage_id == "plan":
            if status == "completed":
                if not plan_pack:
                    return "Legacy work item predates explicit plan artifacts"
                count = len(plan_pack.get("files_to_modify") or [])
                return f"Plan ready with {count} proposed file change(s)"
            if status == "failed":
                count = len((plan_pack.get("scope_assessment") or {}).get("blocking_findings") or [])
                return f"Plan exceeds brownfield scope limits ({count} blocking scope finding(s))"
            return "Plan has not been generated yet"
        if stage_id == "implement":
            if status == "running":
                return "Implementation is running"
            if status == "failed":
                return "Implementation failed and requires rework"
            if status == "completed":
                return "Implementation artifacts available"
            return "Implementation has not started"
        if stage_id == "review":
            if review_report.get("summary"):
                return str(review_report["summary"])
            if rework_pack.get("source") == "review":
                return "Review findings require rework"
            return "Review has not run yet"
        if stage_id == "qa":
            if qa_report.get("summary"):
                return str(qa_report["summary"])
            if rework_pack.get("source") == "qa":
                return "QA findings require rework"
            return "QA has not run yet"
        if stage_id == "refactor":
            if current_state.get("refactor_status") == "completed":
                return "Refactor completed and awaits re-review"
            if current_state.get("refactor_status") == "in_progress":
                return "Refactor is running"
            if current_state.get("refactor_status") == "failed":
                return "Refactor failed and needs another pass"
            if current_state.get("review_status") == "needs_refactor":
                return "Review requires structural refactor before PR readiness"
            return "Refactor is not required"
        if stage_id == "pr_ready" and pr_ready_report.get("summary"):
            return str(pr_ready_report["summary"])
        if bool(current_state.get("pr_ready")):
            return "Work item marked PR ready"
        if current_state.get("review_status") in {"passed", "passed_with_debt"} and current_state.get("qa_status") == "passed":
            return "Ready to mark PR ready"
        return "PR readiness is blocked by earlier stages"

    def _stage_started_at(self, stage_id: str, step: StepRun, latest_job_run) -> Optional[str]:
        if stage_id == "implement" and latest_job_run:
            return latest_job_run.started_at or latest_job_run.created_at
        if stage_id == "refactor":
            runtime_state = step.runtime_state if isinstance(step.runtime_state, dict) else {}
            task_cycle = runtime_state.get(self.RUNTIME_KEY) if isinstance(runtime_state, dict) else {}
            if isinstance(task_cycle, dict):
                return self._string_or_none(task_cycle.get("refactor_started_at"))
            return None
        return step.updated_at

    def _stage_finished_at(
        self,
        stage_id: str,
        *,
        refs: Dict[str, str],
        latest_job_run,
        current_state: Dict[str, Any],
    ) -> Optional[str]:
        if stage_id == "build_context":
            return self._path_timestamp_iso(Path(refs["context_pack_json"])) or self._path_timestamp_iso(Path(refs["context_pack_md"]))
        if stage_id == "plan":
            return self._path_timestamp_iso(Path(refs["plan_pack_json"])) or self._path_timestamp_iso(Path(refs["plan_pack_md"]))
        if stage_id == "implement" and latest_job_run:
            return latest_job_run.finished_at or self._path_timestamp_iso(Path(refs["step_artifacts_dir"]))
        if stage_id == "review":
            return self._path_timestamp_iso(Path(refs["review_report_json"])) or self._path_timestamp_iso(Path(refs["review_report_md"]))
        if stage_id == "qa":
            return self._path_timestamp_iso(Path(refs["test_report_json"])) or self._path_timestamp_iso(Path(refs["test_report_md"]))
        if stage_id == "refactor":
            return self._string_or_none(current_state.get("refactor_completed_at"))
        if stage_id == "pr_ready":
            return self._path_timestamp_iso(Path(refs["pr_ready_report_json"])) or self._path_timestamp_iso(Path(refs["pr_ready_report_md"]))
        return None

    def _stage_agents(
        self,
        stage_id: str,
        *,
        project_id: int,
        owner_agent: Optional[str],
        helper_agents: List[str],
        stage_status: str,
        active_stage: str,
    ) -> List[schemas.WorkItemRuntimeAgentOut]:
        agent_status = "ready"
        if active_stage == stage_id:
            if stage_status in {"running", "waiting_for_clarification", "blocked", "failed"}:
                agent_status = stage_status
        agents: List[schemas.WorkItemRuntimeAgentOut] = []
        if stage_id in {"build_context", "plan", "implement", "refactor", "pr_ready"} and owner_agent:
            agents.append(
                schemas.WorkItemRuntimeAgentOut(
                    agent_id=owner_agent,
                    role=(
                        "context_builder"
                        if stage_id == "build_context"
                        else "planner"
                        if stage_id == "plan"
                        else "refactor_owner"
                        if stage_id == "refactor"
                        else "owner"
                    ),
                    status=agent_status,
                )
            )
        if stage_id in {"implement", "refactor"}:
            for helper in helper_agents:
                agents.append(
                    schemas.WorkItemRuntimeAgentOut(
                        agent_id=helper,
                        role="helper",
                        status=agent_status,
                    )
                )
        if stage_id in {"review", "qa"}:
            assignment = self._resolve_stage_assignment(
                project_id,
                "task_cycle_review" if stage_id == "review" else "task_cycle_qa",
            )
            agent_id = assignment.get("agent_id") or owner_agent
            if agent_id:
                agents.append(
                    schemas.WorkItemRuntimeAgentOut(
                        agent_id=agent_id,
                        role="reviewer" if stage_id == "review" else "qa",
                        status=agent_status,
                        model_override=assignment.get("model_override"),
                        reasoning_effort=assignment.get("reasoning_effort"),
                    )
                )
        return agents

    def _runtime_stage_artifacts(
        self,
        step: StepRun,
        project,
        *,
        stage_id: str,
        rework_source: Optional[str] = None,
    ) -> List[schemas.WorkItemRuntimeArtifactOut]:
        refs = self._artifact_refs(project, step)
        stage_ref_map = {
            "build_context": ("context_pack_json", "context_pack_md"),
            "plan": ("plan_pack_json", "plan_pack_md"),
            "review": ("review_report_json", "review_report_md"),
            "qa": ("test_report_json", "test_report_md"),
            "pr_ready": ("pr_ready_report_json", "pr_ready_report_md"),
        }
        artifacts: List[schemas.WorkItemRuntimeArtifactOut] = []
        if stage_id in {"implement", "refactor"}:
            artifacts.extend(self._step_runtime_artifacts(step, stage_id=stage_id))
        for key in stage_ref_map.get(stage_id, ()):
            artifacts.append(self._work_item_runtime_artifact(refs[key], stage_id=stage_id, key=key))
        if Path(refs["rework_pack_json"]).exists() and rework_source and (
            stage_id == rework_source or (stage_id in {"implement", "refactor"} and rework_source not in {"review", "qa"})
        ):
            artifacts.append(
                self._work_item_runtime_artifact(
                    refs["rework_pack_json"],
                    stage_id=stage_id,
                    key="rework_pack_json",
                )
            )
        return sorted(artifacts, key=lambda artifact: artifact.created_at or "", reverse=True)

    def _work_item_runtime_artifact(self, path_str: str, *, stage_id: str, key: str) -> schemas.WorkItemRuntimeArtifactOut:
        path = Path(path_str)
        stat = path.stat() if path.exists() else None
        return schemas.WorkItemRuntimeArtifactOut(
            id=key,
            key=key,
            stage_id=stage_id,
            name=path.name,
            type=self._artifact_type_from_name(path.name),
            path=str(path),
            source="work_item",
            exists=path.exists(),
            size=int(stat.st_size) if stat else 0,
            created_at=self._path_timestamp_iso(path),
            content_source="work_item" if path.exists() else None,
            content_id=key if path.exists() else None,
        )

    def _step_runtime_artifacts(
        self,
        step: StepRun,
        *,
        stage_id: str,
    ) -> List[schemas.WorkItemRuntimeArtifactOut]:
        artifacts_dir = self._step_artifacts_dir(step)
        if not artifacts_dir.exists():
            return []
        artifacts: List[schemas.WorkItemRuntimeArtifactOut] = []
        for path in sorted(artifacts_dir.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
            if not path.is_file():
                continue
            stat = path.stat()
            artifacts.append(
                schemas.WorkItemRuntimeArtifactOut(
                    id=f"{stage_id}:step:{path.name}",
                    key=path.name,
                    stage_id=stage_id,
                    name=path.name,
                    type=self._artifact_type_from_name(path.name),
                    path=str(path),
                    source="step",
                    exists=True,
                    size=int(stat.st_size),
                    created_at=self._path_timestamp_iso(path),
                    content_source="step",
                    content_id=path.name,
                )
            )
        return artifacts

    def _stage_blocking_reasons(
        self,
        stage_id: str,
        *,
        current_state: Dict[str, Any],
        blocking_clarifications: int,
        review_report: Dict[str, Any],
        qa_report: Dict[str, Any],
        pr_ready_report: Dict[str, Any],
    ) -> List[str]:
        reasons: List[str] = []
        if stage_id == "build_context" and blocking_clarifications:
            reasons.append(f"{blocking_clarifications} blocking clarification(s) open")
        if stage_id == "build_context" and self._string_or_none(current_state.get("bootstrap_status")) == "failed":
            reasons.append(self._string_or_none(current_state.get("bootstrap_error")) or "Brownfield bootstrap failed")
        if stage_id == "plan" and current_state.get("context_status") != "ready":
            reasons.append("Context must be ready before planning")
        if stage_id == "plan" and current_state.get("plan_status") == "needs_split":
            reasons.append("Plan scope is too broad and should be split")
        if stage_id == "implement" and current_state.get("last_failure_source") == "implement":
            reasons.append("Implementation failed and produced a rework pack")
        if stage_id == "implement" and current_state.get("plan_status") not in {"ready", "legacy"}:
            reasons.append("Plan must be generated before implementation")
        if stage_id == "review":
            if int(current_state.get("blocking_policy_findings", 0) or 0) > 0:
                reasons.append(f"{int(current_state.get('blocking_policy_findings', 0) or 0)} blocking policy finding(s)")
            for finding in review_report.get("blocking_findings", [])[:2]:
                reasons.append(str(finding))
        if stage_id == "qa":
            for gate in qa_report.get("gates", []):
                findings = gate.get("findings") or []
                if findings:
                    reasons.append(str(findings[0].get("message") or "QA finding"))
            reasons = reasons[:2]
        if stage_id == "refactor":
            if current_state.get("review_status") == "needs_refactor" or current_state.get("refactor_status") in {"required", "in_progress", "failed"}:
                if current_state.get("review_status") != "needs_refactor":
                    reasons.append("Refactor is only used when review requires structural cleanup")
                if current_state.get("qa_status") != "passed":
                    reasons.append("QA must pass before refactor")
        if stage_id == "pr_ready":
            if current_state.get("review_status") not in {"passed", "passed_with_debt"}:
                reasons.append("Review must pass before PR readiness")
            if current_state.get("qa_status") != "passed":
                reasons.append("QA must pass before PR readiness")
            if current_state.get("refactor_status") in {"required", "in_progress", "failed"}:
                reasons.append("Required refactor must complete before PR readiness")
            for finding in pr_ready_report.get("blocking_findings", [])[:2]:
                reasons.append(str(finding))
        return reasons

    def _blocking_reasons(
        self,
        work_item: schemas.WorkItemOut,
        *,
        state: Dict[str, Any],
        stage_runs: List[schemas.WorkItemStageRunOut],
    ) -> List[str]:
        reasons: List[str] = []
        if work_item.lifecycle_state != self.LIFECYCLE_ACTIVE:
            reasons.append(f"Work item is {work_item.lifecycle_state} and read-only")
        if work_item.blocking_clarifications:
            reasons.append(f"{work_item.blocking_clarifications} blocking clarification(s) open")
        if work_item.blocking_policy_findings:
            reasons.append(f"{work_item.blocking_policy_findings} blocking policy finding(s)")
        if state.get("last_failure_source") == "implement":
            reasons.append("Implementation failed; rework required")
        if state.get("last_failure_source") == "review":
            reasons.append("Review failed; rework required")
        if state.get("last_failure_source") == "qa":
            reasons.append("QA failed; rework required")
        if state.get("last_failure_source") == "pr_ready":
            reasons.append("PR-ready validation failed; rework required")
        if state.get("last_failure_source") == "refactor":
            reasons.append("Refactor failed; another pass is required")
        if state.get("last_failure_source") == "plan":
            reasons.append("Plan scope is too broad and should be decomposed")
        if state.get("refactor_status") == "required":
            reasons.append("Review requires structural refactor before PR readiness")
        if state.get("last_failure_source") == "bootstrap":
            reasons.append(self._string_or_none(state.get("bootstrap_error")) or "Brownfield bootstrap failed")
        if state.get("status") == self.STATUS_BLOCKED:
            reasons.append("Task cycle is blocked")
        for stage_run in stage_runs:
            for reason in stage_run.blocking_reasons:
                if reason not in reasons:
                    reasons.append(reason)
        return reasons

    def _build_activity_feed(
        self,
        work_item: schemas.WorkItemOut,
        *,
        stage_runs: List[schemas.WorkItemStageRunOut],
        latest_artifacts: List[schemas.WorkItemRuntimeArtifactOut],
        windmill: Optional[schemas.WorkItemRuntimeWindmillOut],
        blocking_reasons: List[str],
    ) -> List[schemas.WorkItemRuntimeActivityOut]:
        activity: List[schemas.WorkItemRuntimeActivityOut] = []
        for stage_run in stage_runs:
            activity.append(
                schemas.WorkItemRuntimeActivityOut(
                    id=f"stage:{stage_run.stage_id}",
                    kind="stage",
                    stage_id=stage_run.stage_id,
                    status=stage_run.status,
                    message=stage_run.summary or f"{stage_run.stage_name} is {stage_run.status.replace('_', ' ')}",
                    created_at=stage_run.finished_at or stage_run.started_at,
                    agent_id=stage_run.agent_assignments[0].agent_id if stage_run.agent_assignments else None,
                    run_id=stage_run.run_ids[0] if stage_run.run_ids else None,
                    windmill_job_id=stage_run.windmill_job_id,
                )
            )
        for artifact in latest_artifacts[:5]:
            activity.append(
                schemas.WorkItemRuntimeActivityOut(
                    id=f"artifact:{artifact.id}",
                    kind="artifact",
                    stage_id=artifact.stage_id,
                    status="created",
                    message=f"{self._stage_name(artifact.stage_id)} produced {artifact.name}",
                    created_at=artifact.created_at,
                    artifact_key=artifact.key,
                )
            )
        for index, reason in enumerate(blocking_reasons):
            activity.append(
                schemas.WorkItemRuntimeActivityOut(
                    id=f"blocker:{index}",
                    kind="blocker",
                    stage_id=work_item.active_stage,
                    status="blocked",
                    message=reason,
                )
            )
        if windmill and windmill.job_id:
            activity.append(
                schemas.WorkItemRuntimeActivityOut(
                    id="windmill:active",
                    kind="windmill",
                    stage_id="refactor" if work_item.refactor_status == "in_progress" else "implement",
                    status=work_item.active_stage_status,
                    message=f"Windmill job {windmill.job_id}",
                    run_id=windmill.run_id,
                    windmill_job_id=windmill.job_id,
                )
            )
        return sorted(activity, key=lambda item: item.created_at or "", reverse=True)

    def _windmill_projection(self, run, step: StepRun) -> schemas.WorkItemRuntimeWindmillOut:
        job_runs = self.db.list_job_runs(step_run_id=step.id, limit=5)
        latest_job_run = job_runs[0] if job_runs else None
        flow_id = None
        if latest_job_run:
            flow_id = self._string_or_none((latest_job_run.params or {}).get("flow_id"))
        if not flow_id:
            flow_id = self._string_or_none(run.windmill_flow_id)
        return schemas.WorkItemRuntimeWindmillOut(
            flow_id=flow_id,
            job_id=latest_job_run.windmill_job_id if latest_job_run else None,
            module_id=self._job_run_module_id(latest_job_run),
            run_id=latest_job_run.run_id if latest_job_run else None,
        )

    def _job_run_module_id(self, job_run) -> Optional[str]:
        if job_run is None:
            return None
        params = job_run.params or {}
        result = job_run.result or {}
        for key in ("module_id", "module", "script_path", "stage"):
            value = params.get(key)
            if value:
                return str(value)
        for key in ("module_id", "module", "script_path", "stage"):
            value = result.get(key)
            if value:
                return str(value)
        return None

    def _stage_name(self, stage_id: str) -> str:
        for current_stage_id, stage_name in self.STAGES:
            if current_stage_id == stage_id:
                return stage_name
        return stage_id.replace("_", " ").title()

    def _path_timestamp_iso(self, path: Path) -> Optional[str]:
        if not path.exists():
            return None
        try:
            return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        except Exception:
            return None

    def _task_dir(self, project, step: StepRun) -> Path:
        run = self.db.get_protocol_run(step.protocol_run_id)
        workspace_root = self._workspace_root(run, project)
        return workspace_root / ".devgodzilla" / "task-cycle" / "protocols" / str(run.id) / "work-items" / str(step.id)

    def _workspace_root(self, run, project) -> Path:
        try:
            return resolve_workspace_root(run, project)
        except WorkspacePathError as exc:
            raise TaskCycleError(str(exc)) from exc

    def _protocol_root(self, run, workspace_root: Path) -> Path:
        return resolve_protocol_root(run, workspace_root)

    def _resolve_existing_repo_path(self, workspace_root: Path, value: Optional[str]) -> Optional[Path]:
        if not value:
            return None
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = workspace_root / candidate
        candidate = candidate.resolve()
        return candidate if candidate.exists() else None

    def _infer_protocol_paths(self, run, step: StepRun, workspace_root: Path) -> Dict[str, Path]:
        metadata = dict(run.speckit_metadata or {})
        inferred: Dict[str, Path] = {}

        protocol_root = self._resolve_existing_repo_path(workspace_root, run.protocol_root)
        if protocol_root is None:
            protocol_root = self._resolve_existing_repo_path(workspace_root, self._string_or_none(metadata.get("protocol_root")))

        for key in ("spec_path", "plan_path", "tasks_path"):
            resolved = self._resolve_existing_repo_path(workspace_root, self._string_or_none(metadata.get(key)))
            if resolved is not None:
                inferred[key] = resolved

        if protocol_root is None:
            for parent_key in ("tasks_path", "plan_path", "spec_path"):
                parent_path = inferred.get(parent_key)
                if parent_path is not None:
                    candidate = (parent_path.parent / "_runtime").resolve()
                    if candidate.exists():
                        protocol_root = candidate
                        break

        if protocol_root is None:
            for base_name in ("specs", ".protocols"):
                base = workspace_root / base_name
                if not base.exists():
                    continue
                matches = sorted(base.glob(f"*/_runtime/{step.step_name}.md"))
                if matches:
                    protocol_root = matches[0].parent.resolve()
                    break

        if protocol_root is not None:
            inferred["protocol_root"] = protocol_root
            step_prompt_path = (protocol_root / f"{step.step_name}.md").resolve()
            plan_prompt_path = (protocol_root / "plan.md").resolve()
            if step_prompt_path.exists():
                inferred["step_prompt_path"] = step_prompt_path
            if plan_prompt_path.exists():
                inferred["protocol_plan_path"] = plan_prompt_path

            spec_root = protocol_root.parent
            for key, name in (("spec_path", "spec.md"), ("plan_path", "plan.md"), ("tasks_path", "tasks.md")):
                if key not in inferred:
                    candidate = (spec_root / name).resolve()
                    if candidate.exists():
                        inferred[key] = candidate
        return inferred

    def _protocol_root_value(self, workspace_root: Path, protocol_root: Path) -> str:
        try:
            return str(protocol_root.relative_to(workspace_root))
        except Exception:
            return str(protocol_root)

    def _step_artifacts_dir(self, step: StepRun) -> Path:
        run = self.db.get_protocol_run(step.protocol_run_id)
        project = self.db.get_project(run.project_id)
        protocol_root = self._protocol_root(run, self._workspace_root(run, project))
        return protocol_root / ".devgodzilla" / "steps" / str(step.id) / "artifacts"

    def _discover_manifest_files(self, workspace_root: Path) -> List[Dict[str, str]]:
        candidates = (
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "docker-compose.yml",
            "docker-compose.yaml",
        )
        items: List[Dict[str, str]] = []
        for name in candidates:
            path = workspace_root / name
            if path.exists():
                items.append({"path": name, "reason": "Project manifest or tooling definition"})
        return items

    def _discover_style_guides(self, workspace_root: Path) -> List[Dict[str, str]]:
        candidates = (
            "AGENTS.md",
            ".specify/memory/constitution.md",
            ".editorconfig",
        )
        items: List[Dict[str, str]] = []
        for name in candidates:
            path = workspace_root / name
            if path.exists():
                items.append({"path": name, "reason": "Project-specific guidance or coding policy"})
        return items

    def _discover_code_files(self, workspace_root: Path, step: StepRun, path_refs: Iterable[str]) -> List[Dict[str, str]]:
        ranked: List[Tuple[Path, str, int]] = []
        seen: set[Path] = set()
        hints = {token for token in re.split(r"[^a-z0-9]+", f"{step.step_name} {step.summary or ''}".lower()) if len(token) >= 3}
        hints.update(Path(ref).stem.lower() for ref in path_refs if "." in ref)

        for path in self._iter_workspace_files(workspace_root):
            if path in seen:
                continue
            relative = str(path.relative_to(workspace_root)).lower()
            name = path.name.lower()
            score = 0
            for hint in hints:
                if hint and hint in relative:
                    score += 2 if hint in name else 1
            if path.suffix in {".py", ".ts", ".tsx", ".js", ".jsx"}:
                score += 1
            if "test" in relative:
                score += 1
            if score <= 0:
                continue
            seen.add(path)
            ranked.append((path, "Code-first match for the work item", score))

        ranked.sort(key=lambda item: (-item[2], str(item[0])))
        return [
            {"path": str(path.relative_to(workspace_root)), "reason": reason}
            for path, reason, _score in ranked[:8]
        ]

    def _extract_path_references(self, *texts: str) -> List[str]:
        pattern = re.compile(r"(?P<path>[A-Za-z0-9_./-]+\.[A-Za-z0-9_-]+)")
        refs: List[str] = []
        for text in texts:
            for match in pattern.finditer(text or ""):
                refs.append(match.group("path"))
        return refs

    def _curate_required_files(
        self,
        workspace_root: Path,
        protocol_root: Path,
        step_prompt_path: Path,
        plan_path: Path,
        path_refs: Iterable[str],
        code_refs: Iterable[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        files: List[Tuple[Path, str]] = []
        if step_prompt_path.exists():
            files.append((step_prompt_path, "Task prompt for the work item"))
        if plan_path.exists():
            files.append((plan_path, "Protocol or runtime plan for the work item"))
        for ref in path_refs:
            path = self._resolve_workspace_path(workspace_root, ref)
            if path and path.exists() and path.is_file():
                files.append((path, "File referenced by the task context"))
        for ref in code_refs:
            path = self._resolve_workspace_path(workspace_root, ref.get("path"))
            if path and path.exists() and path.is_file():
                files.append((path, ref.get("reason") or "Code-first context file"))
        curated: List[Dict[str, str]] = []
        seen: set[str] = set()
        for path, reason in files:
            label = self._relative_or_absolute(path, workspace_root, protocol_root)
            if label in seen:
                continue
            seen.add(label)
            curated.append({"path": label, "reason": reason})
        return curated

    def _entry_points(
        self,
        workspace_root: Path,
        protocol_root: Path,
        step_prompt_path: Path,
        plan_path: Path,
        required_files: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        if step_prompt_path.exists():
            items.append({"path": self._relative_or_absolute(step_prompt_path, workspace_root, protocol_root), "reason": "Task prompt entry point"})
        if plan_path.exists():
            items.append({"path": self._relative_or_absolute(plan_path, workspace_root, protocol_root), "reason": "Plan entry point"})
        items.extend(required_files[:4])
        unique: List[Dict[str, str]] = []
        seen: set[str] = set()
        for item in items:
            path = item["path"]
            if path in seen:
                continue
            seen.add(path)
            unique.append(item)
        return unique

    def _extract_acceptance_criteria(self, step_text: str) -> List[str]:
        criteria: List[str] = []
        for raw in (step_text or "").splitlines():
            line = raw.strip()
            if line.startswith("- [ ] "):
                criteria.append(line[6:].strip())
            elif line.startswith("- ") and len(criteria) < 5:
                criteria.append(line[2:].strip())
        return criteria[:5]

    def _extract_goal(self, step_text: str, step: StepRun) -> str:
        for raw in (step_text or "").splitlines():
            line = raw.strip()
            if line.startswith("#"):
                return line.lstrip("#").strip()
        return step.summary or step.step_name

    def _derive_risks(self, step: StepRun, required_files: List[Dict[str, str]]) -> List[str]:
        risks = [f"Changes may affect files referenced by {step.step_name}"]
        if required_files:
            risks.append(f"Review interactions across {len(required_files)} curated files")
        return risks

    def _detect_test_commands(self, workspace_root: Path) -> List[str]:
        commands: List[str] = []
        if (workspace_root / "scripts" / "ci" / "test.sh").exists():
            commands.append("scripts/ci/test.sh")
        if (workspace_root / "pytest.ini").exists() or (workspace_root / "tests").exists():
            commands.append("pytest -q")
        package_json = workspace_root / "package.json"
        if package_json.exists():
            try:
                payload = json.loads(package_json.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
            scripts = payload.get("scripts") if isinstance(payload, dict) else {}
            if isinstance(scripts, dict) and "test" in scripts:
                commands.append("npm test")
        return list(dict.fromkeys(commands))

    def _render_context_markdown(self, payload: Dict[str, Any]) -> str:
        lines = [
            f"# Context Pack: {payload['title']}",
            "",
            f"- Work item: `{payload['work_item_id']}`",
            f"- Goal: {payload['goal']}",
            f"- Generated: {payload['generated_at']}",
            "",
            "## Acceptance Criteria",
        ]
        for item in payload.get("acceptance_criteria") or ["No explicit acceptance criteria captured"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Required Files"])
        for item in payload.get("required_files", []):
            lines.append(f"- `{item['path']}`: {item['reason']}")
        lines.extend(["", "## Allowed Files"])
        for item in payload.get("allowed_files", []) or ["None identified"]:
            lines.append(f"- `{item}`")
        lines.extend(["", "## Forbidden Paths"])
        for item in payload.get("forbidden_paths", []) or ["None"]:
            lines.append(f"- `{item}`")
        lines.extend(["", "## Example Files"])
        for item in payload.get("example_files", []) or ["None identified"]:
            lines.append(f"- `{item}`")
        lines.extend(["", "## Test Commands"])
        for command in payload.get("test_commands", []) or ["No explicit test commands detected"]:
            lines.append(f"- `{command}`")
        lines.extend(["", "## Architecture Notes"])
        for item in payload.get("architecture_notes", []) or ["Prefer narrow edits to existing extension points"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Open Questions"])
        for item in payload.get("open_questions", []) or ["None"]:
            lines.append(f"- {item}")
        return "\n".join(lines) + "\n"

    def _render_plan_markdown(self, payload: Dict[str, Any]) -> str:
        lines = [
            f"# Plan Pack: {payload['title']}",
            "",
            f"- Goal: {payload['goal']}",
            f"- Generated: {payload['generated_at']}",
            f"- Scope: `{payload.get('scope_assessment', {}).get('status', 'unknown')}`",
            "",
            "## Files To Modify",
        ]
        for item in payload.get("files_to_modify", []) or ["None identified"]:
            lines.append(f"- `{item}`")
        lines.extend(["", "## Files To Create"])
        for item in payload.get("files_to_create", []) or ["None proposed"]:
            lines.append(f"- `{item}`")
        lines.extend(["", "## Test Plan"])
        for item in payload.get("test_plan", []) or ["No explicit test plan"]:
            lines.append(f"- `{item}`")
        lines.extend(["", "## Constraints"])
        constraints = payload.get("constraints") or {}
        for item in constraints.get("allowed_files", []) or ["No allowed-file list"]:
            lines.append(f"- Allowed: `{item}`")
        for item in constraints.get("forbidden_paths", []) or []:
            lines.append(f"- Forbidden: `{item}`")
        lines.extend(["", "## Notes"])
        for item in payload.get("notes", []) or ["No additional notes"]:
            lines.append(f"- {item}")
        return "\n".join(lines) + "\n"

    def _render_review_markdown(self, report: Dict[str, Any]) -> str:
        lines = [
            f"# Review Report: {report['work_item_id']}",
            "",
            f"- Verdict: `{report['verdict']}`",
            f"- Summary: {report['summary']}",
            f"- Checked: {report['checked_at']}",
            "",
            "## Blocking Findings",
        ]
        for item in report.get("blocking_findings") or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Maintainability Findings"])
        for item in report.get("maintainability_findings") or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Warnings"])
        for item in report.get("warnings") or ["None"]:
            lines.append(f"- {item}")
        scope_analysis = report.get("scope_analysis") if isinstance(report.get("scope_analysis"), dict) else {}
        if scope_analysis:
            lines.extend(
                [
                    "",
                    "## Scope Analysis",
                    f"- Planned files: {len(scope_analysis.get('planned_files') or [])}",
                    f"- Changed files: {len(scope_analysis.get('changed_files') or [])}",
                    f"- Out of scope files: {len(scope_analysis.get('out_of_scope_files') or [])}",
                ]
            )
        return "\n".join(lines) + "\n"

    def _serialize_qa_report(
        self,
        qa_result: QAResult,
        *,
        deterministic_default: bool,
        requested_gates: List[str],
        prompt_gate_included: bool,
    ) -> Dict[str, Any]:
        gates = []
        for result in qa_result.gate_results:
            gates.append(
                {
                    "id": result.gate_id,
                    "name": result.gate_name,
                    "status": self._map_qa_verdict(result.verdict.value if hasattr(result.verdict, "value") else str(result.verdict)),
                    "findings": [
                        {
                            "severity": finding.severity,
                            "message": finding.message,
                            "file": finding.file_path,
                            "line": finding.line_number,
                            "rule_id": finding.rule_id,
                            "suggestion": finding.suggestion,
                        }
                        for finding in result.findings
                    ],
                }
            )
        summary = f"{qa_result.verdict.value.upper()}: {len(qa_result.all_findings)} findings ({len(qa_result.blocking_findings)} blocking)"
        return {
            "work_item_id": qa_result.step_run_id,
            "verdict": self._map_qa_verdict(qa_result.verdict.value),
            "summary": summary,
            "duration_seconds": qa_result.duration_seconds,
            "deterministic_default": deterministic_default,
            "requested_gates": requested_gates,
            "prompt_gate_included": prompt_gate_included,
            "real_gate_count": sum(1 for gate in gates if gate["id"] != "prompt_qa"),
            "gates": gates,
            "generated_at": self._now_iso(),
        }

    def _render_qa_markdown(self, report: Dict[str, Any]) -> str:
        lines = [
            f"# Test Report: {report['work_item_id']}",
            "",
            f"- Verdict: `{report['verdict']}`",
            f"- Summary: {report['summary']}",
            f"- Deterministic: `{report.get('deterministic_default', False)}`",
            f"- Generated: {report['generated_at']}",
            "",
            "## Gates",
        ]
        for gate in report.get("gates", []):
            lines.append(f"- `{gate['id']}`: {gate['status']}")
        return "\n".join(lines) + "\n"

    def _render_pr_ready_markdown(self, report: Dict[str, Any]) -> str:
        lines = [
            f"# PR Ready Report: {report['work_item_id']}",
            "",
            f"- Summary: {report['summary']}",
            f"- Generated: {report['generated_at']}",
            "",
            "## Pre-commit",
            f"- Status: `{report.get('precommit', {}).get('status', 'unknown')}`",
            f"- Command: `{report.get('precommit', {}).get('command', 'n/a')}`",
        ]
        for item in report.get("precommit", {}).get("findings", []) or ["None"]:
            lines.append(f"- {item}")
        commit_scope = report.get("commit_scope") if isinstance(report.get("commit_scope"), dict) else {}
        lines.extend(["", "## Commit Scope"])
        for item in commit_scope.get("staged_files") or ["None"]:
            lines.append(f"- Staged: `{item}`")
        for item in commit_scope.get("excluded_generated_files") or []:
            lines.append(f"- Excluded generated: `{item}`")
        lines.extend(["", "## Pull Request"])
        pull_request = report.get("pull_request") if isinstance(report.get("pull_request"), dict) else {}
        lines.append(f"- Status: `{pull_request.get('status', 'skipped')}`")
        if pull_request.get("url"):
            lines.append(f"- URL: {pull_request['url']}")
        if pull_request.get("message"):
            lines.append(f"- Message: {pull_request['message']}")
        lines.extend(["", "## Blocking Findings"])
        for item in report.get("blocking_findings") or ["None"]:
            lines.append(f"- {item}")
        return "\n".join(lines) + "\n"

    def _qa_report_has_real_gates(self, qa_report: Dict[str, Any]) -> bool:
        gates = qa_report.get("gates")
        if isinstance(gates, list):
            return any(isinstance(gate, dict) and gate.get("id") != "prompt_qa" for gate in gates)
        return False

    def _project_github_token(self, project) -> Optional[str]:
        return ((getattr(project, "secrets", None) or {}).get("github_token") or "").strip() or None

    def _detect_precommit_command(self, workspace_root: Path) -> Optional[List[str]]:
        repo_venv_precommit = workspace_root / ".venv" / "bin" / "pre-commit"
        if repo_venv_precommit.exists():
            return [str(repo_venv_precommit)]
        installed = shutil.which("pre-commit")
        if installed:
            return [installed]
        return None

    def _summarize_precommit_output(self, stdout: str, stderr: str) -> List[str]:
        combined = f"{stdout or ''}\n{stderr or ''}"
        findings: List[str] = []
        ansi_pattern = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
        for raw in combined.splitlines():
            line = ansi_pattern.sub("", raw).strip()
            if not line:
                continue
            if line not in findings:
                findings.append(line)
            if len(findings) >= 10:
                break
        return findings

    def _run_pr_ready_precommit(
        self,
        workspace_root: Path,
        *,
        changed_files: List[str],
    ) -> Dict[str, Any]:
        config_path = workspace_root / ".pre-commit-config.yaml"
        if not config_path.exists():
            return {
                "status": "skipped",
                "summary": "No pre-commit config found; PR-ready validation skipped",
                "command": "n/a",
                "checked_files": changed_files,
                "findings": [],
                "warnings": [],
            }

        command = self._detect_precommit_command(workspace_root)
        if not command:
            return {
                "status": "failed",
                "summary": "pre-commit is configured but no executable was found in the repo venv or PATH",
                "command": "pre-commit",
                "checked_files": changed_files,
                "findings": ["Install pre-commit in the managed repository before marking PR ready"],
                "warnings": [],
            }

        checked_files = [
            path for path in changed_files
            if path and not Path(path).is_absolute() and (workspace_root / path).exists()
        ]
        run_command = [*command, "run"]
        if checked_files:
            run_command.extend(["--files", *checked_files])
        else:
            run_command.append("--all-files")

        result = subprocess.run(
            run_command,
            cwd=workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
        findings = self._summarize_precommit_output(result.stdout or "", result.stderr or "")
        status = "passed" if result.returncode == 0 else "failed"
        summary = (
            f"Pre-commit passed on {len(checked_files) or 'all'} file set(s)"
            if status == "passed"
            else "Pre-commit validation failed; rework is required before PR creation"
        )
        return {
            "status": status,
            "summary": summary,
            "command": " ".join(run_command),
            "checked_files": checked_files,
            "returncode": result.returncode,
            "findings": findings,
            "warnings": [],
        }

    def _build_pr_ready_report(
        self,
        *,
        step: StepRun,
        run,
        project,
        precommit_report: Dict[str, Any],
        pr_result: Optional[Dict[str, Any]],
        commit_scope: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        blocking_findings = []
        if precommit_report.get("status") == "failed":
            blocking_findings.extend(self._string_list(precommit_report.get("findings")))
        if pr_result and not pr_result.get("success"):
            blocking_findings.append(str(pr_result.get("message") or "Failed to create pull request"))
        summary = (
            str(pr_result.get("message"))
            if pr_result and pr_result.get("success")
            else str(precommit_report.get("summary") or "PR-ready validation incomplete")
        )
        return {
            "work_item_id": step.id,
            "protocol_run_id": run.id,
            "project_id": project.id,
            "summary": summary,
            "precommit": precommit_report,
            "commit_scope": commit_scope or {
                "staged_files": [],
                "excluded_generated_files": [],
            },
            "pull_request": pr_result or {"status": "skipped", "message": "Pull request not attempted"},
            "blocking_findings": blocking_findings,
            "generated_at": self._now_iso(),
        }

    def _write_pr_ready_report(self, refs: Dict[str, str], report: Dict[str, Any]) -> None:
        Path(refs["pr_ready_report_json"]).write_text(json.dumps(report, indent=2), encoding="utf-8")
        Path(refs["pr_ready_report_md"]).write_text(self._render_pr_ready_markdown(report), encoding="utf-8")

    def _open_task_cycle_pr(
        self,
        run,
        project,
        *,
        workspace_root: Path,
        changed_files: List[str],
    ) -> Dict[str, Any]:
        git_service = GitService(self.context)
        github_token = self._project_github_token(project)
        success = git_service.push_and_open_pr(
            workspace_root,
            run.protocol_name,
            run.base_branch,
            protocol_run_id=run.id,
            project_id=project.id,
            github_token=github_token,
            changed_files=changed_files,
        )
        pr_url = None
        git_url = (getattr(project, "git_url", None) or "").strip()
        if git_url and "github.com" in git_url:
            owner_repo = git_url.split("github.com/", 1)[-1].replace(".git", "").strip("/")
            if owner_repo:
                pr_url = f"https://github.com/{owner_repo}/compare/{run.base_branch}...{run.protocol_name}"
        return {
            "success": success,
            "status": "created" if success else "failed",
            "url": pr_url,
            "message": "Pull request created or compare view prepared" if success else "Failed to push branch or create pull request",
        }

    def _blocking_clarifications(self, project_id: int, protocol_run_id: int, step_run_id: int) -> int:
        clarifications = self.db.list_clarifications(
            project_id=project_id,
            protocol_run_id=protocol_run_id,
            step_run_id=step_run_id,
            status="open",
        )
        return sum(1 for item in clarifications if bool(getattr(item, "blocking", False)))

    def _evaluate_blocking_policy_findings(self, step_run_id: int, run, project) -> int:
        service = PolicyService(self.context, self.db)
        findings = service.evaluate_step(step_run_id, repo_root=self._workspace_root(run, project))
        blocking = [item for item in findings if str(item.severity).lower() in {"error", "block", "blocking"}]
        return len(blocking)

    def _context_open_questions(
        self,
        entry_points: List[Dict[str, str]],
        required_files: List[Dict[str, str]],
        test_commands: List[str],
    ) -> List[str]:
        questions: List[str] = []
        code_files = [
            item for item in required_files
            if str(item.get("path", "")).endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rb", ".java"))
        ]
        if not code_files:
            questions.append("No code files were confidently identified for this task. Add likely modules or entry points.")
        if len(entry_points) <= 1:
            questions.append("Context tracing found too few entry points. Confirm the primary files or call chain.")
        if not test_commands:
            questions.append("No test command was detected. Add the exact validation command before QA.")
        return questions

    def _ensure_context_clarifications(
        self,
        *,
        project_id: int,
        protocol_run_id: int,
        step_run_id: int,
        title: str,
        open_questions: List[str],
    ) -> List[Dict[str, Any]]:
        if not open_questions:
            return []

        refs: List[Dict[str, Any]] = []
        for idx, question in enumerate(open_questions, start=1):
            key = f"task-cycle-context-{step_run_id}-{idx}"
            row = self.db.upsert_clarification(
                scope=f"step:{step_run_id}",
                project_id=project_id,
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
                key=key,
                question=f"{title}: {question}",
                recommended={"value": "Add likely files, modules, or exact test commands."},
                options=None,
                applies_to="execution",
                blocking=False,
            )
            refs.append(
                {
                    "id": row.id,
                    "key": row.key,
                    "question": row.question,
                    "blocking": bool(row.blocking),
                }
            )
        return refs

    def _forbidden_paths(self, workspace_root: Path) -> List[str]:
        candidates = ["Origins", "archive", "node_modules", ".venv", ".git"]
        return [name for name in candidates if (workspace_root / name).exists()]

    def _architecture_notes(
        self,
        required_files: List[Dict[str, str]],
        code_refs: List[Dict[str, str]],
    ) -> List[str]:
        notes = ["Prefer narrow edits to existing modules before introducing new files."]
        if required_files:
            notes.append(f"Keep the change scoped to the curated context set ({min(len(required_files), 8)} files shown).")
        if code_refs:
            notes.append("Copy nearby patterns from the discovered code-context files instead of introducing a new style.")
        return notes

    def _plan_notes_from_source(self, plan_source_text: str) -> List[str]:
        notes: List[str] = []
        for raw in (plan_source_text or "").splitlines():
            line = raw.strip()
            if line.startswith("- ") or line.startswith("* "):
                notes.append(line[2:].strip())
            elif re.match(r"^\d+\.\s+", line):
                notes.append(re.sub(r"^\d+\.\s+", "", line).strip())
            if len(notes) >= 5:
                break
        return notes

    def _default_plan_status(
        self,
        refs: Dict[str, str],
        *,
        current_state: Optional[Dict[str, Any]] = None,
    ) -> str:
        plan_path = Path(refs["plan_pack_json"])
        if not plan_path.exists():
            if self._should_infer_legacy_plan(current_state):
                return "legacy"
            return "missing"
        payload = self._read_json(plan_path)
        scope = payload.get("scope_assessment") if isinstance(payload.get("scope_assessment"), dict) else {}
        if scope.get("status") == "needs_split":
            return "needs_split"
        return "ready"

    def _should_infer_legacy_plan(self, current_state: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(current_state, dict):
            return False
        if bool(current_state.get("pr_ready")):
            return True
        status = self._string_or_none(current_state.get("status"))
        if status in {
            self.STATUS_IN_PROGRESS,
            self.STATUS_AWAITING_REVIEW,
            self.STATUS_NEEDS_REWORK,
            self.STATUS_NEEDS_REFACTOR,
            self.STATUS_READY_FOR_PR,
            self.STATUS_PR_READY,
        }:
            return True
        if self._string_or_none(current_state.get("review_status")) not in {None, "", "pending"}:
            return True
        if self._string_or_none(current_state.get("qa_status")) not in {None, "", "pending"}:
            return True
        if self._string_or_none(current_state.get("last_failure_source")) in {"implement", "review", "qa", "refactor"}:
            return True
        return False

    def _api_surface_files(self, files_to_modify: List[str]) -> List[str]:
        api_patterns = (
            "/api/",
            "/routes/",
            "/schemas",
            "/cli/",
            "/main.py",
            "frontend/lib/api/",
        )
        return [
            path
            for path in files_to_modify
            if path.endswith("__init__.py") or any(pattern in path for pattern in api_patterns)
        ]

    def _plan_scope_blocking_findings(self, *, files_to_modify: List[str], public_api_changes: List[str]) -> List[str]:
        findings: List[str] = []
        if len(files_to_modify) > self.MAX_PLAN_TOUCHED_FILES:
            findings.append(
                f"Plan touches {len(files_to_modify)} files which exceeds the brownfield limit of {self.MAX_PLAN_TOUCHED_FILES}"
            )
        if len(public_api_changes) > self.MAX_PUBLIC_API_SURFACE_FILES:
            findings.append(
                f"Plan changes {len(public_api_changes)} API-surface files which exceeds the brownfield limit of {self.MAX_PUBLIC_API_SURFACE_FILES}"
            )
        return findings

    def _review_scope_findings(
        self,
        *,
        step: StepRun,
        run,
        project,
        context_pack: Dict[str, Any],
        plan_pack: Dict[str, Any],
    ) -> Tuple[List[str], List[str], List[str], Dict[str, Any]]:
        workspace_root = self._workspace_root(run, project)
        changed_files = self._changed_files_from_artifacts(step)
        planned_files = self._string_list(plan_pack.get("files_to_modify"))
        allowed_files = set(self._string_list(context_pack.get("allowed_files")))
        effective_files = changed_files or planned_files
        out_of_scope_files = sorted(
            path for path in changed_files if allowed_files and path not in allowed_files and path not in planned_files
        )

        blocking_findings: List[str] = []
        warnings: List[str] = []
        maintainability_findings: List[str] = []

        if len(effective_files) > self.MAX_CHANGED_FILES:
            blocking_findings.append(
                f"Change touches {len(effective_files)} files which exceeds the brownfield limit of {self.MAX_CHANGED_FILES}"
            )
        if out_of_scope_files:
            warnings.append(f"Changed files outside the bounded plan: {', '.join(out_of_scope_files[:5])}")

        maintainability_findings.extend(self._python_structure_findings(workspace_root, effective_files))

        scope_analysis = {
            "planned_files": planned_files,
            "changed_files": changed_files,
            "allowed_files": sorted(allowed_files),
            "out_of_scope_files": out_of_scope_files,
            "limits": {
                "max_changed_files": self.MAX_CHANGED_FILES,
                "max_python_module_lines": self.MAX_PYTHON_MODULE_LINES,
                "max_python_function_lines": self.MAX_PYTHON_FUNCTION_LINES,
                "max_python_function_args": self.MAX_PYTHON_FUNCTION_ARGS,
                "max_python_nesting_depth": self.MAX_PYTHON_NESTING_DEPTH,
            },
        }
        return blocking_findings, warnings, maintainability_findings, scope_analysis

    def _changed_files_from_artifacts(self, step: StepRun) -> List[str]:
        refs = self._artifact_refs(self.db.get_project(self.db.get_protocol_run(step.protocol_run_id).project_id), step)
        artifacts_dir = Path(refs["step_artifacts_dir"])
        if not artifacts_dir.exists():
            return []

        changed: List[str] = []
        status_path = artifacts_dir / "git-status.txt"
        if status_path.exists():
            for raw in status_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line:
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    changed.append(parts[1].strip())

        diff_path = artifacts_dir / "changes.diff"
        if diff_path.exists():
            for raw in diff_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if raw.startswith("+++ b/"):
                    changed.append(raw[6:].strip())

        return list(dict.fromkeys(path for path in changed if path and path != "/dev/null"))

    def _build_pr_commit_scope(
        self,
        *,
        step: StepRun,
        run,
        project,
    ) -> Dict[str, List[str]]:
        workspace_root = self._workspace_root(run, project)
        generated_roots = self._generated_pr_roots(
            step=step,
            run=run,
            workspace_root=workspace_root,
        )
        staged_files: List[str] = []
        excluded_generated_files: List[str] = []
        for raw in self._changed_files_from_artifacts(step):
            normalized = self._normalize_repo_relative_path(raw)
            if not normalized:
                continue
            if self._is_generated_pr_path(normalized, generated_roots=generated_roots):
                if normalized not in excluded_generated_files:
                    excluded_generated_files.append(normalized)
                continue
            if normalized not in staged_files:
                staged_files.append(normalized)
        return {
            "staged_files": staged_files,
            "excluded_generated_files": excluded_generated_files,
        }

    def _generated_pr_roots(
        self,
        *,
        step: StepRun,
        run,
        workspace_root: Path,
    ) -> List[str]:
        generated = [".devgodzilla", ".specify"]
        protocol_root = self._resolve_existing_repo_path(workspace_root, run.protocol_root)
        if protocol_root is None:
            protocol_root = self._infer_protocol_paths(run, step, workspace_root).get("protocol_root")
        if protocol_root is not None:
            try:
                protocol_relative = self._normalize_repo_relative_path(str(protocol_root.relative_to(workspace_root)))
            except Exception:
                protocol_relative = None
            if protocol_relative:
                generated.append(protocol_relative)
                spec_root = self._normalize_repo_relative_path(str(PurePosixPath(protocol_relative).parent))
                if spec_root and spec_root not in {"", "."}:
                    generated.append(spec_root)
        return list(dict.fromkeys(path for path in generated if path))

    def _normalize_repo_relative_path(self, raw: Optional[str]) -> Optional[str]:
        value = str(raw or "").strip().replace("\\", "/")
        if value.startswith("./"):
            value = value[2:]
        parts = [part for part in PurePosixPath(value).parts if part not in {"", "."}]
        if not parts or parts[0] == "..":
            return None
        normalized = PurePosixPath(*parts).as_posix()
        return normalized or None

    def _is_generated_pr_path(self, path: str, *, generated_roots: List[str]) -> bool:
        normalized = self._normalize_repo_relative_path(path)
        if not normalized:
            return True
        pure_path = PurePosixPath(normalized)
        parts = pure_path.parts
        name = pure_path.name.lower()
        if any(part == "_runtime" for part in parts):
            return True
        if parts and parts[0] in {".devgodzilla", ".specify"}:
            return True
        if name.endswith((".prompt.md", ".result.json", ".stdout.log", ".stderr.log", ".error.txt")):
            return True
        for root in generated_roots:
            if normalized == root or normalized.startswith(f"{root}/"):
                return True
            if root.startswith(f"{normalized}/"):
                return True
        return False

    def _python_structure_findings(self, workspace_root: Path, files: List[str]) -> List[str]:
        findings: List[str] = []
        for raw_path in files:
            if not raw_path.endswith(".py"):
                continue
            path = self._resolve_workspace_path(workspace_root, raw_path)
            if path is None or not path.exists() or not path.is_file():
                continue
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except Exception as exc:
                findings.append(f"{raw_path}: unable to analyze Python structure ({exc})")
                continue

            line_count = len(source.splitlines())
            if line_count > self.MAX_PYTHON_MODULE_LINES:
                findings.append(
                    f"{raw_path}: module is {line_count} lines (limit {self.MAX_PYTHON_MODULE_LINES})"
                )

            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                end_lineno = getattr(node, "end_lineno", node.lineno)
                function_lines = max(1, int(end_lineno) - int(node.lineno) + 1)
                arg_count = len(getattr(node.args, "args", [])) + len(getattr(node.args, "kwonlyargs", []))
                nesting_depth = self._python_nesting_depth(node)
                if function_lines > self.MAX_PYTHON_FUNCTION_LINES:
                    findings.append(
                        f"{raw_path}:{node.lineno} {node.name} is {function_lines} lines (limit {self.MAX_PYTHON_FUNCTION_LINES})"
                    )
                if arg_count > self.MAX_PYTHON_FUNCTION_ARGS:
                    findings.append(
                        f"{raw_path}:{node.lineno} {node.name} has {arg_count} parameters (limit {self.MAX_PYTHON_FUNCTION_ARGS})"
                    )
                if nesting_depth > self.MAX_PYTHON_NESTING_DEPTH:
                    findings.append(
                        f"{raw_path}:{node.lineno} {node.name} nests to depth {nesting_depth} (limit {self.MAX_PYTHON_NESTING_DEPTH})"
                    )
                if len(findings) >= 10:
                    return findings
        return findings

    def _python_nesting_depth(self, node: ast.AST) -> int:
        branch_nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try, ast.Match)

        def _walk(current: ast.AST, depth: int) -> int:
            max_depth = depth
            for child in ast.iter_child_nodes(current):
                next_depth = depth + 1 if isinstance(child, branch_nodes) else depth
                max_depth = max(max_depth, _walk(child, next_depth))
            return max_depth

        return _walk(node, 0)

    def _validate_implement_artifacts(self, step: StepRun) -> Tuple[List[str], List[str]]:
        refs = self._artifact_refs(self.db.get_project(self.db.get_protocol_run(step.protocol_run_id).project_id), step)
        artifacts_dir = Path(refs["step_artifacts_dir"])
        errors: List[str] = []
        warnings: List[str] = []
        if not artifacts_dir.exists():
            return ["Missing step artifacts directory"], warnings
        files = [path for path in artifacts_dir.iterdir() if path.is_file()]
        if not files:
            return ["Step artifacts directory is empty"], warnings

        diff_path = artifacts_dir / "changes.diff"
        status_path = artifacts_dir / "git-status.txt"
        if diff_path.exists() and diff_path.stat().st_size == 0:
            errors.append("changes.diff is empty")
        if status_path.exists() and status_path.stat().st_size == 0:
            errors.append("git-status.txt is empty")
        if not diff_path.exists():
            warnings.append("changes.diff is missing")
        if not status_path.exists():
            warnings.append("git-status.txt is missing")
        if not any(path.name in {"execution.json", "stdout.log", "stderr.log", "execution.log"} for path in files):
            warnings.append("Execution log artifacts are missing")
        return errors, warnings

    def _clear_rework_pack(self, refs: Dict[str, str]) -> None:
        path = Path(refs["rework_pack_json"])
        if path.exists():
            path.unlink()

    def _seed_task_cycle_metadata(
        self,
        protocol_run_id: int,
        *,
        owner_agent: Optional[str],
        helper_agents: List[str],
    ) -> None:
        run = self.db.get_protocol_run(protocol_run_id)
        project = self.db.get_project(run.project_id)
        resolved_owner_agent = self._resolve_owner_agent(project.id, owner_agent)
        protocol_metadata = dict(run.speckit_metadata or {})
        protocol_metadata["task_cycle"] = True
        self.db.update_protocol_windmill(run.id, speckit_metadata=protocol_metadata)
        for step in self.db.list_step_runs(protocol_run_id):
            if resolved_owner_agent and resolved_owner_agent != step.assigned_agent:
                self.db.update_step_assigned_agent(step.id, resolved_owner_agent)
                step = self.db.get_step_run(step.id)
            state = self._task_cycle_state(step, project)
            state["owner_agent"] = resolved_owner_agent or step.assigned_agent
            state["helper_agents"] = self._string_list(helper_agents)
            self._persist_task_cycle_state(step, state)

    def _default_exec_engine_id(self, project_id: int) -> str:
        candidate: Optional[str] = None
        try:
            cfg = AgentConfigService(self.context, db=self.db)
            candidate = cfg.get_default_engine_id(
                "exec",
                project_id=project_id,
                fallback=self.context.config.engine_defaults.get("exec"),
            )
        except Exception:
            candidate = self.context.config.engine_defaults.get("exec")
        if not isinstance(candidate, str) or not candidate.strip():
            return "opencode"
        return candidate.strip()

    def _resolve_owner_agent(self, project_id: int, owner_agent: Optional[str]) -> Optional[str]:
        candidate = self._string_or_none(owner_agent)
        if candidate is None:
            return None
        if candidate.lower() in {"dev", "developer", "default", "exec"}:
            return self._default_exec_engine_id(project_id)
        return candidate

    def _resolve_stage_assignment(self, project_id: int, stage_key: str) -> Dict[str, Optional[str]]:
        try:
            cfg = AgentConfigService(self.context, db=self.db)
            assignment = cfg.get_assignment(stage_key, project_id=project_id)
        except Exception:
            assignment = None

        if not isinstance(assignment, dict):
            return {}

        metadata = assignment.get("metadata")
        metadata_dict = metadata if isinstance(metadata, dict) else {}
        return {
            "agent_id": self._resolve_owner_agent(project_id, self._string_or_none(assignment.get("agent_id"))),
            "model_override": self._string_or_none(assignment.get("model_override")),
            "reasoning_effort": self._string_or_none(metadata_dict.get("reasoning_effort")),
        }

    def _write_rework_pack(
        self,
        *,
        project,
        run,
        step: StepRun,
        source: str,
        findings: List[str],
        warnings: Optional[List[str]] = None,
    ) -> None:
        refs = self._artifact_refs(project, step)
        task_dir = Path(refs["task_dir"])
        task_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "work_item_id": step.id,
            "protocol_run_id": run.id,
            "project_id": project.id,
            "source": source,
            "reason": f"{source} requires rework",
            "findings": [item for item in findings if item],
            "required_actions": [item for item in findings if item],
            "warnings": [item for item in (warnings or []) if item],
            "supersedes_artifact_refs": {
                "review_report_json": refs["review_report_json"],
                "test_report_json": refs["test_report_json"],
            },
            "generated_at": self._now_iso(),
        }
        Path(refs["rework_pack_json"]).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _resolve_workspace_path(self, workspace_root: Path, raw: Optional[str]) -> Optional[Path]:
        if not raw:
            return None
        path = Path(raw)
        if path.is_absolute():
            return path
        return workspace_root / path

    def _relative_or_absolute(self, path: Path, workspace_root: Path, protocol_root: Path) -> str:
        for base in (workspace_root, protocol_root):
            try:
                return str(path.relative_to(base))
            except Exception:
                continue
        return str(path)

    def _string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    def _string_or_none(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _slugify(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    def _read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise TaskCycleError(f"Failed to read JSON artifact {path}: {exc}") from exc

    def _map_qa_verdict(self, verdict: str) -> str:
        value = str(verdict).lower()
        if value in {"pass", "passed", "skip", "skipped"}:
            return "passed"
        if value == "warn":
            return "warning"
        return "failed"

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _artifact_type_from_name(self, name: str) -> str:
        lower = name.lower()
        if lower.endswith(".log") or "log" in lower:
            return "log"
        if lower.endswith(".diff") or lower.endswith(".patch"):
            return "diff"
        if lower.endswith(".json"):
            return "json"
        if lower.endswith(".md") or lower.endswith(".txt"):
            return "text"
        return "file"

    def _iter_workspace_files(self, workspace_root: Path) -> Iterable[Path]:
        ignored_dirs = {
            ".git",
            ".idea",
            ".next",
            ".venv",
            "node_modules",
            "__pycache__",
            ".mypy_cache",
            ".pytest_cache",
            "_runtime",
        }
        for path in workspace_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in ignored_dirs for part in path.parts):
                continue
            yield path
