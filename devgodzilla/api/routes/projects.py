from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from devgodzilla.api import schemas
from devgodzilla.api.dependencies import get_db, get_service_context
from devgodzilla.api.routes._clarification_enrichment import enrich_clarifications
from devgodzilla.api.routes._project_git import (
    create_project_branch_in_repo,
    list_git_worktree_paths,
    list_project_branches_for_repo,
    list_project_pulls_for_repo,
    list_project_worktrees_for_repo,
    project_github_token,
)
from devgodzilla.db.database import Database, _UNSET
from devgodzilla.events_catalog import normalize_event_type
from devgodzilla.logging import get_logger, log_extra
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.project_storage import (
    normalize_storage_path,
    project_storage_payload,
    resolve_effective_repo_path,
    validate_project_storage_settings,
)
from devgodzilla.services.policy import PolicyService
from devgodzilla.services.clarifier import ClarifierService
from devgodzilla.services.specification import SpecificationService

router = APIRouter()
logger = get_logger(__name__)


def _looks_like_git_repository_url(value: Optional[str]) -> bool:
    url = (value or "").strip()
    if not url:
        return False
    if re.match(r"^git@[^:]+:.+", url):
        return True
    if not re.match(r"^(https?|ssh)://", url):
        return False
    parsed = urlparse(url)
    path = [segment for segment in parsed.path.split("/") if segment]
    if url.endswith(".git"):
        return True
    return (parsed.hostname or "").lower() in {
        "github.com",
        "gitlab.com",
        "bitbucket.org",
        "dev.azure.com",
    } and len(path) >= 2

def _policy_location(metadata: Optional[dict]) -> Optional[str]:
    if not metadata:
        return None
    if isinstance(metadata.get("location"), str):
        return metadata["location"]
    file_name = metadata.get("file") or metadata.get("path")
    section = metadata.get("section") or metadata.get("heading")
    if file_name and section:
        return f"{file_name}#{section}"
    if file_name:
        return str(file_name)
    if section:
        return str(section)
    return None


def _append_project_event(
    db: Database,
    *,
    project_id: int,
    event_type: str,
    message: str,
    metadata: Optional[dict] = None,
) -> None:
    try:
        db.append_event(
            protocol_run_id=None,
            project_id=project_id,
            event_type=event_type,
            message=message,
            metadata=metadata,
        )
    except Exception:
        pass


def _remove_branch_worktree_if_needed(
    *,
    repo_path: Path,
    branch_name: str,
    project_id: int,
    ctx: ServiceContext,
) -> Optional[str]:
    from devgodzilla.services.git import GitService

    attached_worktree = list_git_worktree_paths(repo_path).get(branch_name)
    if not attached_worktree:
        return None

    attached_worktree_path = Path(attached_worktree).expanduser()
    if attached_worktree_path.resolve() == repo_path.resolve():
        raise HTTPException(status_code=400, detail="Cannot delete the currently checked out branch")

    try:
        GitService(ctx).remove_worktree(repo_path, attached_worktree_path, project_id=project_id)
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Branch {branch_name} is still used by worktree {attached_worktree_path}: {exc}",
        ) from exc
    return str(attached_worktree_path)


def _project_out(
    project: Any,
    ctx: Optional[ServiceContext] = None,
    *,
    onboarding_queued: Optional[bool] = None,
    onboarding_error: Optional[str] = None,
) -> schemas.ProjectOut:
    config = ctx.config if ctx is not None else get_service_context().config
    payload = schemas.ProjectOut.model_validate(project).model_dump()
    payload.update(project_storage_payload(project, config))
    payload["onboarding_queued"] = onboarding_queued
    payload["onboarding_error"] = onboarding_error
    return schemas.ProjectOut(**payload)


