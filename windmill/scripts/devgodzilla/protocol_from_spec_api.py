"""
Create Protocol From Spec (DevGodzilla API)

Creates a protocol run from SpecKit tasks/spec artifacts.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._api import api_json


def main(
    project_id: int,
    *,
    spec_path: Optional[str] = None,
    tasks_path: Optional[str] = None,
    protocol_name: Optional[str] = None,
    spec_run_id: Optional[int] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    payload = {
        "project_id": project_id,
        "spec_path": spec_path,
        "tasks_path": tasks_path,
        "protocol_name": protocol_name,
        "spec_run_id": spec_run_id,
        "overwrite": overwrite,
    }
    return api_json("POST", "/protocols/from-spec", body=payload)
