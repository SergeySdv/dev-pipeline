"""
List Projects Script

Lists all projects for dashboard via DevGodzilla API.
"""

import os
import urllib.request
import json
from typing import Dict, Any


def main() -> Dict[str, Any]:
    """List all projects by calling DevGodzilla API."""
    try:
        # Get DevGodzilla API URL from environment or use default
        base_url = os.environ.get("DEVGODZILLA_API_URL", "http://devgodzilla-api:8000")

        # Call DevGodzilla projects API
        url = f"{base_url}/projects"
        with urllib.request.urlopen(url, timeout=10) as response:
            projects_data = json.loads(response.read().decode())

        # Transform data for dashboard
        projects = [
            {
                "id": p.get("id"),
                "name": p.get("name", "Unknown"),
                "git_url": p.get("git_url", ""),
                "description": p.get("description", ""),
                "base_branch": p.get("base_branch", "main"),
                "created_at": p.get("created_at", ""),
                "status": p.get("status", "active") or "active",
            }
            for p in projects_data
        ]

        return {"projects": projects}

    except Exception as e:
        return {"projects": [], "error": f"Failed to fetch projects: {str(e)}"}
