"""
List Clarifications Script

Lists clarifications for the dashboard, optionally filtered.
"""

import os
import urllib.request
import json
from typing import Dict, Any


def main(project_id: int = None, protocol_id: int = None, status: str = None) -> Dict[str, Any]:
    """List clarifications with optional filtering.
    
    Args:
        project_id: Optional filter by project ID
        protocol_id: Optional filter by protocol run ID
        status: Optional filter by status (open, answered)
    """
    try:
        base_url = os.environ.get("DEVGODZILLA_API_URL", "http://devgodzilla-api:8000")
        
        # Build query params
        params = []
        if project_id:
            params.append(f"project_id={project_id}")
        if protocol_id:
            params.append(f"protocol_run_id={protocol_id}")
        if status:
            params.append(f"status={status}")
        
        query = "?" + "&".join(params) if params else ""
        url = f"{base_url}/clarifications{query}"
        
        with urllib.request.urlopen(url, timeout=10) as response:
            clarifications_data = json.loads(response.read().decode())
        
        clarifications = [
            {
                "id": c.get("id"),
                "question": c.get("question", ""),
                "status": c.get("status", "open"),
                "protocol_run_id": c.get("protocol_run_id"),
                "options": c.get("options", []),
                "created_at": c.get("created_at", ""),
            }
            for c in clarifications_data
        ]
        
        open_count = sum(1 for c in clarifications if c["status"] == "open")
        
        return {
            "clarifications": clarifications,
            "open_count": open_count,
            "total_count": len(clarifications),
        }

    except Exception as e:
        return {"clarifications": [], "open_count": 0, "total_count": 0, "error": str(e)}
