"""
SpecKit Specify (DevGodzilla API)

Runs SpecKit "specify" for a project by calling the DevGodzilla API.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._api import api_json


def main(project_id: int, description: str, feature_name: str = "") -> Dict[str, Any]:
    body: Dict[str, Any] = {"description": description}
    if feature_name:
        body["feature_name"] = feature_name
    return api_json("POST", f"/projects/{project_id}/speckit/specify", body=body)

