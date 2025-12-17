"""
Create Project Script

Creates a new project via DevGodzilla API.
"""

import os
import urllib.request
import json
from typing import Dict, Any


def main(
    name: str,
    git_url: str = "",
    base_branch: str = "main",
    description: str = ""
) -> Dict[str, Any]:
    """Create a new project.
    
    Args:
        name: Project name (required)
        git_url: Git repository URL
        base_branch: Base branch name (default: main)
        description: Project description
    """
    try:
        base_url = os.environ.get("DEVGODZILLA_API_URL", "http://devgodzilla-api:8000")
        
        data = {
            "name": name,
            "base_branch": base_branch or "main",
        }
        
        if git_url:
            data["git_url"] = git_url
        if description:
            data["description"] = description
        
        req = urllib.request.Request(
            f"{base_url}/projects",
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            project = json.loads(response.read().decode())
        
        return {
            "success": True,
            "project": {
                "id": project.get("id"),
                "name": project.get("name"),
                "git_url": project.get("git_url", ""),
                "base_branch": project.get("base_branch", "main"),
                "description": project.get("description", ""),
                "status": project.get("status", "active"),
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
