"""
DevGodzilla SpecKit API Routes

REST endpoints for SpecKit integration: initialization, spec generation,
planning, and task management.
"""

from typing import Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from devgodzilla.api.dependencies import get_db, get_service_context
from devgodzilla.db.database import Database
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.specification import SpecificationService
from devgodzilla.services.policy import PolicyService

router = APIRouter(prefix="/speckit", tags=["SpecKit"])


class InitRequest(BaseModel):
    project_id: int
    constitution_content: Optional[str] = None


class SpecKitResponse(BaseModel):
    success: bool
    path: Optional[str] = None
    constitution_hash: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class SpecifyRequest(BaseModel):
    project_id: int
    description: str = Field(..., min_length=10, description="Feature description")
    feature_name: Optional[str] = Field(None, description="Optional feature name")
    base_branch: Optional[str] = Field(None, description="Optional base branch for the spec run")


class SpecifyResponse(BaseModel):
    success: bool
    spec_path: Optional[str] = None
    spec_number: Optional[int] = None
    feature_name: Optional[str] = None
    spec_run_id: Optional[int] = None
    worktree_path: Optional[str] = None
    branch_name: Optional[str] = None
    base_branch: Optional[str] = None
    spec_root: Optional[str] = None
    error: Optional[str] = None


class PlanRequest(BaseModel):
    project_id: int
    spec_path: str = Field(..., description="Path to spec.md file")
    spec_run_id: Optional[int] = Field(None, description="Optional SpecRun id")


class PlanResponse(BaseModel):
    success: bool
    plan_path: Optional[str] = None
    data_model_path: Optional[str] = None
    contracts_path: Optional[str] = None
    spec_run_id: Optional[int] = None
    worktree_path: Optional[str] = None
    error: Optional[str] = None


class TasksRequest(BaseModel):
    project_id: int
    plan_path: str = Field(..., description="Path to plan.md file")
    spec_run_id: Optional[int] = Field(None, description="Optional SpecRun id")


class TasksResponse(BaseModel):
    success: bool
    tasks_path: Optional[str] = None
    task_count: int = 0
    parallelizable_count: int = 0
    spec_run_id: Optional[int] = None
    worktree_path: Optional[str] = None
    error: Optional[str] = None


class ClarificationEntry(BaseModel):
    question: str
    answer: str


class ClarifyRequest(BaseModel):
    project_id: int
    spec_path: str = Field(..., description="Path to spec file")
    entries: List[ClarificationEntry] = Field(default_factory=list)
    notes: Optional[str] = None
    spec_run_id: Optional[int] = Field(None, description="Optional SpecRun id")


class ClarifyResponse(BaseModel):
    success: bool
    spec_path: Optional[str] = None
    clarifications_added: int = 0
    spec_run_id: Optional[int] = None
    worktree_path: Optional[str] = None
    error: Optional[str] = None


class ChecklistRequest(BaseModel):
    project_id: int
    spec_path: str = Field(..., description="Path to spec file")
    spec_run_id: Optional[int] = Field(None, description="Optional SpecRun id")


class ChecklistResponse(BaseModel):
    success: bool
    checklist_path: Optional[str] = None
    item_count: int = 0
    spec_run_id: Optional[int] = None
    worktree_path: Optional[str] = None
    error: Optional[str] = None


class AnalyzeRequest(BaseModel):
    project_id: int
    spec_path: str = Field(..., description="Path to spec file")
    plan_path: Optional[str] = None
    tasks_path: Optional[str] = None
    spec_run_id: Optional[int] = Field(None, description="Optional SpecRun id")


class AnalyzeResponse(BaseModel):
    success: bool
    report_path: Optional[str] = None
    spec_run_id: Optional[int] = None
    worktree_path: Optional[str] = None
    error: Optional[str] = None


class ImplementRequest(BaseModel):
    project_id: int
    spec_path: str = Field(..., description="Path to spec file")
    spec_run_id: Optional[int] = Field(None, description="Optional SpecRun id")


