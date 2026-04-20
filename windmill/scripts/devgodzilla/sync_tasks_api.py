"""
Sync Tasks to Sprint (DevGodzilla API)

Imports SpecKit tasks.md into an existing sprint.
"""

from __future__ import annotations

from typing import Any, Dict

from ._api import api_json


def main(
    sprint_id: int,
    spec_path: str,
    overwrite_existing: bool = False,
) -> Dict[str, Any]:
    """Import tasks from SpecKit markdown into sprint."""
    payload = {
        "spec_path": spec_path,
        "overwrite_existing": overwrite_existing,
    }
    return api_json("POST", f"/sprints/{sprint_id}/actions/import-tasks", body=payload)
