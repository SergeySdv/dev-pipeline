"""
Project Onboard (DevGodzilla API)

Creates a project in DevGodzilla, clones it locally (in the API container), and initializes `.specify/`.

This script is designed to run inside Windmill and only talks to the DevGodzilla API.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._api import api_json


def main(
    git_url: str,
    project_name: str,
    branch: str = "main",
    description: str = "",
    constitution_content: str = "",
    run_discovery_agent: bool = False,
) -> Dict[str, Any]:
    created = api_json(
        "POST",
        "/projects",
        body={
            "name": project_name,
            "git_url": git_url,
            "base_branch": branch or "main",
            "description": description or "",
        },
    )
    if created.get("error"):
        return {"success": False, "error": created["error"], "step": "create_project"}

    project_id = created.get("id")
    if not isinstance(project_id, int):
        return {"success": False, "error": "DevGodzilla did not return a project id", "step": "create_project"}

    onboard_body: Dict[str, Any] = {
        "branch": branch or None,
        "clone_if_missing": True,
    }
    if constitution_content:
        onboard_body["constitution_content"] = constitution_content
    if run_discovery_agent:
        onboard_body["run_discovery_agent"] = True

    onboarded = api_json("POST", f"/projects/{project_id}/actions/onboard", body=onboard_body)
    if onboarded.get("error"):
        return {
            "success": False,
            "error": onboarded["error"],
            "step": "onboard",
            "project_id": project_id,
        }

    return {
        "success": bool(onboarded.get("success", False)),
        "project_id": project_id,
        "project": onboarded.get("project") or created,
        "local_path": onboarded.get("local_path"),
        "speckit_path": onboarded.get("speckit_path"),
        "constitution_hash": onboarded.get("constitution_hash"),
        "warnings": onboarded.get("warnings") or [],
        "discovery_success": onboarded.get("discovery_success", False),
        "discovery_log_path": onboarded.get("discovery_log_path"),
        "discovery_missing_outputs": onboarded.get("discovery_missing_outputs") or [],
        "discovery_error": onboarded.get("discovery_error"),
    }
