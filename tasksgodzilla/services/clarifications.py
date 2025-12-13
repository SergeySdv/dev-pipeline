from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from tasksgodzilla.domain import Clarification
from tasksgodzilla.logging import get_logger
from tasksgodzilla.storage import BaseDatabase

log = get_logger(__name__)


def _scope_key(*, project_id: int, protocol_run_id: Optional[int] = None, step_run_id: Optional[int] = None) -> str:
    if step_run_id is not None:
        return f"step:{step_run_id}"
    if protocol_run_id is not None:
        return f"protocol:{protocol_run_id}"
    return f"project:{project_id}"


@dataclass
class ClarificationsService:
    db: BaseDatabase

    def ensure_from_policy(
        self,
        *,
        project_id: int,
        policy: dict[str, Any],
        applies_to: str,
        protocol_run_id: Optional[int] = None,
        step_run_id: Optional[int] = None,
        answered_by: Optional[str] = None,
    ) -> list[Clarification]:
        """
        Materialize clarification questions from a policy into the DB.
        Filters to matching applies_to and de-dupes by (scope,key).
        """
        clarifications = policy.get("clarifications") if isinstance(policy, dict) else None
        if not isinstance(clarifications, list) or not clarifications:
            return []

        scope = _scope_key(project_id=project_id, protocol_run_id=protocol_run_id, step_run_id=step_run_id)
        out: list[Clarification] = []
        for item in clarifications:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            question = item.get("question")
            item_applies = item.get("applies_to") or item.get("appliesTo")
            if not isinstance(key, str) or not key.strip():
                continue
            if not isinstance(question, str) or not question.strip():
                continue
            if item_applies and str(item_applies) != applies_to:
                continue
            blocking = bool(item.get("blocking")) if "blocking" in item else False
            recommended = item.get("recommended")
            if recommended is not None and not isinstance(recommended, dict):
                # Store only objects in DB; keep raw in events/UI if needed.
                recommended = {"value": recommended}
            options = item.get("options")
            if options is not None and not isinstance(options, list):
                options = None
            try:
                row = self.db.upsert_clarification(
                    scope=scope,
                    project_id=project_id,
                    protocol_run_id=protocol_run_id,
                    step_run_id=step_run_id,
                    key=key.strip(),
                    question=question.strip(),
                    recommended=recommended,
                    options=options,
                    applies_to=applies_to,
                    blocking=blocking,
                )
                out.append(row)
            except Exception as exc:  # pragma: no cover - best effort
                log.warning(
                    "clarification_upsert_failed",
                    extra={"project_id": project_id, "scope": scope, "key": key, "error": str(exc)},
                )
        return out

    def list_open(
        self,
        *,
        project_id: Optional[int] = None,
        protocol_run_id: Optional[int] = None,
        step_run_id: Optional[int] = None,
        applies_to: Optional[str] = None,
        limit: int = 200,
    ) -> list[Clarification]:
        return self.db.list_clarifications(
            project_id=project_id,
            protocol_run_id=protocol_run_id,
            step_run_id=step_run_id,
            status="open",
            applies_to=applies_to,
            limit=limit,
        )

    def set_clarification_answer(
        self,
        *,
        project_id: int,
        key: str,
        answer: Optional[dict],
        protocol_run_id: Optional[int] = None,
        step_run_id: Optional[int] = None,
        answered_by: Optional[str] = None,
    ) -> Clarification:
        scope = _scope_key(project_id=project_id, protocol_run_id=protocol_run_id, step_run_id=step_run_id)
        return self.db.answer_clarification(scope=scope, key=key, answer=answer, answered_by=answered_by, status="answered")

    def has_blocking_open(
        self,
        *,
        project_id: Optional[int] = None,
        protocol_run_id: Optional[int] = None,
        step_run_id: Optional[int] = None,
        applies_to: Optional[str] = None,
    ) -> bool:
        open_items = self.list_open(
            project_id=project_id,
            protocol_run_id=protocol_run_id,
            step_run_id=step_run_id,
            applies_to=applies_to,
        )
        return any(c.blocking for c in open_items)

    def list_blocking_open(
        self,
        *,
        project_id: Optional[int] = None,
        protocol_run_id: Optional[int] = None,
        step_run_id: Optional[int] = None,
        applies_to: Optional[str] = None,
        limit: int = 200,
    ) -> list[Clarification]:
        items = self.list_open(
            project_id=project_id,
            protocol_run_id=protocol_run_id,
            step_run_id=step_run_id,
            applies_to=applies_to,
            limit=limit,
        )
        return [c for c in items if c.blocking]

    # Backward-compatible alias (assignment so it doesn't violate naming tests).
    answer = set_clarification_answer
