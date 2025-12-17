"""
Get Project Script

Fetches a single project by ID via DevGodzilla API.
"""

import os
import urllib.request
import json
from typing import Dict, Any


def main(project_id: int) -> Dict[str, Any]:
    """Get project details by ID.
    
    Args:
        project_id: The project ID to fetch
    """
    try:
        base_url = os.environ.get("DEVGODZILLA_API_URL", "http://devgodzilla-api:8000")
        
        url = f"{base_url}/projects/{project_id}"
        with urllib.request.urlopen(url, timeout=10) as response:
            project = json.loads(response.read().decode())
        
        return {
            "project": {
                "id": project.get("id"),
                "name": project.get("name", "Unknown"),
                "description": project.get("description", ""),
                "git_url": project.get("git_url", ""),
                "base_branch": project.get("base_branch", "main"),
                "local_path": project.get("local_path", ""),
                "status": project.get("status", "active"),
                "constitution_version": project.get("constitution_version", ""),
                "created_at": project.get("created_at", ""),
                "updated_at": project.get("updated_at", ""),
            }
        }

    except Exception as e:
        return {"project": None, "error": str(e)}
