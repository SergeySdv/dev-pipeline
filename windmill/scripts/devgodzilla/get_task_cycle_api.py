"""
Get Task Cycle Work Items (DevGodzilla API)

Fetches projected task-cycle work items for a project and optional protocol run.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._api import api_json


def main(
    project_id: int,
    *,
    protocol_run_id: Optional[int] = None,
) -> Dict[str, Any]:
    path = f"/projects/{project_id}/task-cycle"
    if protocol_run_id is not None:
        path = f"{path}?protocol_run_id={protocol_run_id}"
    payload = api_json("GET", path)
    items: List[Dict[str, Any]] = payload if isinstance(payload, list) else []
    next_work_item_id = None
    for item in items:
        if not item.get("pr_ready"):
            next_work_item_id = item.get("id")
            break
    return {
        "work_items": items,
        "next_work_item_id": next_work_item_id,
        "count": len(items),
    }
