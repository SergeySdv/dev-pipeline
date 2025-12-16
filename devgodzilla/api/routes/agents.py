from typing import List
from fastapi import APIRouter, HTTPException

from devgodzilla.api import schemas
from devgodzilla.engines.registry import get_registry

router = APIRouter()

@router.get("/agents", response_model=List[schemas.AgentInfo])
def list_agents():
    """List available agents."""
    registry = get_registry()
    agents = []
    
    # Use real registry metadata if populated
    # In a real app, engines are registered at startup.
    # If standard engines are not auto-registered in this context, the list might be empty.
    # For now, we trust list_metadata() returns what's registered.
    
    for meta in registry.list_metadata():
        agents.append(schemas.AgentInfo(
            id=meta.id,
            name=meta.display_name,
            kind=meta.kind.value if hasattr(meta.kind, 'value') else str(meta.kind),
            capabilities=meta.capabilities,
            status="available" # Health check logic can go here
        ))
        
    return agents


@router.get("/agents/{agent_id}", response_model=schemas.AgentInfo)
def get_agent(agent_id: str):
    """Get agent details by ID."""
    registry = get_registry()
    meta = next((m for m in registry.list_metadata() if m.id == agent_id), None)
    if meta is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return schemas.AgentInfo(
        id=meta.id,
        name=meta.display_name,
        kind=meta.kind.value if hasattr(meta.kind, "value") else str(meta.kind),
        capabilities=meta.capabilities,
        status="available",
    )


@router.post("/agents/{agent_id}/health")
def check_agent_health(agent_id: str):
    """Check agent health (availability)."""
    registry = get_registry()
    try:
        engine = registry.get_or_default(agent_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        ok = engine.check_availability()
    except Exception:
        ok = False

    return {"status": "available" if ok else "unavailable"}
