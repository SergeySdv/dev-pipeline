"""
Handle Feedback Script

Handles feedback loop actions when QA fails or clarification is needed.

Args:
    action: Feedback action (clarify, re_plan, re_specify, retry)
    context: Context about the failure
    step_id: Step that triggered feedback

Returns:
    resolved: Whether the feedback was resolved
    next_action: Recommended next action
    updated_context: Updated context after feedback handling
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Import DevGodzilla services if available
try:
    from devgodzilla.services import ClarifierService, PlanningService
    from devgodzilla.db import get_database
    DEVGODZILLA_AVAILABLE = True
except ImportError:
    DEVGODZILLA_AVAILABLE = False


FEEDBACK_ACTIONS = {
    "clarify": "Request clarification from user",
    "re_plan": "Re-generate the implementation plan",
    "re_specify": "Re-generate the specification",
    "retry": "Retry the step with updated context",
    "skip": "Skip this step and continue",
    "block": "Block workflow until manual resolution",
}


def main(
    action: str,
    context: dict = None,
    step_id: str = "",
) -> dict:
    """Handle feedback loop action."""
    
    context = context or {}
    start_time = datetime.now()
    
    if action not in FEEDBACK_ACTIONS:
        return {
            "resolved": False,
            "error": f"Unknown action: {action}. Valid actions: {list(FEEDBACK_ACTIONS.keys())}",
        }
    
    # Use DevGodzilla services if available
    if DEVGODZILLA_AVAILABLE and action in ["clarify", "re_plan"]:
        try:
            return _handle_with_devgodzilla(action, context, step_id)
        except Exception as e:
            pass
    
    # Demo feedback handling
    return _demo_handle_feedback(action, context, step_id, start_time)


def _handle_with_devgodzilla(
    action: str,
    context: dict,
    step_id: str,
) -> dict:
    """Handle feedback using DevGodzilla services."""
    
    db = get_database()
    
    if action == "clarify":
        clarifier = ClarifierService(db)
        question = clarifier.generate_question(context)
        return {
            "resolved": False,
            "next_action": "await_user_input",
            "question": question,
            "clarification_id": question.id if hasattr(question, 'id') else None,
        }
    
    elif action == "re_plan":
        planning = PlanningService(db)
        # This would trigger re-planning
        return {
            "resolved": False,
            "next_action": "generate_plan",
            "updated_context": context,
        }
    
    return {"resolved": False, "next_action": "manual"}


def _demo_handle_feedback(
    action: str,
    context: dict,
    step_id: str,
    start_time: datetime,
) -> dict:
    """Demo feedback handling."""
    
    updated_context = dict(context)
    updated_context["feedback_handled_at"] = start_time.isoformat()
    updated_context["feedback_action"] = action
    
    if action == "clarify":
        # Generate a clarification question
        error_message = context.get("error", "Unknown error")
        qa_failures = context.get("qa_failures", [])
        
        question = f"Step {step_id} needs clarification:\n"
        if qa_failures:
            question += f"QA gates failed: {', '.join(qa_failures)}\n"
        question += f"Error context: {error_message}\n"
        question += "How should we proceed?"
        
        return {
            "resolved": False,
            "next_action": "await_user_input",
            "question": question,
            "options": [
                "Retry with more context",
                "Skip this step",
                "Modify requirements",
                "Block for manual fix",
            ],
            "updated_context": updated_context,
            "step_id": step_id,
            "demo_mode": True,
        }
    
    elif action == "re_plan":
        return {
            "resolved": False,
            "next_action": "generate_plan",
            "message": f"Triggering re-planning from step {step_id}",
            "updated_context": updated_context,
            "demo_mode": True,
        }
    
    elif action == "re_specify":
        return {
            "resolved": False,
            "next_action": "generate_spec",
            "message": "Specification update required",
            "updated_context": updated_context,
            "demo_mode": True,
        }
    
    elif action == "retry":
        updated_context["retry_count"] = context.get("retry_count", 0) + 1
        return {
            "resolved": True,
            "next_action": "execute_step",
            "message": f"Retrying step {step_id}",
            "updated_context": updated_context,
            "demo_mode": True,
        }
    
    elif action == "skip":
        return {
            "resolved": True,
            "next_action": "continue",
            "message": f"Skipping step {step_id}",
            "updated_context": updated_context,
            "step_skipped": True,
            "demo_mode": True,
        }
    
    elif action == "block":
        return {
            "resolved": False,
            "next_action": "manual",
            "message": f"Workflow blocked at step {step_id}",
            "updated_context": updated_context,
            "blocked": True,
            "demo_mode": True,
        }
    
    return {
        "resolved": False,
        "next_action": "unknown",
        "error": f"Unhandled action: {action}",
        "demo_mode": True,
    }
