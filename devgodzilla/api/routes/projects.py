from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from devgodzilla.api import schemas
from devgodzilla.api.dependencies import get_db, get_service_context
from devgodzilla.db.database import Database, _UNSET
from devgodzilla.services.base import ServiceContext

router = APIRouter()


class ProjectOnboardRequest(BaseModel):
    branch: Optional[str] = Field(default=None, description="Branch to checkout after clone (defaults to project.base_branch)")
    clone_if_missing: bool = Field(default=True, description="Clone repo if local_path is missing")
    constitution_content: Optional[str] = Field(default=None, description="Optional custom constitution content")
    run_discovery_agent: bool = Field(default=False, description="Run headless agent discovery (writes tasksgodzilla/*)")
    discovery_pipeline: bool = Field(default=True, description="Use multi-stage discovery pipeline")
    discovery_engine_id: Optional[str] = Field(default=None, description="Engine ID for discovery (default: opencode)")
    discovery_model: Optional[str] = Field(default=None, description="Model for discovery (default: engine default)")


class ProjectOnboardResponse(BaseModel):
    success: bool
    project: schemas.ProjectOut
    local_path: str
    speckit_initialized: bool
    speckit_path: Optional[str] = None
    constitution_hash: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    discovery_success: bool = False
    discovery_log_path: Optional[str] = None
    discovery_missing_outputs: List[str] = Field(default_factory=list)
    discovery_error: Optional[str] = None
    error: Optional[str] = None


@router.post("/projects", response_model=schemas.ProjectOut)
def create_project(
    project: schemas.ProjectCreate,
    db: Database = Depends(get_db)
):
    """Create a new project."""
    return db.create_project(
        name=project.name,
        git_url=project.git_url or "",
        base_branch=project.base_branch,
        local_path=project.local_path
    )

@router.get("/projects", response_model=List[schemas.ProjectOut])
def list_projects(
    status: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """List all projects, optionally filtered by status."""
    projects = db.list_projects()
    if status:
        projects = [p for p in projects if p.status == status]
    return projects

@router.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: int,
    db: Database = Depends(get_db)
):
    """Get project by ID."""
    try:
        return db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

@router.put("/projects/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: int,
    project: schemas.ProjectUpdate,
    db: Database = Depends(get_db)
):
    """Update a project."""
    try:
        return db.update_project(
            project_id,
            name=project.name,
            description=project.description if project.description is not None else _UNSET,
            status=project.status.value if project.status else None,
            git_url=project.git_url,
            base_branch=project.base_branch,
            local_path=project.local_path,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

@router.post("/projects/{project_id}/archive", response_model=schemas.ProjectOut)
def archive_project(
    project_id: int,
    db: Database = Depends(get_db)
):
    """Archive a project."""
    try:
        return db.update_project(project_id, status="archived")
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

@router.post("/projects/{project_id}/unarchive", response_model=schemas.ProjectOut)
def unarchive_project(
    project_id: int,
    db: Database = Depends(get_db)
):
    """Unarchive a project."""
    try:
        return db.update_project(project_id, status="active")
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Database = Depends(get_db)
):
    """Delete a project and all associated data."""
    try:
        db.get_project(project_id)  # Check exists first
        db.delete_project(project_id)
        return {"status": "deleted", "project_id": project_id}
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/projects/{project_id}/actions/onboard", response_model=ProjectOnboardResponse)
def onboard_project(
    project_id: int,
    request: ProjectOnboardRequest,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """
    Onboard a project repository for DevGodzilla workflows.

    - Ensures the repo exists locally (clone if missing)
    - Checks out the requested branch (or project.base_branch)
    - Initializes `.specify/` via SpecificationService
    """
    try:
        project = db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.git_url:
        raise HTTPException(status_code=400, detail="Project has no git_url")

    from devgodzilla.services.git import GitService, run_process
    from devgodzilla.services.specification import SpecificationService

    git = GitService(ctx)
    try:
        repo_path = git.resolve_repo_path(
            project.git_url,
            project.name,
            project.local_path,
            project_id=project.id,
            clone_if_missing=bool(request.clone_if_missing),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Clone failed: {exc}")

    branch = (request.branch or project.base_branch or "main").strip()
    if branch:
        try:
            run_process(["git", "fetch", "--prune", "origin", branch], cwd=repo_path, check=False)
            # Prefer tracking branch when available.
            res = run_process(["git", "checkout", branch], cwd=repo_path, check=False)
            if res.returncode != 0:
                run_process(["git", "checkout", "-B", branch, f"origin/{branch}"], cwd=repo_path, check=False)
        except Exception:
            # Best-effort: branch checkout isn't strictly required for SpecKit init.
            pass

    # Persist local_path (ensure DevGodzilla API can later find the repo).
    if not project.local_path or project.local_path != str(repo_path):
        try:
            db.update_project(project_id, local_path=str(repo_path))
        except Exception:
            pass

    spec_service = SpecificationService(ctx, db)
    init_result = spec_service.init_project(
        str(repo_path),
        constitution_content=request.constitution_content,
        project_id=project_id,
    )

    discovery_success = False
    discovery_log_path: Optional[str] = None
    discovery_missing_outputs: List[str] = []
    discovery_error: Optional[str] = None
    if request.run_discovery_agent:
        try:
            from devgodzilla.services.discovery_agent import DiscoveryAgentService

            svc = DiscoveryAgentService(ctx)
            disc = svc.run_discovery(
                repo_root=repo_path,
                engine_id=request.discovery_engine_id or "opencode",
                model=request.discovery_model,
                pipeline=bool(request.discovery_pipeline),
                stages=None,
                timeout_seconds=int(os.environ.get("DEVGODZILLA_DISCOVERY_TIMEOUT_SECONDS", "900")),
                strict_outputs=True,
            )
            discovery_success = bool(disc.success)
            discovery_log_path = str(disc.log_path)
            discovery_missing_outputs = [str(p) for p in disc.missing_outputs]
            discovery_error = disc.error
        except Exception as e:
            discovery_success = False
            discovery_error = str(e)
    updated_project = db.get_project(project_id)

    return ProjectOnboardResponse(
        success=init_result.success,
        project=schemas.ProjectOut.model_validate(updated_project),
        local_path=str(repo_path),
        speckit_initialized=init_result.success,
        speckit_path=init_result.spec_path,
        constitution_hash=init_result.constitution_hash,
        warnings=init_result.warnings,
        discovery_success=discovery_success,
        discovery_log_path=discovery_log_path,
        discovery_missing_outputs=discovery_missing_outputs,
        discovery_error=discovery_error,
        error=init_result.error,
    )

@router.get("/projects/{project_id}/sprints", response_model=List[schemas.SprintOut])
def list_project_sprints(
    project_id: int,
    status: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """List sprints for a specific project."""
    return db.list_sprints(project_id=project_id, status=status)

@router.get("/projects/{project_id}/tasks", response_model=List[schemas.AgileTaskOut])
def list_project_tasks(
    project_id: int,
    sprint_id: Optional[int] = None,
    board_status: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 100,
    db: Database = Depends(get_db)
):
    """List tasks for a specific project."""
    return db.list_tasks(
        project_id=project_id,
        sprint_id=sprint_id,
        board_status=board_status,
        assignee=assignee,
        limit=limit
    )
