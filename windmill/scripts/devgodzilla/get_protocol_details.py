
"""
Get Protocol Details Script

Gets full details for a protocol run, including steps.
"""

from typing import List, Dict, Any
try:
    from devgodzilla.db import get_database
    DEVGODZILLA_AVAILABLE = True
except ImportError:
    DEVGODZILLA_AVAILABLE = False

def main(protocol_run_id: int) -> Dict[str, Any]:
    """Get detailed protocol info."""
    if not DEVGODZILLA_AVAILABLE:
        return {"error": "DevGodzilla services not available"}
        
    db = get_database()
    try:
        run = db.get_protocol_run(protocol_run_id)
        steps = db.list_step_runs(protocol_run_id)
        events = db.list_events(protocol_run_id)
        
        return {
            "run": {
                "id": run.id,
                "name": run.protocol_name,
                "status": run.status,
                "branch": run.base_branch,
                "description": run.description,
                "windmill_flow_id": run.windmill_flow_id,
                "created_at": run.created_at,
            },
            "steps": [
                {
                    "id": s.id,
                    "index": s.step_index,
                    "name": s.step_name,
                    "status": s.status,
                    "type": s.step_type,
                    "summary": s.summary,
                    "agent": s.assigned_agent,
                    "parallel_group": s.parallel_group
                }
                for s in steps
            ],
            "events": [
                {
                    "type": e.event_type,
                    "message": e.message,
                    "created_at": e.created_at
                }
                for e in events
            ]
        }
    except Exception as e:
        return {"error": str(e)}
