"""
DevGodzilla Webhook Handlers

Handles incoming webhooks from Windmill and CI/CD systems.
"""

import hashlib
import hmac
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel

from devgodzilla.api.dependencies import get_db
from devgodzilla.db.database import Database

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ==================== Request Models ====================

class WindmillJobUpdate(BaseModel):
    """Windmill job status update."""
    job_id: str
    status: str  # running, success, failure, cancelled
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class GitHubWebhook(BaseModel):
    """GitHub webhook payload."""
    action: str
    repository: Dict[str, Any]
    sender: Dict[str, Any]
    # Workflow run specific
    workflow_run: Optional[Dict[str, Any]] = None
    # Check run specific
    check_run: Optional[Dict[str, Any]] = None
    # Pull request specific
    pull_request: Optional[Dict[str, Any]] = None


class GitLabWebhook(BaseModel):
    """GitLab webhook payload."""
    object_kind: str
    project: Dict[str, Any]
    user: Dict[str, Any]
    # Pipeline specific
    object_attributes: Optional[Dict[str, Any]] = None


def _normalize_repo_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.strip().lower()
    if text.endswith(".git"):
        text = text[:-4]
    if text.startswith("git@"):
        text = text.replace("git@", "", 1)
        text = text.replace(":", "/", 1)
    if text.startswith("https://"):
        text = text[len("https://") :]
    elif text.startswith("http://"):
        text = text[len("http://") :]
    return text.strip("/")


def _resolve_project_id(db: Database, candidates: list[str]) -> Optional[int]:
    normalized = {_normalize_repo_url(value) for value in candidates if value}
    normalized.discard(None)
    if not normalized:
        return None
    for project in db.list_projects():
        project_url = _normalize_repo_url(project.git_url)
        if project_url and project_url in normalized:
            return project.id
    return None


def _emit_ci_event(
    db: Database,
    *,
    event_type: str,
    message: str,
    project_id: Optional[int],
    protocol_run_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    if project_id is None and protocol_run_id is None:
        return
    try:
        db.append_event(
            protocol_run_id=protocol_run_id,
            project_id=project_id,
            event_type=event_type,
            message=message,
            metadata=metadata,
        )
    except Exception:
        pass


# ==================== Windmill Webhooks ====================

@router.post("/windmill/job")
async def windmill_job_webhook(
    payload: WindmillJobUpdate,
    request: Request,
    db: Database = Depends(get_db),
):
    """
    Handle Windmill job status updates.
    
    Called by Windmill when a job completes, fails, or is cancelled.
    Updates the corresponding protocol/step run in the database.
    """
    from devgodzilla.logging import get_logger
    logger = get_logger(__name__)
    
    logger.info(
        "windmill_webhook_received",
        extra={
            "job_id": payload.job_id,
            "status": payload.status,
        },
    )
    
    status_map = {
        "queued": "queued",
        "running": "running",
        "success": "succeeded",
        "completed": "succeeded",
        "failure": "failed",
        "failed": "failed",
        "cancelled": "cancelled",
        "canceled": "cancelled",
    }

    try:
        db.update_job_run_by_windmill_id(
            payload.job_id,
            status=status_map.get(payload.status.lower(), payload.status.lower()),
            result=payload.result,
            error=payload.error,
            started_at=payload.started_at.isoformat() if payload.started_at else None,
            finished_at=payload.finished_at.isoformat() if payload.finished_at else None,
        )
    except KeyError:
        # Webhook can arrive before we persist the job run; don't fail the webhook.
        pass
    
    return {
        "status": "received",
        "job_id": payload.job_id,
    }


@router.post("/windmill/flow")
async def windmill_flow_webhook(
    request: Request,
):
    """
    Handle Windmill flow completion webhook.
    
    Called when an entire flow completes.
    """
    payload = await request.json()
    
    from devgodzilla.logging import get_logger
    logger = get_logger(__name__)
    
    logger.info(
        "windmill_flow_webhook_received",
        extra={"payload": payload},
    )
    
    # TODO: Update protocol_run by windmill_flow_id
    
    return {"status": "received"}


# ==================== GitHub Webhooks ====================

@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
    project_id: Optional[int] = Query(None, description="Override project ID for logging"),
    protocol_run_id: Optional[int] = Query(None, description="Override protocol run ID for logging"),
    db: Database = Depends(get_db),
):
    """
    Handle GitHub webhooks.
    
    Supported events:
    - workflow_run: When a CI workflow completes
    - check_run: When a check run completes
    - pull_request: When a PR is opened/merged
    """
    payload = await request.json()
    
    from devgodzilla.logging import get_logger
    logger = get_logger(__name__)
    
    logger.info(
        "github_webhook_received",
        extra={
            "event": x_github_event,
            "action": payload.get("action"),
        },
    )
    
    repo = payload.get("repository", {})
    candidate_urls = [
        repo.get("clone_url"),
        repo.get("ssh_url"),
        repo.get("html_url"),
        repo.get("git_url"),
    ]
    if repo.get("full_name"):
        candidate_urls.append(f"github.com/{repo['full_name']}")
    resolved_project_id = project_id or _resolve_project_id(db, candidate_urls)

    event_type = f"ci_webhook_github_{x_github_event}" if x_github_event else "ci_webhook_github"
    _emit_ci_event(
        db,
        event_type=event_type,
        message=f"GitHub webhook {x_github_event or 'event'} received",
        project_id=resolved_project_id,
        protocol_run_id=protocol_run_id,
        metadata={
            "event": x_github_event,
            "action": payload.get("action"),
            "repository": repo.get("full_name") or repo.get("name"),
            "branch": payload.get("workflow_run", {}).get("head_branch")
            or payload.get("check_run", {}).get("check_suite", {}).get("head_branch")
            or payload.get("pull_request", {}).get("base", {}).get("ref"),
        },
    )

    if x_github_event == "workflow_run":
        return await _handle_workflow_run(payload)
    elif x_github_event == "check_run":
        return await _handle_check_run(payload)
    elif x_github_event == "pull_request":
        return await _handle_pull_request(payload)
    
    return {"status": "ignored", "event": x_github_event}


