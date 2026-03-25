"""
Specifications API Routes

Endpoints for listing and managing feature specifications across projects.
Enhanced with comprehensive filtering support.
"""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query

from devgodzilla.api.dependencies import get_db, get_service_context, Database
from devgodzilla.api.routes._specification_queries import (
    build_filters_applied,
    list_specification_items,
    spec_key,
    specification_content_payload,
)
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.specification import SpecificationService

router = APIRouter(tags=["specifications"])


class SpecificationOut(BaseModel):
    id: int
    spec_run_id: Optional[int] = None
    path: str
    spec_path: Optional[str] = None
    plan_path: Optional[str] = None
    tasks_path: Optional[str] = None
    checklist_path: Optional[str] = None
    analysis_path: Optional[str] = None
    implement_path: Optional[str] = None
    title: str
    project_id: int
    project_name: str
    status: str
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    worktree_path: Optional[str] = None
    branch_name: Optional[str] = None
    base_branch: Optional[str] = None
    feature_name: Optional[str] = None
    spec_number: Optional[int] = None
    tasks_generated: bool = False
    protocol_id: Optional[int] = None
    sprint_id: Optional[int] = None
    sprint_name: Optional[str] = None
    linked_tasks: int = 0
    completed_tasks: int = 0
    story_points: int = 0
    has_plan: bool = False
    has_tasks: bool = False


class SpecificationFilterParams(BaseModel):
    """Filter parameters for specifications listing."""
    project_id: Optional[int] = None
    sprint_id: Optional[int] = None
    status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    has_plan: Optional[bool] = None
    has_tasks: Optional[bool] = None
    search: Optional[str] = None


class SpecificationLinkSprintRequest(BaseModel):
    sprint_id: Optional[int] = Field(None, description="Sprint ID to link, or None to unlink")


class SpecificationContentOut(BaseModel):
    id: int
    path: str
    title: str
    spec_content: Optional[str] = None
    plan_content: Optional[str] = None
    tasks_content: Optional[str] = None
    checklist_content: Optional[str] = None
    analysis_content: Optional[str] = None


class SpecificationsListOut(BaseModel):
    """Paginated list of specifications with filter metadata."""
    items: List[SpecificationOut]
    total: int
    filters_applied: Dict[str, Any]


def get_specification_service(
    ctx: ServiceContext = Depends(get_service_context),
    db: Database = Depends(get_db),
) -> SpecificationService:
    return SpecificationService(ctx, db)


@router.get("/specifications", response_model=SpecificationsListOut)
def list_specifications(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    sprint_id: Optional[int] = Query(None, description="Filter by sprint ID"),
    status: Optional[str] = Query(None, description="Filter by status: draft, in-progress, completed"),
    date_from: Optional[str] = Query(None, description="Filter by created date from (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter by created date to (ISO format)"),
    has_plan: Optional[bool] = Query(None, description="Filter by has implementation plan"),
    has_tasks: Optional[bool] = Query(None, description="Filter by has tasks generated"),
    search: Optional[str] = Query(None, description="Search in title and path"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """
    List all feature specifications across projects with comprehensive filtering.
    
    Filters:
    - project_id: Filter to a specific project
    - sprint_id: Filter specs linked to a specific sprint
    - status: draft | in-progress | completed
    - date_from/date_to: Date range filter (ISO format: YYYY-MM-DD)
    - has_plan: Filter by whether spec has implementation plan
    - has_tasks: Filter by whether spec has tasks generated
    - search: Full-text search in title and path
    """
    filters_applied = build_filters_applied(
        project_id=project_id,
        sprint_id=sprint_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        has_plan=has_plan,
        has_tasks=has_tasks,
        search=search,
    )
    all_specifications = list_specification_items(
        db=db,
        service=service,
        project_id=project_id,
        sprint_id=sprint_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        has_plan=has_plan,
        has_tasks=has_tasks,
        search=search,
    )
    total = len(all_specifications)
    paginated = [SpecificationOut(**item) for item in all_specifications[offset:offset + limit]]
    
    return SpecificationsListOut(
        items=paginated,
        total=total,
        filters_applied=filters_applied,
    )


def _get_specification_by_id(
    spec_id: int,
    db: Database,
    service: SpecificationService,
) -> SpecificationOut:
    result = list_specifications(
        project_id=None,
        sprint_id=None,
        status=None,
        date_from=None,
        date_to=None,
        has_plan=None,
        has_tasks=None,
        search=None,
        limit=500,
        offset=0,
        db=db,
        service=service,
    )
    for spec in result.items:
        if spec.id == spec_id:
            return spec
    raise HTTPException(status_code=404, detail=f"Specification {spec_id} not found")


@router.get("/specifications/{spec_id}", response_model=SpecificationOut)
def get_specification(
    spec_id: int,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Get a single specification by ID."""
    return _get_specification_by_id(spec_id=spec_id, db=db, service=service)


@router.get("/specifications/{spec_id}/content", response_model=SpecificationContentOut)
def get_specification_content(
    spec_id: int,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Get specification content including spec, plan, and tasks markdown."""
    spec = _get_specification_by_id(spec_id=spec_id, db=db, service=service)
    
    # Get project to find local path
    try:
        project = db.get_project(spec.project_id)
    except (KeyError, Exception):
        raise HTTPException(status_code=404, detail=f"Project {spec.project_id} not found")
    
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local path")
    content = specification_content_payload(project.local_path, spec.path)
    
    return SpecificationContentOut(
        id=spec_id,
        path=spec.path,
        title=spec.title,
        spec_content=content["spec_content"],
        plan_content=content["plan_content"],
        tasks_content=content["tasks_content"],
        checklist_content=content["checklist_content"],
        analysis_content=content["analysis_content"],
    )


@router.post("/specifications/{spec_id}/link-sprint")
def link_specification_to_sprint(
    spec_id: int,
    request: SpecificationLinkSprintRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(get_specification_service),
):
    """Link or unlink a specification to/from a sprint."""
    spec = _get_specification_by_id(spec_id=spec_id, db=db, service=service)
    
    # Verify sprint exists if linking
    if request.sprint_id is not None:
        try:
            sprint = db.get_sprint(request.sprint_id)
            # Verify sprint belongs to same project
            if sprint.project_id != spec.project_id:
                raise HTTPException(
                    status_code=400,
                    detail="Sprint must belong to the same project as the specification"
                )
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Sprint {request.sprint_id} not found")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to load sprint {request.sprint_id}: {exc}")
    
    spec_ref_key = spec_key(spec, spec.id)
    try:
        db.set_spec_sprint_link(spec.project_id, spec_ref_key, request.sprint_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist spec-sprint link: {exc}")

    return {
        "success": True,
        "persisted": True,
        "spec_id": spec_id,
        "sprint_id": request.sprint_id,
        "message": f"Specification {'linked to' if request.sprint_id else 'unlinked from'} sprint"
    }
