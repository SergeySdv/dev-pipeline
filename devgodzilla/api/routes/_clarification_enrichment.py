from __future__ import annotations

from typing import List

from devgodzilla.api import schemas
from devgodzilla.db.database import Database
from devgodzilla.qa.gates.prompt import summarize_prompt_qa_report


def enrich_clarification(db: Database, clarification) -> schemas.ClarificationOut:
    payload = schemas.ClarificationOut.model_validate(clarification)
    if payload.applies_to != "qa" or payload.step_run_id is None:
        return payload
    if not payload.key or not payload.key.startswith("qa:prompt_qa:"):
        return payload

    qa_record = db.get_latest_qa_result(step_run_id=payload.step_run_id)
    report_text = getattr(qa_record, "report_text", None) if qa_record else None
    if not isinstance(report_text, str) or not report_text.strip():
        return payload

    details = summarize_prompt_qa_report(report_text)
    if not payload.recommended:
        payload.recommended = {
            "text": details["text"],
            "summary": details["summary"],
            "next_actions": details["next_actions"],
            "report_excerpt": details["report_excerpt"],
        }

    if payload.question.strip() == "Resolve QA finding: Prompt QA reported FAIL":
        payload.question = f"Resolve QA finding: {details['message']}"

    return payload


def enrich_clarifications(db: Database, clarifications: List[object]) -> List[schemas.ClarificationOut]:
    return [enrich_clarification(db, clarification) for clarification in clarifications]