class ImplementResponse(BaseModel):
    success: bool
    run_path: Optional[str] = None
    metadata_path: Optional[str] = None
    spec_run_id: Optional[int] = None
    worktree_path: Optional[str] = None
    error: Optional[str] = None


class SpecRunCleanupRequest(BaseModel):
    delete_remote_branch: bool = False


class SpecRunCleanupResponse(BaseModel):
    success: bool
    spec_run_id: Optional[int] = None
    worktree_path: Optional[str] = None
    deleted_remote_branch: bool = False
    error: Optional[str] = None


class ConstitutionRequest(BaseModel):
    content: str = Field(..., min_length=10)


class SpecListItem(BaseModel):
    id: Optional[int] = None
    name: str
    path: str
    spec_path: Optional[str] = None
    plan_path: Optional[str] = None
    tasks_path: Optional[str] = None
    checklist_path: Optional[str] = None
    analysis_path: Optional[str] = None
    implement_path: Optional[str] = None
    has_spec: bool
    has_plan: bool
    has_tasks: bool
    status: Optional[str] = None
    spec_run_id: Optional[int] = None
    worktree_path: Optional[str] = None
    branch_name: Optional[str] = None
    base_branch: Optional[str] = None
    spec_number: Optional[int] = None
    feature_name: Optional[str] = None


def get_specification_service(
    ctx: ServiceContext = Depends(get_service_context),
    db: Database = Depends(get_db),
) -> SpecificationService:
    return SpecificationService(ctx, db)


