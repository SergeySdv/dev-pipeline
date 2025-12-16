from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from devgodzilla.api import schemas
from devgodzilla.api.dependencies import get_db
from devgodzilla.db.database import Database, _UNSET

router = APIRouter()

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

