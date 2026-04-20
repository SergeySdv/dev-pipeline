
"""
Create Sprint From Protocol (DevGodzilla API)

Creates a sprint from an existing protocol run.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._api import api_json


def main(
    protocol_id: int,
    sprint_name: Optional[str] = None,
    auto_sync: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a sprint from a protocol run."""
    payload = {
        "sprint_name": sprint_name,
        "auto_sync": auto_sync,
        "start_date": start_date,
        "end_date": end_date,
    }
    return api_json("POST", f"/protocols/{protocol_id}/actions/create-sprint", body=payload)