@router.post("/init", response_model=SpecKitResponse)
def init_speckit(
    request: InitRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Initialize SpecKit for a project."""
    project = db.get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local path")

    constitution_content = request.constitution_content
    if constitution_content is None:
        policy_service = PolicyService(ctx, db)
        effective = policy_service.resolve_effective_policy(
            request.project_id,
            repo_root=Path(project.local_path).expanduser(),
            include_repo_local=True,
        )
        constitution_content = policy_service.render_constitution(effective)

    result = service.init_project(
        project.local_path,
        constitution_content=constitution_content,
        project_id=request.project_id,
    )

    return SpecKitResponse(
        success=result.success,
        path=result.spec_path,
        constitution_hash=result.constitution_hash,
        error=result.error,
        warnings=result.warnings,
    )


@router.get("/constitution/{project_id}")
def get_constitution(
    project_id: int,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Get project constitution."""
    project = db.get_project(project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    content = service.get_constitution(project.local_path)
    if content is None:
        raise HTTPException(status_code=404, detail="Constitution not found. Run init first.")

    return {"content": content}


@router.put("/constitution/{project_id}", response_model=SpecKitResponse)
def save_constitution(
    project_id: int,
    request: ConstitutionRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Save project constitution."""
    project = db.get_project(project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    result = service.save_constitution(
        project.local_path,
        request.content,
        project_id=project_id,
    )
    policy_service = PolicyService(ctx, db)
    override, meta = policy_service.policy_override_from_constitution(request.content)
    updates: dict[str, Any] = {}
    if isinstance(meta.get("key"), str):
        updates["policy_pack_key"] = meta["key"]
    if isinstance(meta.get("version"), str):
        updates["policy_pack_version"] = meta["version"]
    if override is not None:
        updates["policy_overrides"] = override
    if updates:
        db.update_project_policy(project_id, **updates)

    return SpecKitResponse(
        success=result.success,
        path=result.spec_path,
        constitution_hash=result.constitution_hash,
        error=result.error,
        warnings=result.warnings,
    )


@router.post("/specify", response_model=SpecifyResponse)
def run_specify(
    request: SpecifyRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Generate a feature specification."""
    project = db.get_project(request.project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    result = service.run_specify(
        project.local_path,
        request.description,
        feature_name=request.feature_name,
        base_branch=request.base_branch,
        project_id=request.project_id,
    )

    return SpecifyResponse(
        success=result.success,
        spec_path=result.spec_path,
        spec_number=result.spec_number,
        feature_name=result.feature_name,
        spec_run_id=result.spec_run_id,
        worktree_path=result.worktree_path,
        branch_name=result.branch_name,
        base_branch=result.base_branch,
        spec_root=result.spec_root,
        error=result.error,
    )


@router.post("/plan", response_model=PlanResponse)
def run_plan(
    request: PlanRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Generate an implementation plan from a spec."""
    project = db.get_project(request.project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    result = service.run_plan(
        project.local_path,
        request.spec_path,
        spec_run_id=request.spec_run_id,
        project_id=request.project_id,
    )

    return PlanResponse(
        success=result.success,
        plan_path=result.plan_path,
        data_model_path=result.data_model_path,
        contracts_path=result.contracts_path,
        spec_run_id=result.spec_run_id,
        worktree_path=result.worktree_path,
        error=result.error,
    )


@router.post("/tasks", response_model=TasksResponse)
def run_tasks(
    request: TasksRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Generate a task list from a plan."""
    project = db.get_project(request.project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    result = service.run_tasks(
        project.local_path,
        request.plan_path,
        spec_run_id=request.spec_run_id,
        project_id=request.project_id,
    )

    return TasksResponse(
        success=result.success,
        tasks_path=result.tasks_path,
        task_count=result.task_count,
        parallelizable_count=result.parallelizable_count,
        spec_run_id=result.spec_run_id,
        worktree_path=result.worktree_path,
        error=result.error,
    )


@router.post("/clarify", response_model=ClarifyResponse)
def run_clarify(
    request: ClarifyRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Append clarifications to an existing specification."""
    project = db.get_project(request.project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    result = service.run_clarify(
        project.local_path,
        request.spec_path,
        entries=[entry.dict() for entry in request.entries],
        notes=request.notes,
        spec_run_id=request.spec_run_id,
        project_id=request.project_id,
    )

    return ClarifyResponse(
        success=result.success,
        spec_path=result.spec_path,
        clarifications_added=result.clarifications_added,
        spec_run_id=result.spec_run_id,
        worktree_path=result.worktree_path,
        error=result.error,
    )


@router.post("/checklist", response_model=ChecklistResponse)
def run_checklist(
    request: ChecklistRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Generate a checklist for a spec."""
    project = db.get_project(request.project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    result = service.run_checklist(
        project.local_path,
        request.spec_path,
        spec_run_id=request.spec_run_id,
        project_id=request.project_id,
    )

    return ChecklistResponse(
        success=result.success,
        checklist_path=result.checklist_path,
        item_count=result.item_count,
        spec_run_id=result.spec_run_id,
        worktree_path=result.worktree_path,
        error=result.error,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def run_analyze(
    request: AnalyzeRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Generate a placeholder analysis report for a spec."""
    project = db.get_project(request.project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    result = service.run_analyze(
        project.local_path,
        request.spec_path,
        plan_path=request.plan_path,
        tasks_path=request.tasks_path,
        spec_run_id=request.spec_run_id,
        project_id=request.project_id,
    )

    return AnalyzeResponse(
        success=result.success,
        report_path=result.report_path,
        spec_run_id=result.spec_run_id,
        worktree_path=result.worktree_path,
        error=result.error,
    )


@router.post("/implement", response_model=ImplementResponse)
def run_implement(
    request: ImplementRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Initialize an implementation run directory."""
    project = db.get_project(request.project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    result = service.run_implement(
        project.local_path,
        request.spec_path,
        spec_run_id=request.spec_run_id,
        project_id=request.project_id,
    )

    return ImplementResponse(
        success=result.success,
        run_path=result.run_path,
        metadata_path=result.metadata_path,
        spec_run_id=result.spec_run_id,
        worktree_path=result.worktree_path,
        error=result.error,
    )


@router.get("/specs/{project_id}", response_model=List[SpecListItem])
def list_specs(
    project_id: int,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """List all specs in a project."""
    project = db.get_project(project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    specs = service.list_specs(project.local_path, project_id=project_id)
    return [SpecListItem(**spec) for spec in specs]


@router.get("/status/{project_id}")
def get_speckit_status(
    project_id: int,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Get SpecKit status for a project."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.local_path:
        return {
            "initialized": False,
            "constitution_hash": None,
            "constitution_version": None,
            "spec_count": 0,
        }

    from pathlib import Path
    specify_path = Path(project.local_path) / ".specify"
    initialized = specify_path.exists()

    specs = service.list_specs(project.local_path, project_id=project_id) if initialized else []

    return {
        "initialized": initialized,
        "constitution_hash": project.constitution_hash,
        "constitution_version": project.constitution_version,
        "spec_count": len(specs),
        "specs": specs,
    }


@router.post("/spec-runs/{spec_run_id}/cleanup", response_model=SpecRunCleanupResponse)
def cleanup_spec_run(
    spec_run_id: int,
    request: SpecRunCleanupRequest = SpecRunCleanupRequest(),
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Cleanup a SpecRun worktree and artifacts."""
    try:
        db.get_spec_run(spec_run_id)
    except Exception:
        raise HTTPException(status_code=404, detail="SpecRun not found")

    result = service.cleanup_spec_run(
        spec_run_id=spec_run_id,
        delete_remote_branch=bool(request.delete_remote_branch),
    )
    return SpecRunCleanupResponse(
        success=result.success,
        spec_run_id=result.spec_run_id,
        worktree_path=result.worktree_path,
        deleted_remote_branch=result.deleted_remote_branch,
        error=result.error,
    )


# =============================================================================
# Workflow Orchestration
# =============================================================================

class WorkflowRequest(BaseModel):
    """Request for full spec→plan→tasks workflow."""
    project_id: int
    description: str = Field(..., min_length=10, description="Feature description")
    feature_name: Optional[str] = Field(None, description="Optional feature name")
    base_branch: Optional[str] = Field(None, description="Optional base branch for the spec run")
    stop_after: Optional[str] = Field(
        None,
        description="Stop workflow after step: 'spec', 'plan', or run full pipeline (None)"
    )
    skip_existing: bool = Field(
        False,
        description="Skip steps if artifacts already exist"
    )


class WorkflowStepResult(BaseModel):
    """Result of a single workflow step."""
    step: str
    success: bool
    path: Optional[str] = None
    error: Optional[str] = None
    skipped: bool = False


class WorkflowResponse(BaseModel):
    """Response from workflow orchestration."""
    success: bool
    spec_path: Optional[str] = None
    plan_path: Optional[str] = None
    tasks_path: Optional[str] = None
    task_count: int = 0
    parallelizable_count: int = 0
    spec_run_id: Optional[int] = None
    worktree_path: Optional[str] = None
    steps: List[WorkflowStepResult] = Field(default_factory=list)
    stopped_after: Optional[str] = None
    error: Optional[str] = None


@router.post("/workflow", response_model=WorkflowResponse)
def run_workflow(
    request: WorkflowRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """
    Run the full SpecKit workflow: spec → plan → tasks.
    
    This endpoint orchestrates the full specification pipeline:
    1. Generate feature specification from description
    2. Generate implementation plan from spec
    3. Generate task list from plan
    
    Use `stop_after` to run partial pipelines:
    - "spec": Only generate the specification
    - "plan": Generate spec and plan
    - None: Run the full pipeline (default)
    """
    project = db.get_project(request.project_id)
    if not project or not project.local_path:
        raise HTTPException(status_code=404, detail="Project not found")

    steps: List[WorkflowStepResult] = []
    spec_path = None
    plan_path = None
    tasks_path = None
    task_count = 0
    parallelizable_count = 0
    spec_run_id = None
    worktree_path = None

    # Step 1: Generate Specification
    try:
        spec_result = service.run_specify(
            project.local_path,
            request.description,
            feature_name=request.feature_name,
            base_branch=request.base_branch,
            project_id=request.project_id,
        )
        
        if not spec_result.success:
            steps.append(WorkflowStepResult(
                step="spec",
                success=False,
                error=spec_result.error,
            ))
            return WorkflowResponse(
                success=False,
                steps=steps,
                error=f"Specification generation failed: {spec_result.error}",
            )
        
        spec_path = spec_result.spec_path
        spec_run_id = spec_result.spec_run_id
        worktree_path = spec_result.worktree_path
        steps.append(WorkflowStepResult(
            step="spec",
            success=True,
            path=spec_path,
        ))
        
        if request.stop_after == "spec":
            return WorkflowResponse(
                success=True,
                spec_path=spec_path,
                spec_run_id=spec_run_id,
                worktree_path=worktree_path,
                steps=steps,
                stopped_after="spec",
            )
    except Exception as e:
        steps.append(WorkflowStepResult(
            step="spec",
            success=False,
            error=str(e),
        ))
        return WorkflowResponse(
            success=False,
            steps=steps,
            error=f"Specification generation error: {str(e)}",
        )

    # Step 2: Generate Plan
    try:
        plan_result = service.run_plan(
            project.local_path,
            spec_path,
            spec_run_id=spec_run_id,
            project_id=request.project_id,
        )
        
        if not plan_result.success:
            steps.append(WorkflowStepResult(
                step="plan",
                success=False,
                error=plan_result.error,
            ))
            return WorkflowResponse(
                success=False,
                spec_path=spec_path,
                steps=steps,
                error=f"Plan generation failed: {plan_result.error}",
            )
        
        plan_path = plan_result.plan_path
        steps.append(WorkflowStepResult(
            step="plan",
            success=True,
            path=plan_path,
        ))
        
        if request.stop_after == "plan":
            return WorkflowResponse(
                success=True,
                spec_path=spec_path,
                plan_path=plan_path,
                spec_run_id=spec_run_id,
                worktree_path=worktree_path,
                steps=steps,
                stopped_after="plan",
            )
    except Exception as e:
        steps.append(WorkflowStepResult(
            step="plan",
            success=False,
            error=str(e),
        ))
        return WorkflowResponse(
            success=False,
            spec_path=spec_path,
            steps=steps,
            error=f"Plan generation error: {str(e)}",
        )

    # Step 3: Generate Tasks
    try:
        tasks_result = service.run_tasks(
            project.local_path,
            plan_path,
            spec_run_id=spec_run_id,
            project_id=request.project_id,
        )
        
        if not tasks_result.success:
            steps.append(WorkflowStepResult(
                step="tasks",
                success=False,
                error=tasks_result.error,
            ))
            return WorkflowResponse(
                success=False,
                spec_path=spec_path,
                plan_path=plan_path,
                steps=steps,
                error=f"Tasks generation failed: {tasks_result.error}",
            )
        
        tasks_path = tasks_result.tasks_path
        task_count = tasks_result.task_count
        parallelizable_count = tasks_result.parallelizable_count
        
        steps.append(WorkflowStepResult(
            step="tasks",
            success=True,
            path=tasks_path,
        ))
    except Exception as e:
        steps.append(WorkflowStepResult(
            step="tasks",
            success=False,
            error=str(e),
        ))
        return WorkflowResponse(
            success=False,
            spec_path=spec_path,
            plan_path=plan_path,
            steps=steps,
            error=f"Tasks generation error: {str(e)}",
        )

    return WorkflowResponse(
        success=True,
        spec_path=spec_path,
        plan_path=plan_path,
        tasks_path=tasks_path,
        task_count=task_count,
        parallelizable_count=parallelizable_count,
        spec_run_id=spec_run_id,
        worktree_path=worktree_path,
        steps=steps,
    )
