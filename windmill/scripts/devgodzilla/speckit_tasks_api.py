"""
SpecKit Tasks (DevGodzilla API)

Runs SpecKit "tasks" for a project by calling the DevGodzilla API.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._api import api_json


def main(project_id: int, plan_path: str, spec_run_id: Optional[int] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {"plan_path": plan_path}
    if spec_run_id is not None:
        body["spec_run_id"] = spec_run_id
    return api_json("POST", f"/projects/{project_id}/speckit/tasks", body=body)
