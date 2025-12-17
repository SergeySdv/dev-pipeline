"""
List Protocols Script

Lists protocols for a specific project via DevGodzilla API.
Now includes stats and optional filtering.
"""

import os
import urllib.request
import json
from typing import Dict, Any
from datetime import date


def main(project_id: int = None, status: str = None) -> Dict[str, Any]:
    """List protocols, optionally filtered by project or status.
    
    Args:
        project_id: Optional filter by project ID
        status: Optional filter by status (pending, running, completed, failed)
    """
    try:
        base_url = os.environ.get("DEVGODZILLA_API_URL", "http://devgodzilla-api:8000")
        
        # Build query params
        params = []
        if project_id:
            params.append(f"project_id={project_id}")
        if status:
            params.append(f"status={status}")
        
        query = "?" + "&".join(params) if params else ""
        url = f"{base_url}/protocols{query}"
        
        with urllib.request.urlopen(url, timeout=10) as response:
            protocols_data = json.loads(response.read().decode())
        
        # Calculate stats
        all_count = len(protocols_data)
        running_count = sum(1 for p in protocols_data if p.get("status") == "running")
        today_str = date.today().isoformat()
        completed_today = sum(1 for p in protocols_data 
            if p.get("status") == "completed" 
            and p.get("created_at", "")[:10] == today_str)
        
        protocols = [
            {
                "id": p.get("id"),
                "protocol_name": p.get("protocol_name", "Unknown"),
                "project_id": p.get("project_id"),
                "status": p.get("status", "pending"),
                "summary": p.get("summary", ""),
                "created_at": p.get("created_at", ""),
                "base_branch": p.get("base_branch", ""),
            }
            for p in protocols_data
        ]
        
        return {
            "protocols": protocols,
            "stats": {
                "total": all_count,
                "running": running_count,
                "completed_today": completed_today
            }
        }

    except Exception as e:
        return {"protocols": [], "stats": {"total": 0, "running": 0, "completed_today": 0}, "error": str(e)}
