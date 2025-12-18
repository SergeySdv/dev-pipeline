from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from devgodzilla.api import schemas
from devgodzilla.api.dependencies import get_db
from devgodzilla.db.database import Database

router = APIRouter(tags=["Runs"])


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


@router.get("/runs", response_model=List[schemas.JobRunOut])
def list_runs(
    project_id: Optional[int] = None,
    protocol_run_id: Optional[int] = None,
    step_run_id: Optional[int] = None,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 200,
    db: Database = Depends(get_db),
):
    runs = db.list_job_runs(
        limit=limit,
        project_id=project_id,
        protocol_run_id=protocol_run_id,
        step_run_id=step_run_id,
        status=status,
        job_type=job_type,
    )
    return [schemas.JobRunOut.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=schemas.JobRunOut)
def get_run(
    run_id: str,
    db: Database = Depends(get_db),
):
    try:
        run = db.get_job_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    return schemas.JobRunOut.model_validate(run)


@router.get("/runs/{run_id}/logs", response_model=schemas.ArtifactContentOut)
def get_run_logs(
    run_id: str,
    max_bytes: int = 200_000,
    db: Database = Depends(get_db),
):
    try:
        run = db.get_job_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")

    if not run.log_path:
        return schemas.ArtifactContentOut(
            id="logs",
            name="logs",
            type="log",
            content="",
            truncated=False,
        )

    path = Path(run.log_path).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Run logs not found")

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
        id="logs",
        name=path.name,
        type="log",
        content=content,
        truncated=truncated,
    )


@router.get("/runs/{run_id}/artifacts", response_model=List[schemas.RunArtifactOut])
def list_run_artifacts(
    run_id: str,
    db: Database = Depends(get_db),
):
    try:
        db.get_job_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")

    artifacts = db.list_run_artifacts(run_id)
    items: list[schemas.RunArtifactOut] = []
    for a in artifacts:
        size = 0
        try:
            p = Path(a.path).expanduser()
            size = p.stat().st_size if p.exists() else (a.bytes or 0)
        except Exception:
            size = a.bytes or 0

        items.append(
            schemas.RunArtifactOut(
                run_id=a.run_id,
                id=a.name,
                type=_artifact_type_from_name(a.name),
                name=a.name,
                size=int(size),
                created_at=None,
            )
        )
    return items


@router.get("/runs/{run_id}/artifacts/{artifact_id}/content", response_model=schemas.ArtifactContentOut)
def get_run_artifact_content(
    run_id: str,
    artifact_id: str,
    max_bytes: int = 200_000,
    db: Database = Depends(get_db),
):
    try:
        artifact = db.get_run_artifact(run_id, artifact_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Artifact not found")

    path = Path(artifact.path).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")

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
        id=artifact_id,
        name=artifact_id,
        type=_artifact_type_from_name(artifact_id),
        content=content,
        truncated=truncated,
    )

