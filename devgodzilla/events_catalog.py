"""Event taxonomy helpers for consistent event types and categories."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional


_EVENT_CATEGORY_OVERRIDES = {
    "protocol_started": "planning",
    "protocol_completed": "execution",
    "protocol_failed": "execution",
    "protocol_paused": "execution",
    "protocol_resumed": "execution",
}

_EVENT_CATEGORY_PREFIXES: dict[str, tuple[str, ...]] = {
    "onboarding": ("onboarding_", "setup_", "clarification_"),
    "discovery": ("discovery_",),
    "planning": ("planning_", "plan_", "spec_"),
    "execution": ("step_", "execute_", "run_", "job_"),
    "qa": ("qa_", "step_qa_", "feedback_", "quality_"),
    "policy": ("policy_",),
    "ci_webhook": ("ci_", "webhook_", "github_", "gitlab_"),
}

_ACRONYMS = {"qa", "ci", "api", "sse", "id"}


def _camel_to_snake(name: str) -> str:
    if not name:
        return name
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.replace("__", "_").lower()


def snake_to_camel(value: str) -> str:
    parts = [p for p in value.split("_") if p]
    return "".join(part.upper() if part in _ACRONYMS else part.capitalize() for part in parts)


def normalize_event_type(event_type: str) -> str:
    if not event_type:
        return event_type
    if "_" in event_type:
        return event_type.lower()
    return _camel_to_snake(event_type)


def event_type_variants(event_type: str) -> List[str]:
    normalized = normalize_event_type(event_type)
    variants = {event_type, normalized}
    if normalized:
        variants.add(snake_to_camel(normalized))
    return [v for v in variants if v]


def infer_event_category(event_type: str) -> str:
    normalized = normalize_event_type(event_type)
    if not normalized:
        return "other"
    override = _EVENT_CATEGORY_OVERRIDES.get(normalized)
    if override:
        return override
    for category, prefixes in _EVENT_CATEGORY_PREFIXES.items():
        if any(normalized.startswith(prefix) for prefix in prefixes):
            return category
    return "other"


def normalize_event_categories(categories: Optional[Iterable[str]]) -> List[str]:
    if not categories:
        return []
    return [normalize_event_type(c) for c in categories if c]
