"""
Update Project Script

Updates a project's name or status via DevGodzilla API.
"""

import os
import urllib.request
import json
from typing import Dict, Any


def main(
    project_id: int,
    name: str = None,
    status: str = None,
    description: str = None
) -> Dict[str, Any]:
    """Update project details.
    
    Args:
        project_id: Project ID to update
        name: New project name (optional)
        status: New status - 'active' or 'archived' (optional)
        description: New description (optional)
    """
    try:
        base_url = os.environ.get("DEVGODZILLA_API_URL", "http://devgodzilla-api:8000")
        
        data = {}
        if name is not None:
            data["name"] = name
        if status is not None:
            data["status"] = status
        if description is not None:
            data["description"] = description
        
        if not data:
            return {"success": False, "error": "No fields to update"}
        
        req = urllib.request.Request(
            f"{base_url}/projects/{project_id}",
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='PUT'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            project = json.loads(response.read().decode())
        
        return {
            "success": True,
            "project": {
                "id": project.get("id"),
                "name": project.get("name"),
                "status": project.get("status"),
                "description": project.get("description", ""),
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
