from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from devgodzilla.api import schemas
from devgodzilla.api.dependencies import get_db, get_service_context
from devgodzilla.db.database import Database
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.task_cycle import TaskCycleError, TaskCycleService

router = APIRouter()


class WorkItemQARequest(BaseModel):
    gates: Optional[List[str]] = None


def _task_cycle_service(
    ctx: ServiceContext = Depends(get_service_context),
    db: Database = Depends(get_db),
) -> TaskCycleService:
    return TaskCycleService(ctx, db)


@router.get("/projects/{project_id}/task-cycle", response_model=List[schemas.WorkItemOut])
def list_task_cycle_work_items(
    project_id: int,
    protocol_run_id: Optional[int] = Query(default=None),
    lifecycle: str = Query(default="active"),
    db: Database = Depends(get_db),
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return service.list_work_items(project_id, protocol_run_id=protocol_run_id, lifecycle=lifecycle)
    except TaskCycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/projects/{project_id}/brownfield/run", response_model=schemas.BrownfieldRunOut)
def start_brownfield_run(
    project_id: int,
    request: schemas.BrownfieldRunRequest,
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        return service.start_brownfield_run(project_id, request)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    except TaskCycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/work-items/{work_item_id}", response_model=schemas.WorkItemOut)
def get_work_item(
    work_item_id: int,
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        return service.get_work_item(work_item_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Work item not found")


@router.get("/work-items/{work_item_id}/artifacts/{artifact_key}/content", response_model=schemas.ArtifactContentOut)
def get_work_item_artifact_content(
    work_item_id: int,
    artifact_key: str,
    max_bytes: int = Query(default=200_000, ge=1, le=2_000_000),
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        return service.read_artifact_content(work_item_id, artifact_key, max_bytes=max_bytes)
    except KeyError:
        raise HTTPException(status_code=404, detail="Work item not found")
    except TaskCycleError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status, detail=detail)


@router.post("/work-items/{work_item_id}/build-context", response_model=schemas.WorkItemOut)
def build_context(
    work_item_id: int,
    request: schemas.BuildContextRequest,
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        return service.build_context(work_item_id, refresh=request.refresh)
    except KeyError:
        raise HTTPException(status_code=404, detail="Work item not found")
    except TaskCycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/work-items/{work_item_id}/actions/implement", response_model=schemas.WorkItemOut)
def implement_work_item(
    work_item_id: int,
    request: schemas.WorkItemImplementRequest,
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        return service.implement(work_item_id, owner_agent=request.owner_agent)
    except KeyError:
        raise HTTPException(status_code=404, detail="Work item not found")
    except TaskCycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/work-items/{work_item_id}/actions/review", response_model=schemas.WorkItemReviewOut)
def review_work_item(
    work_item_id: int,
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        _, review = service.review(work_item_id)
        return review
    except KeyError:
        raise HTTPException(status_code=404, detail="Work item not found")
    except TaskCycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/work-items/{work_item_id}/actions/qa", response_model=schemas.WorkItemQAOut)
def qa_work_item(
    work_item_id: int,
    request: WorkItemQARequest,
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        return service.qa(work_item_id, gates=request.gates)
    except KeyError:
        raise HTTPException(status_code=404, detail="Work item not found")
    except TaskCycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/work-items/{work_item_id}/actions/mark-pr-ready", response_model=schemas.WorkItemOut)
def mark_pr_ready(
    work_item_id: int,
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        return service.mark_pr_ready(work_item_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Work item not found")
    except TaskCycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/work-items/{work_item_id}/actions/archive", response_model=schemas.WorkItemOut)
def archive_work_item(
    work_item_id: int,
    request: schemas.WorkItemLifecycleRequest,
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        return service.archive_work_item(work_item_id, reason=request.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="Work item not found")
    except TaskCycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/work-items/{work_item_id}/actions/cancel", response_model=schemas.WorkItemOut)
def cancel_work_item(
    work_item_id: int,
    request: schemas.WorkItemLifecycleRequest,
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        return service.cancel_work_item(work_item_id, reason=request.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="Work item not found")
    except TaskCycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/work-items/{work_item_id}/actions/reassign-owner", response_model=schemas.WorkItemOut)
def reassign_work_item_owner(
    work_item_id: int,
    request: schemas.WorkItemReassignRequest,
    service: TaskCycleService = Depends(_task_cycle_service),
):
    try:
        return service.reassign_owner(work_item_id, request.owner_agent)
    except KeyError:
        raise HTTPException(status_code=404, detail="Work item not found")
    except TaskCycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
