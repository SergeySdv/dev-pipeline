"""
SpecKit Tasks (DevGodzilla API)

Runs SpecKit "tasks" for a project by calling the DevGodzilla API.
"""

from __future__ import annotations

from typing import Any, Dict

from ._api import api_json


def main(project_id: int, plan_path: str) -> Dict[str, Any]:
    return api_json("POST", f"/projects/{project_id}/speckit/tasks", body={"plan_path": plan_path})

