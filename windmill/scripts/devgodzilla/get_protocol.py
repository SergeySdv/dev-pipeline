"""
Get Protocol Script

Fetches a single protocol by ID with its steps via DevGodzilla API.
"""

import os
import urllib.request
import json
from typing import Dict, Any


def main(protocol_id: int) -> Dict[str, Any]:
    """Get protocol details and steps by ID.
    
    Args:
        protocol_id: The protocol ID to fetch
    """
    try:
        base_url = os.environ.get("DEVGODZILLA_API_URL", "http://devgodzilla-api:8000")
        
        # Get protocol
        url = f"{base_url}/protocols/{protocol_id}"
        with urllib.request.urlopen(url, timeout=10) as response:
            protocol = json.loads(response.read().decode())
        
        # Get steps
        steps_url = f"{base_url}/steps?protocol_run_id={protocol_id}"
        with urllib.request.urlopen(steps_url, timeout=10) as response:
            steps_data = json.loads(response.read().decode())
        
        steps = [
            {
                "id": s.get("id"),
                "step_name": s.get("step_name", "Step"),
                "step_type": s.get("step_type", ""),
                "step_index": s.get("step_index", 0),
                "status": s.get("status", "pending"),
                "depends_on": s.get("depends_on") or [],
                "parallel_group": s.get("parallel_group", ""),
                "assigned_agent": s.get("assigned_agent", ""),
                "summary": s.get("summary", ""),
            }
            for s in steps_data
        ]
        
        return {
            "protocol": {
                "id": protocol.get("id"),
                "protocol_name": protocol.get("protocol_name", "Unknown"),
                "project_id": protocol.get("project_id"),
                "status": protocol.get("status", "pending"),
                "summary": protocol.get("summary", ""),
                "base_branch": protocol.get("base_branch", ""),
                "created_at": protocol.get("created_at", ""),
            },
            "steps": steps,
            "step_count": len(steps),
            "completed_count": sum(1 for s in steps if s["status"] == "completed"),
            "running_count": sum(1 for s in steps if s["status"] == "running"),
        }

    except Exception as e:
        return {"protocol": None, "steps": [], "error": str(e)}
