from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from devgodzilla.api import schemas
from devgodzilla.api.dependencies import get_db
from devgodzilla.db.database import Database

router = APIRouter()

@router.get("/clarifications", response_model=List[schemas.ClarificationOut])
def list_clarifications(
    project_id: Optional[int] = None,
    protocol_run_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Database = Depends(get_db)
):
    """List clarifications."""
    return db.list_clarifications(
        project_id=project_id,
        protocol_run_id=protocol_run_id,
        status=status,
        limit=limit
    )

@router.post("/clarifications/{clarification_id}/answer", response_model=schemas.ClarificationOut)
def answer_clarification(
    clarification_id: int,
    answer: schemas.ClarificationAnswer,
    db: Database = Depends(get_db)
):
    """Answer a clarification."""
    try:
        clarification = db.get_clarification_by_id(clarification_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Clarification not found")

    # Store answer as structured JSON (so UI can render rich answers later)
    payload = {"text": answer.answer}

    try:
        updated = db.answer_clarification(
            scope=clarification.scope,
            key=clarification.key,
            answer=payload,
            answered_by=answer.answered_by,
            status="answered",
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Clarification not found")

    return updated
