from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


def extract_spec_run_id(metadata: Any) -> Optional[int]:
    if not isinstance(metadata, dict):
        return None
    value = metadata.get("spec_run_id")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.isdigit():
            return int(candidate)
    return None


def with_spec_run_id(
    metadata: Optional[Mapping[str, Any]],
    spec_run_id: Optional[int],
) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(metadata or {})
    if spec_run_id is not None:
        merged["spec_run_id"] = int(spec_run_id)
    return merged