def _validate_storage_or_400(
    *,
    repo_mode: Optional[schemas.RepoMode],
    local_path: Optional[str],
    managed_repo_root_override: Optional[str],
    worktrees_root_override: Optional[str],
    artifacts_root_override: Optional[str],
    git_url: Optional[str],
    ctx: ServiceContext,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    normalized_local_path = normalize_storage_path(local_path)
    normalized_managed_root = normalize_storage_path(managed_repo_root_override)
    normalized_worktrees_root = normalize_storage_path(worktrees_root_override)
    normalized_artifacts_root = normalize_storage_path(artifacts_root_override)
    errors = validate_project_storage_settings(
        repo_mode=repo_mode.value if repo_mode else None,
        local_path=normalized_local_path,
        managed_repo_root_override=normalized_managed_root,
        worktrees_root_override=normalized_worktrees_root,
        artifacts_root_override=normalized_artifacts_root,
        git_url=git_url,
        config=ctx.config,
    )
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    return (
        normalized_local_path,
        normalized_managed_root,
        normalized_worktrees_root,
        normalized_artifacts_root,
    )

def _normalize_policy_enforcement_mode(mode: Optional[str]) -> Optional[str]:
    if mode is None:
        return None
    value = str(mode).strip().lower()
    mapping = {
        "advisory": "warn",
        "mandatory": "block",
        "enforce": "block",
        "blocking": "block",
    }
    return mapping.get(value, value)


def _project_secrets_with_github_token(
    existing: Optional[dict],
    github_token: Optional[str],
) -> Optional[dict]:
    secrets = dict(existing or {})
    token = (github_token or "").strip()
    if token:
        secrets["github_token"] = token
    else:
        secrets.pop("github_token", None)
    return secrets or None


class ProjectOnboardRequest(BaseModel):
    branch: Optional[str] = Field(default=None, description="Branch to checkout after clone (defaults to project.base_branch)")
    clone_if_missing: bool = Field(default=True, description="Clone repo if local_path is missing")
    constitution_content: Optional[str] = Field(default=None, description="Optional custom constitution content")
    run_discovery_agent: bool = Field(
        default=True,
        description="Run headless agent discovery (writes specs/discovery/_runtime/* artifacts)",
    )
    discovery_pipeline: bool = Field(default=True, description="Use multi-stage discovery pipeline")
    discovery_engine_id: Optional[str] = Field(default=None, description="Engine ID for discovery (default: opencode)")
    discovery_model: Optional[str] = Field(default=None, description="Model for discovery (default: engine default)")


class ProjectOnboardResponse(BaseModel):
    success: bool
    project: schemas.ProjectOut
    local_path: str
    speckit_initialized: bool
    speckit_path: Optional[str] = None
    constitution_hash: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    discovery_success: bool = False
    discovery_log_path: Optional[str] = None
    discovery_missing_outputs: List[str] = Field(default_factory=list)
    discovery_error: Optional[str] = None
    error: Optional[str] = None


def _get_project_or_404(db: Database, project_id: int):
    try:
        return db.get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


def _event_time_map(recent_events: List[Any]) -> dict[str, Any]:
    times: dict[str, Any] = {}
    for event in recent_events:
        event_type = normalize_event_type(event.event_type)
        times.setdefault(event_type, event.created_at)
    return times


def _count_blocking_clarifications(db: Database, project_id: int) -> int:
    try:
        clarifications = db.list_clarifications(project_id=project_id, status="open")
    except (KeyError, AttributeError):
        return 0
    return sum(1 for clarification in clarifications if getattr(clarification, "blocking", False))


def _build_onboarding_stages(
    project: Any,
    event_set: set[str],
    event_times: dict[str, Any],
    blocking_count: int,
) -> List[schemas.OnboardingStage]:
    repo_stage = _repository_onboarding_stage(project, event_set, event_times)
    spec_stage = _speckit_onboarding_stage(project, event_set, event_times, repo_stage.status)
    return [
        repo_stage,
        spec_stage,
        _discovery_onboarding_stage(event_set, event_times),
        _clarifications_onboarding_stage(blocking_count, repo_stage.status, spec_stage.status),
    ]


def _repository_onboarding_stage(
    project: Any,
    event_set: set[str],
    event_times: dict[str, Any],
) -> schemas.OnboardingStage:
    repo_status = "completed" if project.local_path or "onboarding_repo_ready" in event_set else "pending"
    if repo_status == "pending" and {"onboarding_started", "onboarding_enqueued"} & event_set:
        repo_status = "running"

    completed_at = None
    if repo_status == "completed":
        completed_at = event_times.get("onboarding_repo_ready") or project.updated_at or project.created_at

    return schemas.OnboardingStage(
        name="Repository Setup",
        status=repo_status,
        started_at=event_times.get("onboarding_started") or event_times.get("onboarding_enqueued"),
        completed_at=completed_at,
    )


def _speckit_onboarding_stage(
    project: Any,
    event_set: set[str],
    event_times: dict[str, Any],
    repo_status: str,
) -> schemas.OnboardingStage:
    spec_status = "completed" if project.constitution_hash or "onboarding_speckit_initialized" in event_set else "pending"
    if "onboarding_failed" in event_set:
        spec_status = "failed"
    elif repo_status == "running" and spec_status == "pending":
        spec_status = "running"

    completed_at = None
    if spec_status == "completed":
        completed_at = event_times.get("onboarding_speckit_initialized") or project.updated_at or project.created_at

    return schemas.OnboardingStage(
        name="SpecKit Initialization",
        status=spec_status,
        started_at=event_times.get("onboarding_repo_ready") or event_times.get("onboarding_started"),
        completed_at=completed_at,
    )


def _discovery_onboarding_stage(
    event_set: set[str],
    event_times: dict[str, Any],
) -> schemas.OnboardingStage:
    if "discovery_completed" in event_set:
        status = "completed"
    elif "discovery_failed" in event_set:
        status = "failed"
    elif "discovery_started" in event_set:
        status = "running"
    elif "discovery_skipped" in event_set:
        status = "skipped"
    else:
        status = "pending"

    return schemas.OnboardingStage(
        name="Discovery",
        status=status,
        started_at=event_times.get("discovery_started"),
        completed_at=event_times.get("discovery_completed") if status == "completed" else None,
    )


def _clarifications_onboarding_stage(
    blocking_count: int,
    repo_status: str,
    spec_status: str,
) -> schemas.OnboardingStage:
    if repo_status == "pending" or spec_status == "pending":
        status = "pending"
    elif blocking_count > 0:
        status = "blocked"
    else:
        status = "completed"
    return schemas.OnboardingStage(name="Clarifications", status=status)


def _onboarding_overall_status(stages: List[schemas.OnboardingStage], blocking_count: int) -> str:
    stage_statuses = {stage.status for stage in stages}
    if "failed" in stage_statuses:
        return "failed"
    if blocking_count > 0:
        return "blocked"
    if "running" in stage_statuses:
        return "running"
    if stage_statuses.issubset({"completed", "skipped"}):
        return "completed"
    return "pending"


def _resolve_onboarding_repo_path(
    project: Any,
    request: ProjectOnboardRequest,
    project_id: int,
    ctx: ServiceContext,
) -> Path:
    from devgodzilla.services.git import GitService

    git = GitService(ctx)
    github_token = project_github_token(project)
    repo_resolve_start = time.perf_counter()
    try:
        effective_repo_path = resolve_effective_repo_path(project, ctx.config)
        repo_path = git.resolve_repo_path(
            project.git_url,
            project.name,
            str(effective_repo_path) if effective_repo_path else project.local_path,
            project_id=project.id,
            clone_if_missing=bool(request.clone_if_missing),
            github_token=github_token,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Clone failed: {exc}") from exc

    repo_resolve_duration_ms = int((time.perf_counter() - repo_resolve_start) * 1000)
    logger.info(
        "onboarding_repo_resolved",
        extra=log_extra(
            project_id=project_id,
            repo_path=str(repo_path),
            duration_ms=repo_resolve_duration_ms,
        ),
    )
    return repo_path


def _checkout_onboarding_branch(project: Any, repo_path: Path, branch: str, ctx: ServiceContext) -> None:
    from devgodzilla.services.git import run_process

    if not branch:
        return

    git = GitService(ctx)
    github_token = project_github_token(project)
    try:
        git_env = git.build_remote_git_env(project.git_url, github_token)
        run_process(["git", "fetch", "--prune", "origin", branch], cwd=repo_path, check=False, env=git_env)
        result = run_process(["git", "checkout", branch], cwd=repo_path, check=False)
        if result.returncode != 0:
            run_process(
                ["git", "checkout", "-B", branch, f"origin/{branch}"],
                cwd=repo_path,
                check=False,
                env=git_env,
            )
    except Exception:
        pass


def _resolve_constitution_content(
    request: ProjectOnboardRequest,
    project_id: int,
    repo_path: Path,
    ctx: ServiceContext,
    db: Database,
) -> tuple[Optional[str], Any]:
    constitution_content = request.constitution_content
    effective_policy = None
    if constitution_content is not None:
        return constitution_content, effective_policy

    try:
        policy_service = PolicyService(ctx, db)
        effective_policy = policy_service.resolve_effective_policy(
            project_id,
            repo_root=repo_path,
            include_repo_local=True,
        )
        constitution_content = policy_service.render_constitution(effective_policy)
    except Exception:
        constitution_content = None
        effective_policy = None
    return constitution_content, effective_policy


def _run_discovery_agent(
    project_id: int,
    repo_path: Path,
    request: ProjectOnboardRequest,
    ctx: ServiceContext,
    db: Database,
) -> tuple[bool, Optional[str], List[str], Optional[str]]:
    discovery_success = False
    discovery_log_path: Optional[str] = None
    discovery_missing_outputs: List[str] = []
    discovery_error: Optional[str] = None

    if not request.run_discovery_agent:
        logger.debug("discovery_skipped", extra=log_extra(project_id=project_id, reason="disabled"))
        _append_project_event(
            db,
            project_id=project_id,
            event_type="discovery_skipped",
            message="Discovery skipped",
            metadata={"reason": "disabled"},
        )
        return discovery_success, discovery_log_path, discovery_missing_outputs, discovery_error

    discovery_start = time.perf_counter()
    _append_project_event(
        db,
        project_id=project_id,
        event_type="discovery_started",
        message="Discovery started",
        metadata={
            "engine_id": request.discovery_engine_id or "opencode",
            "model": request.discovery_model,
            "pipeline": bool(request.discovery_pipeline),
        },
    )
    try:
        from devgodzilla.services.discovery_agent import DiscoveryAgentService

        service = DiscoveryAgentService(ctx, db=db)
        discovery = service.run_discovery(
            repo_root=repo_path,
            engine_id=request.discovery_engine_id or "opencode",
            model=request.discovery_model,
            pipeline=bool(request.discovery_pipeline),
            stages=None,
            timeout_seconds=int(os.environ.get("DEVGODZILLA_DISCOVERY_TIMEOUT_SECONDS", "900")),
            strict_outputs=True,
            project_id=project_id,
        )
        discovery_success = bool(discovery.success)
        discovery_log_path = str(discovery.log_path)
        discovery_missing_outputs = [str(path) for path in discovery.missing_outputs]
        discovery_error = discovery.error
        discovery_warning = discovery.warning
        fallback_engine_id = discovery.fallback_engine_id
    except Exception as exc:
        discovery_warning = None
        fallback_engine_id = None
        discovery_error = str(exc)

    discovery_duration_ms = int((time.perf_counter() - discovery_start) * 1000)
    logger.info(
        "discovery_completed",
        extra=log_extra(
            project_id=project_id,
            success=discovery_success,
            duration_ms=discovery_duration_ms,
            log_path=discovery_log_path,
            missing_outputs=discovery_missing_outputs,
            error=discovery_error,
            warning=discovery_warning,
            fallback_engine_id=fallback_engine_id,
        ),
    )
    _append_project_event(
        db,
        project_id=project_id,
        event_type="discovery_completed" if discovery_success else "discovery_failed",
        message="Discovery completed" if discovery_success else ("Discovery failed" if not discovery_warning else f"Discovery completed with fallback: {discovery_warning}"),
        metadata={
            "success": discovery_success,
            "log_path": discovery_log_path,
            "missing_outputs": discovery_missing_outputs,
            "error": discovery_error,
            "warning": discovery_warning,
            "fallback_engine_id": fallback_engine_id,
        },
    )
    return discovery_success, discovery_log_path, discovery_missing_outputs, discovery_error


class CreateBranchRequest(BaseModel):
    name: str = Field(..., description="New branch name (e.g. feature/foo)")
    base_ref: Optional[str] = Field(default=None, description="Base ref (branch/sha), defaults to project.base_branch")
    checkout: bool = Field(default=False, description="Checkout the new branch after creation")
    push: bool = Field(default=False, description="Push branch to origin and set upstream")


@router.post("/projects", response_model=schemas.ProjectOut)
def create_project(
    project: schemas.ProjectCreate,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Create a new project."""
    logger.debug(
        "create_project_request",
        extra=log_extra(
            project_name=project.name,
            base_branch=project.base_branch,
            has_git_url=bool((project.git_url or "").strip()),
            auto_onboard=bool(project.auto_onboard),
            auto_discovery=bool(project.auto_discovery),
            local_path=project.local_path,
        ),
    )
    has_git_url = bool((project.git_url or "").strip())
    has_local_path = bool((project.local_path or "").strip())
    (
        normalized_local_path,
        normalized_managed_root,
        normalized_worktrees_root,
        normalized_artifacts_root,
    ) = _validate_storage_or_400(
        repo_mode=project.repo_mode,
        local_path=project.local_path,
        managed_repo_root_override=project.managed_repo_root_override,
        worktrees_root_override=project.worktrees_root_override,
        artifacts_root_override=project.artifacts_root_override,
        git_url=project.git_url,
        ctx=ctx,
    )
    if project.auto_onboard and not (has_git_url or has_local_path):
        raise HTTPException(status_code=400, detail="git_url or local_path is required for auto onboarding")
    if project.auto_onboard and has_git_url and not _looks_like_git_repository_url(project.git_url):
        raise HTTPException(
            status_code=400,
            detail="git_url must be a cloneable Git repository URL for auto onboarding",
        )
    if project.auto_onboard and not getattr(ctx.config, "windmill_enabled", False):
        raise HTTPException(status_code=503, detail="Windmill integration not configured")

    created = db.create_project(
        name=project.name,
        git_url=project.git_url or "",
        base_branch=project.base_branch,
        secrets=_project_secrets_with_github_token(None, project.github_token),
        local_path=normalized_local_path,
        repo_mode=project.repo_mode.value if project.repo_mode else None,
        task_cycle_autonomous=bool(project.task_cycle_autonomous),
        managed_repo_root_override=normalized_managed_root,
        worktrees_root_override=normalized_worktrees_root,
        artifacts_root_override=normalized_artifacts_root,
    )
    logger.info(
        "project_created",
        extra=log_extra(
            project_id=created.id,
            project_name=created.name,
            base_branch=created.base_branch,
            local_path=created.local_path,
            auto_onboard=bool(project.auto_onboard),
        ),
    )

    onboarding_queued: Optional[bool] = None
    onboarding_error: Optional[str] = None

    if project.auto_onboard:
        try:
            from devgodzilla.services.onboarding_queue import enqueue_project_onboarding

            logger.debug(
                "onboarding_enqueue_start",
                extra=log_extra(
                    project_id=created.id,
                    branch=created.base_branch,
                    run_discovery_agent=bool(project.auto_discovery),
                ),
            )
            enqueue_start = time.perf_counter()
            result = enqueue_project_onboarding(
                ctx,
                db,
                project_id=created.id,
                branch=created.base_branch,
                run_discovery_agent=bool(project.auto_discovery),
            )
            enqueue_duration_ms = int((time.perf_counter() - enqueue_start) * 1000)
            logger.info(
                "onboarding_enqueue_success",
                extra=log_extra(
                    project_id=created.id,
                    windmill_job_id=result.windmill_job_id,
                    duration_ms=enqueue_duration_ms,
                ),
            )
            onboarding_queued = True
        except Exception as exc:
            onboarding_error = str(exc)
            logger.exception(
                "onboarding_enqueue_exception",
                extra=log_extra(project_id=created.id, error=onboarding_error),
            )
            _append_project_event(
                db,
                project_id=created.id,
                event_type="onboarding_enqueue_failed",
                message="Failed to enqueue onboarding",
                metadata={"error": onboarding_error},
            )
            onboarding_queued = False

    return _project_out(
        created,
        ctx,
        onboarding_queued=onboarding_queued,
        onboarding_error=onboarding_error,
    )

@router.get("/projects", response_model=List[schemas.ProjectOut])
def list_projects(
    status: Optional[str] = None,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """List all projects, optionally filtered by status."""
    projects = db.list_projects()
    if status:
        projects = [p for p in projects if p.status == status]
    return [_project_out(project, ctx) for project in projects]

@router.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: int,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Get project by ID."""
    try:
        return _project_out(db.get_project(project_id), ctx)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

@router.put("/projects/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: int,
    project: schemas.ProjectUpdate,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Update a project."""
    try:
        existing = db.get_project(project_id)
        next_git_url = project.git_url if project.git_url is not None else existing.git_url
        next_local_path = project.local_path if "local_path" in project.model_fields_set else existing.local_path
        next_repo_mode = project.repo_mode if "repo_mode" in project.model_fields_set else existing.repo_mode
        next_managed_root = (
            project.managed_repo_root_override
            if "managed_repo_root_override" in project.model_fields_set
            else existing.managed_repo_root_override
        )
        next_worktrees_root = (
            project.worktrees_root_override
            if "worktrees_root_override" in project.model_fields_set
            else existing.worktrees_root_override
        )
        next_artifacts_root = (
            project.artifacts_root_override
            if "artifacts_root_override" in project.model_fields_set
            else existing.artifacts_root_override
        )
        (
            normalized_local_path,
            normalized_managed_root,
            normalized_worktrees_root,
            normalized_artifacts_root,
        ) = _validate_storage_or_400(
            repo_mode=next_repo_mode if isinstance(next_repo_mode, schemas.RepoMode) else (
                schemas.RepoMode(next_repo_mode) if next_repo_mode else None
            ),
            local_path=next_local_path,
            managed_repo_root_override=next_managed_root,
            worktrees_root_override=next_worktrees_root,
            artifacts_root_override=next_artifacts_root,
            git_url=next_git_url,
            ctx=ctx,
        )
        secrets = _UNSET
        if "github_token" in project.model_fields_set:
            secrets = _project_secrets_with_github_token(existing.secrets, project.github_token)
        updated = db.update_project(
            project_id,
            name=project.name,
            description=project.description if project.description is not None else _UNSET,
            status=project.status.value if project.status else None,
            git_url=project.git_url,
            base_branch=project.base_branch,
            secrets=secrets,
            local_path=normalized_local_path if "local_path" in project.model_fields_set else _UNSET,
            repo_mode=(
                project.repo_mode.value
                if "repo_mode" in project.model_fields_set and project.repo_mode is not None
                else (None if "repo_mode" in project.model_fields_set else _UNSET)
            ),
            task_cycle_autonomous=(
                project.task_cycle_autonomous
                if "task_cycle_autonomous" in project.model_fields_set
                else _UNSET
            ),
            managed_repo_root_override=(
                normalized_managed_root
                if "managed_repo_root_override" in project.model_fields_set
                else _UNSET
            ),
            worktrees_root_override=(
                normalized_worktrees_root
                if "worktrees_root_override" in project.model_fields_set
                else _UNSET
            ),
            artifacts_root_override=(
                normalized_artifacts_root
                if "artifacts_root_override" in project.model_fields_set
                else _UNSET
            ),
        )
        return _project_out(updated, ctx)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

@router.post("/projects/{project_id}/archive", response_model=schemas.ProjectOut)
def archive_project(
    project_id: int,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Archive a project."""
    try:
        return _project_out(db.update_project(project_id, status="archived"), ctx)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

@router.post("/projects/{project_id}/unarchive", response_model=schemas.ProjectOut)
def unarchive_project(
    project_id: int,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Unarchive a project."""
    try:
        return _project_out(db.update_project(project_id, status="active"), ctx)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Database = Depends(get_db)
):
    """Delete a project and all associated data."""
    try:
        db.get_project(project_id)  # Check exists first
        db.delete_project(project_id)
        return {"status": "deleted", "project_id": project_id}
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/projects/{project_id}/onboarding", response_model=schemas.OnboardingSummary)
def get_project_onboarding(
    project_id: int,
    db: Database = Depends(get_db)
):
    """Get onboarding status summary."""
    project = _get_project_or_404(db, project_id)
    recent_events = db.list_recent_events(
        limit=50,
        project_id=project_id,
        categories=["onboarding", "discovery"],
    )
    event_set = {normalize_event_type(event.event_type) for event in recent_events}
    event_times = _event_time_map(recent_events)
    blocking_count = _count_blocking_clarifications(db, project_id)
    stages = _build_onboarding_stages(project, event_set, event_times, blocking_count)
    overall_status = _onboarding_overall_status(stages, blocking_count)
    events = [
        schemas.OnboardingEvent(
            id=event.id,
            event_type=event.event_type,
            message=event.message,
            metadata=event.metadata,
            created_at=event.created_at,
        )
        for event in reversed(recent_events)
    ]

    return schemas.OnboardingSummary(
        project_id=project_id,
        status=overall_status,
        stages=stages,
        events=events,
        blocking_clarifications=blocking_count
    )


@router.post("/projects/{project_id}/actions/onboard", response_model=ProjectOnboardResponse)
@router.post("/projects/{project_id}/onboarding/actions/start", response_model=ProjectOnboardResponse)
def onboard_project(
    project_id: int,
    request: ProjectOnboardRequest = ProjectOnboardRequest(), # Allow empty body
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """
    Onboard a project repository for DevGodzilla workflows.

    - Ensures the repo exists locally (clone if missing)
    - Checks out the requested branch (or project.base_branch)
    - Initializes `.specify/` via SpecificationService
    """
    project = _get_project_or_404(db, project_id)
    if not project.git_url:
        raise HTTPException(status_code=400, detail="Project has no git_url")

    logger.debug(
        "onboarding_request_received",
        extra=log_extra(
            project_id=project_id,
            branch=request.branch or project.base_branch,
            clone_if_missing=bool(request.clone_if_missing),
            run_discovery_agent=bool(request.run_discovery_agent),
            discovery_pipeline=bool(request.discovery_pipeline),
            discovery_engine_id=request.discovery_engine_id,
            discovery_model=request.discovery_model,
        ),
    )
    _append_project_event(
        db,
        project_id=project_id,
        event_type="onboarding_started",
        message="Onboarding started",
        metadata={
            "branch": request.branch or project.base_branch,
            "clone_if_missing": bool(request.clone_if_missing),
        },
    )
    repo_path = _resolve_onboarding_repo_path(project, request, project_id, ctx)
    branch = (request.branch or project.base_branch or "main").strip()
    _checkout_onboarding_branch(project, repo_path, branch, ctx)

    if not project.local_path or project.local_path != str(repo_path):
        try:
            db.update_project(project_id, local_path=str(repo_path))
        except Exception:
            pass

    _append_project_event(
        db,
        project_id=project_id,
        event_type="onboarding_repo_ready",
        message="Repository ready for onboarding",
        metadata={"repo_path": str(repo_path), "branch": branch},
    )

    constitution_content, effective_policy = _resolve_constitution_content(
        request,
        project_id,
        repo_path,
        ctx,
        db,
    )
    spec_service = SpecificationService(ctx, db)
    spec_init_start = time.perf_counter()
    init_result = spec_service.init_project(
        str(repo_path),
        constitution_content=constitution_content,
        project_id=project_id,
    )
    spec_init_duration_ms = int((time.perf_counter() - spec_init_start) * 1000)
    logger.info(
        "onboarding_speckit_initialized",
        extra=log_extra(
            project_id=project_id,
            success=bool(init_result.success),
            duration_ms=spec_init_duration_ms,
            spec_path=init_result.spec_path,
        ),
    )

    _append_project_event(
        db,
        project_id=project_id,
        event_type="onboarding_speckit_initialized" if init_result.success else "onboarding_failed",
        message="SpecKit initialized" if init_result.success else "SpecKit initialization failed",
        metadata={
            "warnings": init_result.warnings,
            "error": init_result.error,
            "spec_path": init_result.spec_path,
        },
    )

    if effective_policy is not None:
        try:
            clarifier = ClarifierService(ctx, db)
            clarifier.ensure_from_policy(
                project_id=project_id,
                policy=effective_policy.policy,
                applies_to="onboarding",
            )
        except Exception:
            pass

    discovery_success, discovery_log_path, discovery_missing_outputs, discovery_error = _run_discovery_agent(
        project_id,
        repo_path,
        request,
        ctx,
        db,
    )
    updated_project = db.get_project(project_id)

    return ProjectOnboardResponse(
        success=init_result.success,
        project=schemas.ProjectOut.model_validate(updated_project),
        local_path=str(repo_path),
        speckit_initialized=init_result.success,
        speckit_path=init_result.spec_path,
        constitution_hash=init_result.constitution_hash,
        warnings=init_result.warnings,
        discovery_success=discovery_success,
        discovery_log_path=discovery_log_path,
        discovery_missing_outputs=discovery_missing_outputs,
        discovery_error=discovery_error,
        error=init_result.error,
    )


@router.post("/projects/{project_id}/discovery/actions/retry", response_model=schemas.DiscoveryRetryResponse)
def retry_project_discovery(
    project_id: int,
    request: schemas.DiscoveryRetryRequest = schemas.DiscoveryRetryRequest(),
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Retry repository discovery for a project."""
    try:
        project = db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local repository path")

    repo_root = Path(project.local_path).expanduser().resolve()
    if not repo_root.exists():
        raise HTTPException(status_code=404, detail="Project repository not found on disk")

    engine_id = request.discovery_engine_id or "opencode"
    pipeline = bool(request.discovery_pipeline)

    _append_project_event(
        db,
        project_id=project_id,
        event_type="discovery_started",
        message="Discovery started",
        metadata={
            "engine_id": engine_id,
            "model": request.discovery_model,
            "pipeline": pipeline,
            "retry": True,
        },
    )

    discovery_success = False
    discovery_log_path: Optional[str] = None
    discovery_missing_outputs: List[str] = []
    discovery_error: Optional[str] = None
    discovery_warning: Optional[str] = None
    fallback_engine_id: Optional[str] = None
    try:
        from devgodzilla.services.discovery_agent import DiscoveryAgentService

        svc = DiscoveryAgentService(ctx, db=db)
        disc = svc.run_discovery(
            repo_root=repo_root,
            engine_id=engine_id,
            model=request.discovery_model,
            pipeline=pipeline,
            stages=request.stages,
            timeout_seconds=int(os.environ.get("DEVGODZILLA_DISCOVERY_TIMEOUT_SECONDS", "900")),
            strict_outputs=bool(request.strict_outputs),
            project_id=project_id,
        )
        discovery_success = bool(disc.success)
        discovery_log_path = str(disc.log_path)
        discovery_missing_outputs = [str(p) for p in disc.missing_outputs]
        discovery_error = disc.error
        discovery_warning = disc.warning
        fallback_engine_id = disc.fallback_engine_id
    except Exception as e:
        discovery_success = False
        discovery_error = str(e)

    _append_project_event(
        db,
        project_id=project_id,
        event_type="discovery_completed" if discovery_success else "discovery_failed",
        message="Discovery completed" if discovery_success else ("Discovery failed" if not discovery_warning else f"Discovery completed with fallback: {discovery_warning}"),
        metadata={
            "success": discovery_success,
            "log_path": discovery_log_path,
            "missing_outputs": discovery_missing_outputs,
            "error": discovery_error,
            "warning": discovery_warning,
            "fallback_engine_id": fallback_engine_id,
            "engine_id": engine_id,
            "model": request.discovery_model,
            "pipeline": pipeline,
            "retry": True,
        },
    )

    return schemas.DiscoveryRetryResponse(
        success=discovery_success,
        discovery_log_path=discovery_log_path,
        discovery_missing_outputs=discovery_missing_outputs,
        discovery_error=discovery_error,
        discovery_warning=discovery_warning,
        fallback_engine_id=fallback_engine_id,
        engine_id=engine_id,
        model=request.discovery_model,
        pipeline=pipeline,
    )


@router.get("/projects/{project_id}/discovery/logs", response_model=schemas.ArtifactContentOut)
def get_project_discovery_logs(
    project_id: int,
    max_bytes: int = 200_000,
    db: Database = Depends(get_db),
):
    try:
        project = db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local repository path")

    repo_root = Path(project.local_path).expanduser().resolve()
    log_path = repo_root / "specs" / "discovery" / "_runtime" / "opencode-discovery.log"
    if not log_path.exists() or not log_path.is_file():
        return schemas.ArtifactContentOut(
            id="discovery-log",
            name=log_path.name,
            type="log",
            content="",
            truncated=False,
        )

    max_bytes = max(1, min(int(max_bytes), 2_000_000))
    raw = log_path.read_bytes()
    truncated = len(raw) > max_bytes
    if truncated:
        raw = raw[:max_bytes]
    try:
        content = raw.decode("utf-8")
    except Exception:
        content = raw.decode("utf-8", errors="replace")

    return schemas.ArtifactContentOut(
        id="discovery-log",
        name=log_path.name,
        type="log",
        content=content,
        truncated=truncated,
    )

@router.get("/projects/{project_id}/sprints", response_model=List[schemas.SprintOut])
def list_project_sprints(
    project_id: int,
    status: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """List sprints for a specific project."""
    return db.list_sprints(project_id=project_id, status=status)

@router.get("/projects/{project_id}/tasks", response_model=List[schemas.AgileTaskOut])
def list_project_tasks(
    project_id: int,
    sprint_id: Optional[int] = None,
    board_status: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 100,
    db: Database = Depends(get_db)
):
    """List tasks for a specific project."""
    return db.list_tasks(
        project_id=project_id,
        sprint_id=sprint_id,
        board_status=board_status,
        assignee=assignee,
        limit=limit
    )

@router.get("/projects/{project_id}/policy", response_model=schemas.PolicyConfigOut)
def get_project_policy(
    project_id: int,
    db: Database = Depends(get_db)
):
    """Get policy configuration for a project."""
    try:
        project = db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return schemas.PolicyConfigOut(
        policy_pack_key=project.policy_pack_key,
        policy_pack_version=project.policy_pack_version,
        policy_overrides=project.policy_overrides,
        policy_repo_local_enabled=bool(project.policy_repo_local_enabled) if project.policy_repo_local_enabled is not None else False,
        policy_enforcement_mode=_normalize_policy_enforcement_mode(project.policy_enforcement_mode) or "warn",
    )

@router.put("/projects/{project_id}/policy", response_model=schemas.ProjectOut)
def update_project_policy(
    project_id: int,
    policy: schemas.PolicyConfigUpdate,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Update policy configuration for a project."""
    try:
        db.get_project(project_id)  # Check exists
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Build update kwargs
    kwargs = {}
    if policy.policy_pack_key is not None:
        kwargs["policy_pack_key"] = policy.policy_pack_key
    if policy.policy_pack_version is not None:
        kwargs["policy_pack_version"] = policy.policy_pack_version
    if policy.policy_overrides is not None:
        kwargs["policy_overrides"] = policy.policy_overrides
    if policy.policy_repo_local_enabled is not None:
        kwargs["policy_repo_local_enabled"] = policy.policy_repo_local_enabled
    if policy.policy_enforcement_mode is not None:
        kwargs["policy_enforcement_mode"] = _normalize_policy_enforcement_mode(policy.policy_enforcement_mode)

    updated = db.update_project_policy(project_id, **kwargs)
    try:
        if updated.local_path:
            constitution_path = Path(updated.local_path).expanduser() / ".specify" / "memory" / "constitution.md"
            if constitution_path.exists():
                policy_service = PolicyService(ctx, db)
                effective = policy_service.resolve_effective_policy(
                    project_id,
                    repo_root=Path(updated.local_path).expanduser(),
                    include_repo_local=True,
                )
                constitution_content = policy_service.render_constitution(effective)
                spec_service = SpecificationService(ctx, db)
                spec_service.save_constitution(updated.local_path, constitution_content, project_id=project_id)
    except Exception:
        pass

    return _project_out(updated, ctx)

@router.get("/projects/{project_id}/policy/effective", response_model=schemas.EffectivePolicyOut)
def get_effective_policy(
    project_id: int,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Get computed effective policy with hash."""
    try:
        project = db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    from devgodzilla.services.policy import PolicyService
    from pathlib import Path
    
    policy_service = PolicyService(ctx, db)
    
    # Determine repo root
    repo_root = None
    if project.local_path:
        try:
            repo_root = Path(project.local_path).expanduser()
        except Exception:
            pass
    
    effective = policy_service.resolve_effective_policy(
        project_id,
        repo_root=repo_root,
        include_repo_local=True,
    )
    
    return schemas.EffectivePolicyOut(
        hash=effective.effective_hash,
        policy=effective.policy,
        pack_key=effective.pack_key,
        pack_version=effective.pack_version,
    )

@router.get("/projects/{project_id}/policy/findings", response_model=List[schemas.PolicyFindingOut])
def get_policy_findings(
    project_id: int,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """Get policy violation findings for a project."""
    try:
        db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    from devgodzilla.services.policy import PolicyService
    
    policy_service = PolicyService(ctx, db)
    findings = policy_service.evaluate_project(project_id)
    
    return [
        schemas.PolicyFindingOut(
            code=f.code,
            severity=f.severity,
            message=f.message,
            scope=f.scope,
            location=_policy_location(f.metadata),
            suggested_fix=f.suggested_fix,
            metadata=f.metadata,
        )
        for f in findings
    ]

@router.get("/projects/{project_id}/branches", response_model=List[schemas.BranchOut])
def list_project_branches(
    project_id: int,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """List git branches for a project repository."""
    project = _get_project_or_404(db, project_id)
    return list_project_branches_for_repo(project, ctx)


@router.post("/projects/{project_id}/branches")
def create_project_branch(
    project_id: int,
    request: CreateBranchRequest,
    db: Database = Depends(get_db),
):
    """Create a git branch in the project repository."""
    project = _get_project_or_404(db, project_id)
    branch_name, base_commit = create_project_branch_in_repo(
        project,
        branch_name=request.name,
        base_ref=request.base_ref,
        checkout=request.checkout,
        push=request.push,
    )

    _append_project_event(
        db,
        project_id=project_id,
        event_type="git_branch_created",
        message=f"Created branch {branch_name} from {base_commit}",
        metadata={
            "branch": branch_name,
            "base_ref": request.base_ref or project.base_branch or "main",
            "checkout": request.checkout,
            "push": request.push,
        },
    )
    return {"message": f"Branch created: {branch_name}", "branch": branch_name}


@router.post("/projects/{project_id}/branches/{branch}/delete")
def delete_project_branch(
    project_id: int,
    branch: str,
    delete_remote: bool = False,
    ctx: ServiceContext = Depends(get_service_context),
    db: Database = Depends(get_db),
):
    """Delete a local (and optionally remote) git branch for the project repository."""
    try:
        project = db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local repository path")

    from devgodzilla.services.git import run_process

    repo_path = Path(project.local_path).expanduser()
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail="Project repository path does not exist")
    if not (repo_path / ".git").exists():
        raise HTTPException(status_code=400, detail="Project path is not a git repository")

    branch_name = (branch or "").strip()
    if not branch_name:
        raise HTTPException(status_code=400, detail="Branch name is required")

    current_branch = run_process(["git", "symbolic-ref", "--short", "HEAD"], cwd=repo_path, check=False).stdout.strip()
    if current_branch and current_branch == branch_name:
        raise HTTPException(status_code=400, detail="Cannot delete the currently checked out branch")

    exists_res = run_process(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"], cwd=repo_path, check=False)
    if exists_res.returncode != 0:
        raise HTTPException(status_code=404, detail=f"Local branch not found: {branch_name}")

    removed_worktree_path = _remove_branch_worktree_if_needed(
        repo_path=repo_path,
        branch_name=branch_name,
        project_id=project_id,
        ctx=ctx,
    )

    run_process(["git", "branch", "-D", branch_name], cwd=repo_path, check=True)

    deleted_remote_branch = False
    if delete_remote:
        remote_res = run_process(["git", "push", "origin", "--delete", branch_name], cwd=repo_path, check=False)
        deleted_remote_branch = remote_res.returncode == 0

    _append_project_event(
        db,
        project_id=project_id,
        event_type="git_branch_deleted",
        message=f"Deleted branch {branch_name}",
        metadata={
            "branch": branch_name,
            "deleted_remote": deleted_remote_branch,
            "removed_worktree_path": removed_worktree_path,
        },
    )
    message = f"Branch deleted: {branch_name}"
    if removed_worktree_path:
        message = f"{message} (removed worktree {removed_worktree_path})"
    return {"message": message}

@router.get("/projects/{project_id}/clarifications", response_model=List[schemas.ClarificationOut])
def list_project_clarifications(
    project_id: int,
    status: Optional[str] = None,
    limit: int = 100,
    db: Database = Depends(get_db)
):
    """List clarifications scoped to a project."""
    try:
        db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    if status == "all":
        status = None
    
    clarifications = db.list_clarifications(
        project_id=project_id,
        status=status,
        limit=limit
    )
    return enrich_clarifications(db, clarifications)

@router.post("/projects/{project_id}/clarifications/{key}", response_model=schemas.ClarificationOut)
def answer_project_clarification(
    project_id: int,
    key: str,
    answer: schemas.ClarificationAnswer,
    db: Database = Depends(get_db)
):
    """Answer a clarification scoped to a project."""
    try:
        db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Construct scope for project-level clarification
    scope = f"project:{project_id}"
    
    # Store answer as structured JSON
    payload = {"text": answer.answer}
    
    try:
        updated = db.answer_clarification(
            scope=scope,
            key=key,
            answer=payload,
            answered_by=answer.answered_by,
            status="answered",
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Clarification not found")
    
    return updated

@router.get("/projects/{project_id}/commits", response_model=List[schemas.CommitOut])
def list_project_commits(
    project_id: int,
    limit: int = 20,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """List recent git commits for a project repository."""
    try:
        project = db.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local repository path")
    
    from pathlib import Path
    from devgodzilla.services.git import run_process
    
    repo_path = Path(project.local_path).expanduser()
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail="Project repository path does not exist")
    
    if not (repo_path / ".git").exists():
        raise HTTPException(status_code=400, detail="Project path is not a git repository")
    
    commits = []
    try:
        # Use git log to get recent commits with format: sha|subject|author name|relative date
        result = run_process(
            ["git", "log", f"-{limit}", "--format=%H|%s|%an|%ar"],
            cwd=repo_path,
        )
        for line in result.stdout.strip().splitlines():
            if line:
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    commits.append(schemas.CommitOut(
                        sha=parts[0],
                        message=parts[1],
                        author=parts[2],
                        date=parts[3],
                    ))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to list commits: {exc}")
    
    return commits

@router.get("/projects/{project_id}/pulls", response_model=List[schemas.PullRequestOut])
def list_project_pulls(
    project_id: int,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """List open pull requests for a project repository (GitHub only)."""
    _ = ctx
    project = _get_project_or_404(db, project_id)
    return list_project_pulls_for_repo(project)


@router.get("/projects/{project_id}/worktrees", response_model=List[schemas.WorktreeOut])
def list_project_worktrees(
    project_id: int,
    db: Database = Depends(get_db),
    ctx: ServiceContext = Depends(get_service_context),
):
    """List worktrees associated with protocols and spec runs for a project."""
    _ = ctx
    project = _get_project_or_404(db, project_id)
    return list_project_worktrees_for_repo(project_id, project, db)
