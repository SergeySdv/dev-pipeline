"""
SpecKit Checklist (DevGodzilla API)

Generates a SpecKit checklist by calling the DevGodzilla API.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._api import api_json


def main(project_id: int, spec_path: str, spec_run_id: Optional[int] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {"spec_path": spec_path}
    if spec_run_id is not None:
        body["spec_run_id"] = spec_run_id
    return api_json("POST", f"/projects/{project_id}/speckit/checklist", body=body)
