from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from devgodzilla.api.dependencies import get_db, get_service_context
from devgodzilla.db.database import Database
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.specification import SpecificationService

router = APIRouter(tags=["SpecKit"])


class SpecKitResponse(BaseModel):
    success: bool
    path: Optional[str] = None
    constitution_hash: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class ConstitutionRequest(BaseModel):
    content: str = Field(..., min_length=10)


class SpecifyRequest(BaseModel):
    description: str = Field(..., min_length=10)
    feature_name: Optional[str] = None


class SpecifyResponse(BaseModel):
    success: bool
    spec_path: Optional[str] = None
    spec_number: Optional[int] = None
    feature_name: Optional[str] = None
    error: Optional[str] = None


class PlanRequest(BaseModel):
    spec_path: str


class PlanResponse(BaseModel):
    success: bool
    plan_path: Optional[str] = None
    data_model_path: Optional[str] = None
    contracts_path: Optional[str] = None
    error: Optional[str] = None


class TasksRequest(BaseModel):
    plan_path: str


class TasksResponse(BaseModel):
    success: bool
    tasks_path: Optional[str] = None
    task_count: int = 0
    parallelizable_count: int = 0
    error: Optional[str] = None


def _service(
    ctx: ServiceContext = Depends(get_service_context),
    db: Database = Depends(get_db),
) -> SpecificationService:
    return SpecificationService(ctx, db)


@router.post("/projects/{project_id}/speckit/init", response_model=SpecKitResponse)
def init_project_speckit(
    project_id: int,
    request: Optional[ConstitutionRequest] = None,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(_service),
):
    project = db.get_project(project_id)
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local path")
    result = service.init_project(
        project.local_path,
        constitution_content=request.content if request else None,
        project_id=project_id,
    )
    return SpecKitResponse(
        success=result.success,
        path=result.spec_path,
        constitution_hash=result.constitution_hash,
        error=result.error,
        warnings=result.warnings,
    )


@router.get("/projects/{project_id}/speckit/constitution")
def get_project_constitution(
    project_id: int,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(_service),
):
    project = db.get_project(project_id)
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local path")
    content = service.get_constitution(project.local_path)
    if content is None:
        raise HTTPException(status_code=404, detail="Constitution not found")
    return {"content": content}


@router.put("/projects/{project_id}/speckit/constitution", response_model=SpecKitResponse)
def put_project_constitution(
    project_id: int,
    request: ConstitutionRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(_service),
):
    project = db.get_project(project_id)
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local path")
    result = service.save_constitution(project.local_path, request.content, project_id=project_id)
    return SpecKitResponse(
        success=result.success,
        path=result.spec_path,
        constitution_hash=result.constitution_hash,
        error=result.error,
    )


@router.post("/projects/{project_id}/speckit/specify", response_model=SpecifyResponse)
def project_speckit_specify(
    project_id: int,
    request: SpecifyRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(_service),
):
    project = db.get_project(project_id)
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local path")
    result = service.run_specify(project.local_path, request.description, feature_name=request.feature_name, project_id=project_id)
    return SpecifyResponse(
        success=result.success,
        spec_path=result.spec_path,
        spec_number=result.spec_number,
        feature_name=result.feature_name,
        error=result.error,
    )


@router.post("/projects/{project_id}/speckit/plan", response_model=PlanResponse)
def project_speckit_plan(
    project_id: int,
    request: PlanRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(_service),
):
    project = db.get_project(project_id)
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local path")
    result = service.run_plan(project.local_path, request.spec_path, project_id=project_id)
    return PlanResponse(
        success=result.success,
        plan_path=result.plan_path,
        data_model_path=result.data_model_path,
        contracts_path=result.contracts_path,
        error=result.error,
    )


@router.post("/projects/{project_id}/speckit/tasks", response_model=TasksResponse)
def project_speckit_tasks(
    project_id: int,
    request: TasksRequest,
    db: Database = Depends(get_db),
    service: SpecificationService = Depends(_service),
):
    project = db.get_project(project_id)
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local path")
    result = service.run_tasks(project.local_path, request.plan_path, project_id=project_id)
    return TasksResponse(
        success=result.success,
        tasks_path=result.tasks_path,
        task_count=result.task_count,
        parallelizable_count=result.parallelizable_count,
        error=result.error,
    )

