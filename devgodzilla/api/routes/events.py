"""
DevGodzilla Events Endpoint

DB-backed Server-Sent Events (SSE) endpoint for real-time updates.
"""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse

from devgodzilla.api import schemas
from devgodzilla.api.dependencies import get_db
from devgodzilla.db.database import Database
from devgodzilla.events_catalog import normalize_event_type

router = APIRouter(tags=["Events"])


def _event_to_sse(event: schemas.EventOut) -> str:
    payload = event.model_dump()
    return (
        f"id: {event.id}\n"
        f"event: {event.event_type}\n"
        f"data: {json.dumps(payload, default=str)}\n\n"
    )


# ==================== SSE Endpoint ====================

async def event_generator(
    db: Database,
    protocol_id: Optional[int] = None,
    project_id: Optional[int] = None,
    event_types: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    *,
    since_id: int = 0,
    poll_interval_seconds: float = 0.5,
) -> AsyncGenerator[str, None]:
    last_id = max(0, int(since_id))
    yield "event: connected\ndata: {}\n\n"

    category_set = {normalize_event_type(c) for c in categories or [] if c}
    idle_ticks = 0
    while True:
        batch = db.list_events_since_id(
            since_id=last_id,
            limit=200,
            protocol_run_id=protocol_id,
            project_id=project_id,
            event_types=event_types,
        )
        if batch:
            idle_ticks = 0
            for e in batch:
                out = schemas.EventOut.model_validate(e)
                last_id = max(last_id, out.id)
                if category_set and (out.event_category or "other") not in category_set:
                    continue
                yield _event_to_sse(out)
        else:
            idle_ticks += 1
            if idle_ticks >= int(30 / max(poll_interval_seconds, 0.1)):
                idle_ticks = 0
                yield ": heartbeat\n\n"

        await asyncio.sleep(poll_interval_seconds)


@router.get("/events")
async def events_stream(
    protocol_id: Optional[int] = Query(None, description="Filter by protocol ID"),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    kind: Optional[str] = Query(None, description="Deprecated: use event_type"),
    category: Optional[List[str]] = Query(None, description="Filter by event category"),
    since_id: int = Query(0, ge=0, description="Only stream events with id > since_id"),
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    db: Database = Depends(get_db),
):
    """
    Server-Sent Events stream for real-time updates.
    
    Use query parameters to filter events:
    - protocol_id: Only receive events for this protocol
    - project_id: Only receive events for this project
    """
    effective_since = since_id
    if last_event_id and last_event_id.isdigit():
        effective_since = max(effective_since, int(last_event_id))

    effective_event_types = [event_type or kind] if (event_type or kind) else None
    return StreamingResponse(
        event_generator(
            db,
            protocol_id,
            project_id,
            event_types=effective_event_types,
            categories=category,
            since_id=effective_since,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/events/recent")
async def recent_events(
    limit: int = Query(50, ge=1, le=200),
    protocol_id: Optional[int] = Query(None, description="Filter by protocol ID"),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    kind: Optional[str] = Query(None, description="Deprecated: use event_type"),
    category: Optional[List[str]] = Query(None, description="Filter by event category"),
    db: Database = Depends(get_db),
):
    """
    Get recent events (non-streaming).
    
    Returns the last N events from the DB-backed event store.
    """
    effective_event_types = [event_type or kind] if (event_type or kind) else None
    items = db.list_recent_events(
        limit=limit,
        protocol_run_id=protocol_id,
        project_id=project_id,
        event_types=effective_event_types,
        categories=category,
    )
    return {
        "events": [schemas.EventOut.model_validate(e).model_dump() for e in items],
    }