async def _handle_workflow_run(payload: dict):
    """Handle GitHub workflow_run event."""
    workflow_run = payload.get("workflow_run", {})
    conclusion = workflow_run.get("conclusion")
    
    if conclusion == "success":
        # CI passed - could auto-advance protocol
        pass
    elif conclusion in ("failure", "cancelled"):
        # CI failed - trigger feedback loop
        pass
    
    return {
        "status": "processed",
        "workflow": workflow_run.get("name"),
        "conclusion": conclusion,
    }


async def _handle_check_run(payload: dict):
    """Handle GitHub check_run event."""
    check_run = payload.get("check_run", {})
    return {
        "status": "processed",
        "check": check_run.get("name"),
        "conclusion": check_run.get("conclusion"),
    }


async def _handle_pull_request(payload: dict):
    """Handle GitHub pull_request event."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    
    return {
        "status": "processed",
        "action": action,
        "pr_number": pr.get("number"),
    }


# ==================== GitLab Webhooks ====================

@router.post("/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_token: str = Header(None),
    project_id: Optional[int] = Query(None, description="Override project ID for logging"),
    protocol_run_id: Optional[int] = Query(None, description="Override protocol run ID for logging"),
    db: Database = Depends(get_db),
):
    """
    Handle GitLab webhooks.
    
    Supported events:
    - Pipeline: When a CI pipeline completes
    - Merge Request: When an MR is created/merged
    """
    payload = await request.json()
    
    from devgodzilla.logging import get_logger
    logger = get_logger(__name__)
    
    object_kind = payload.get("object_kind")
    
    logger.info(
        "gitlab_webhook_received",
        extra={"object_kind": object_kind},
    )
    
    project = payload.get("project", {})
    candidate_urls = [
        project.get("web_url"),
        project.get("git_ssh_url"),
        project.get("git_http_url"),
        project.get("http_url"),
        project.get("ssh_url"),
    ]
    resolved_project_id = project_id or _resolve_project_id(db, candidate_urls)

    event_type = f"ci_webhook_gitlab_{object_kind}" if object_kind else "ci_webhook_gitlab"
    attrs = payload.get("object_attributes", {}) or {}
    _emit_ci_event(
        db,
        event_type=event_type,
        message=f"GitLab webhook {object_kind or 'event'} received",
        project_id=resolved_project_id,
        protocol_run_id=protocol_run_id,
        metadata={
            "event": object_kind,
            "status": attrs.get("status"),
            "action": attrs.get("action"),
            "ref": attrs.get("ref"),
            "repository": project.get("path_with_namespace") or project.get("name"),
        },
    )

    if object_kind == "pipeline":
        return await _handle_gitlab_pipeline(payload)
    elif object_kind == "merge_request":
        return await _handle_gitlab_mr(payload)
    
    return {"status": "ignored", "object_kind": object_kind}


async def _handle_gitlab_pipeline(payload: dict):
    """Handle GitLab pipeline event."""
    attrs = payload.get("object_attributes", {})
    return {
        "status": "processed",
        "pipeline_status": attrs.get("status"),
    }


async def _handle_gitlab_mr(payload: dict):
    """Handle GitLab merge request event."""
    attrs = payload.get("object_attributes", {})
    return {
        "status": "processed",
        "action": attrs.get("action"),
        "mr_iid": attrs.get("iid"),
    }
