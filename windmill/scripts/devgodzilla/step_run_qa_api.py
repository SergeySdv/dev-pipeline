"""
Step Run QA (DevGodzilla API)

Runs QA gates for a single step via DevGodzilla API.

Args:
    step_run_id: Step run ID
    gates: Optional list of gate IDs (lint, type, test)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._api import api_json


def main(step_run_id: int, gates: Optional[List[str]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    if gates:
        payload["gates"] = gates
    return api_json("POST", f"/steps/{step_run_id}/actions/qa", body=payload)

