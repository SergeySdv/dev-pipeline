from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from devgodzilla.api import schemas
from devgodzilla.api.dependencies import get_db, get_service_context
from devgodzilla.services.base import ServiceContext
from devgodzilla.db.database import Database
from devgodzilla.services.planning import PlanningService

router = APIRouter()


def _workspace_root(run, project) -> Path:
    if run.worktree_path:
        return Path(run.worktree_path).expanduser()
    if project.local_path:
        return Path(project.local_path).expanduser()
    return Path.cwd()


def _protocol_root(run, workspace_root: Path) -> Path:
    if run.protocol_root:
        return Path(run.protocol_root).expanduser()
    return workspace_root / ".specify" / "specs" / run.protocol_name


def _artifact_type_from_name(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".log") or "log" in lower:
        return "log"
    if lower.endswith(".diff") or lower.endswith(".patch"):
        return "diff"
    if lower.endswith(".md") and ("report" in lower or "qa" in lower):
        return "report"
    if lower.endswith(".json"):
        return "json"
    if lower.endswith(".txt") or lower.endswith(".md"):
        return "text"
    return "file"

@router.post("/protocols", response_model=schemas.ProtocolOut)
def create_protocol(
    protocol: schemas.ProtocolCreate,
    background_tasks: BackgroundTasks,
    ctx: ServiceContext = Depends(get_service_context),
    db: Database = Depends(get_db)
):
    """Create a new protocol run."""
    # Create the run record
    run = db.create_protocol_run(
        project_id=protocol.project_id,
        protocol_name=protocol.name,
        status="pending",
        base_branch=protocol.branch_name or "main",
        description=protocol.description,
    )
    
    # If using planning service, we should trigger plan_protocol in background
    # But for now, we just return the pending run. The CLI triggers planning explicitly.
    # We could add an option 'plan: bool = False' to trigger it.
    
    return run

@router.get("/protocols", response_model=List[schemas.ProtocolOut])
def list_protocols(
    project_id: Optional[int] = None,
    limit: int = 20,
    db: Database = Depends(get_db)
):
    """List protocol runs."""
    if project_id is None:
        # We need to support listing all, but our DB interface requires project_id
        # We might need to extend the DB interface or fetch for all projects (inefficient).
        # For now, require project_id
        raise HTTPException(status_code=400, detail="project_id is required")
        
    runs = db.list_protocol_runs(project_id=project_id)
    return runs[:limit]

@router.get("/protocols/{protocol_id}", response_model=schemas.ProtocolOut)
def get_protocol(
    protocol_id: int,
    db: Database = Depends(get_db)
):
    """Get a protocol run by ID."""
    try:
        return db.get_protocol_run(protocol_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Protocol {protocol_id} not found")

@router.post("/protocols/{protocol_id}/actions/start", response_model=schemas.ProtocolOut)
def start_protocol(
    protocol_id: int,
    background_tasks: BackgroundTasks,
    ctx: ServiceContext = Depends(get_service_context),
    db: Database = Depends(get_db)
):
    """Start planning/execution for a protocol."""
    try:
        run = db.get_protocol_run(protocol_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Protocol not found")
        
    if run.status not in ["pending", "planned"]:
        raise HTTPException(status_code=400, detail=f"Cannot start protocol in {run.status} state")
        
    # Update status to planning
    db.update_protocol_status(protocol_id, "planning")
    
    # Trigger planning service in background
    def run_planning():
        service = PlanningService(ctx, db)
        service.plan_protocol(protocol_id)
        
    background_tasks.add_task(run_planning)
    
    return db.get_protocol_run(protocol_id)


@router.post("/protocols/{protocol_id}/actions/pause", response_model=schemas.ProtocolOut)
def pause_protocol(
    protocol_id: int,
    db: Database = Depends(get_db),
):
    """Pause a running protocol."""
    try:
        run = db.get_protocol_run(protocol_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Protocol not found")

    if run.status != "running":
        raise HTTPException(status_code=400, detail=f"Cannot pause protocol in {run.status} state")

    db.update_protocol_status(protocol_id, "paused")
    return db.get_protocol_run(protocol_id)


@router.post("/protocols/{protocol_id}/actions/resume", response_model=schemas.ProtocolOut)
def resume_protocol(
    protocol_id: int,
    db: Database = Depends(get_db),
):
    """Resume a paused protocol."""
    try:
        run = db.get_protocol_run(protocol_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Protocol not found")

    if run.status != "paused":
        raise HTTPException(status_code=400, detail=f"Cannot resume protocol in {run.status} state")

    db.update_protocol_status(protocol_id, "running")
    return db.get_protocol_run(protocol_id)


@router.post("/protocols/{protocol_id}/actions/cancel", response_model=schemas.ProtocolOut)
def cancel_protocol(
    protocol_id: int,
    db: Database = Depends(get_db),
):
    """Cancel a protocol."""
    try:
        run = db.get_protocol_run(protocol_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Protocol not found")

    if run.status in ["completed", "cancelled"]:
        return run

    db.update_protocol_status(protocol_id, "cancelled")
    return db.get_protocol_run(protocol_id)


@router.get("/protocols/{protocol_id}/artifacts", response_model=List[schemas.ProtocolArtifactOut])
def list_protocol_artifacts(
    protocol_id: int,
    limit: int = 200,
    db: Database = Depends(get_db),
):
    """List artifacts across all steps for a protocol (aggregated)."""
    limit = max(1, min(int(limit), 500))
    try:
        run = db.get_protocol_run(protocol_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Protocol not found")

    project = db.get_project(run.project_id)
    root = _protocol_root(run, _workspace_root(run, project))

    items: List[schemas.ProtocolArtifactOut] = []
    for step in db.list_step_runs(protocol_id):
        artifacts_dir = root / ".devgodzilla" / "steps" / str(step.id) / "artifacts"
        if not artifacts_dir.exists():
            continue
        for p in artifacts_dir.iterdir():
            if not p.is_file():
                continue
            stat = p.stat()
            items.append(
                schemas.ProtocolArtifactOut(
                    id=f"{step.id}:{p.name}",
                    type=_artifact_type_from_name(p.name),
                    name=p.name,
                    size=stat.st_size,
                    created_at=None,
                    step_run_id=step.id,
                    step_name=step.step_name,
                )
            )

    # Sort by file mtime desc (best-effort)
    def _mtime(item: schemas.ProtocolArtifactOut) -> float:
        try:
            step_id_str, filename = item.id.split(":", 1)
            p = root / ".devgodzilla" / "steps" / step_id_str / "artifacts" / filename
            return p.stat().st_mtime
        except Exception:
            return 0.0

    items.sort(key=_mtime, reverse=True)
    return items[:limit]
