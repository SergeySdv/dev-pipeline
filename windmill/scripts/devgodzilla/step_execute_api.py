"""
Step Execute (DevGodzilla API)

Executes a single step via DevGodzilla API.

Args:
    step_run_id: Step run ID
"""

from __future__ import annotations

from typing import Any, Dict

from ._api import api_json


def main(step_run_id: int) -> Dict[str, Any]:
    return api_json("POST", f"/steps/{step_run_id}/actions/execute", body={})

