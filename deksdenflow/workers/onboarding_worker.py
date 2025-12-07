from pathlib import Path
from typing import Optional

from deksdenflow.domain import ProtocolStatus
from deksdenflow.logging import get_logger, log_extra
from deksdenflow.project_setup import ensure_assets, ensure_local_repo, DEFAULT_PROJECTS_ROOT
from deksdenflow.storage import BaseDatabase

log = get_logger(__name__)


def handle_project_setup(project_id: int, db: BaseDatabase, protocol_run_id: Optional[int] = None) -> None:
    """
    Lightweight onboarding job that prepares a project using the existing starter assets.
    It intentionally avoids mutating git state; the goal is to surface progress to the console.
    """
    project = db.get_project(project_id)
    if protocol_run_id is None:
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name=f"setup-{project.id}",
            status=ProtocolStatus.PENDING,
            base_branch=project.base_branch,
            worktree_path=None,
            protocol_root=None,
            description="Project setup and bootstrap",
        )
        protocol_run_id = run.id

    db.update_protocol_status(protocol_run_id, ProtocolStatus.RUNNING)
    db.append_event(protocol_run_id, "setup_started", f"Onboarding {project.name}")

    try:
        repo_path = Path(project.git_url).expanduser()
        repo_preexisting = repo_path.exists()
        try:
            repo_path = ensure_local_repo(project.git_url, project.name)
        except FileNotFoundError:
            db.append_event(
                protocol_run_id,
                "setup_pending_clone",
                f"Repo path {project.git_url} not present locally. "
                "Set DEKSDENFLOW_AUTO_CLONE=true or clone manually before running setup.",
                metadata={"git_url": project.git_url, "projects_root": str(DEFAULT_PROJECTS_ROOT)},
            )
            db.update_protocol_status(protocol_run_id, ProtocolStatus.BLOCKED)
            db.append_event(protocol_run_id, "setup_blocked", "Setup blocked until repository is present.")
            return
        except Exception as exc:  # pragma: no cover - defensive
            db.append_event(
                protocol_run_id,
                "setup_clone_failed",
                f"Repo clone failed: {exc}",
                metadata={"git_url": project.git_url, "projects_root": str(DEFAULT_PROJECTS_ROOT)},
            )
            db.update_protocol_status(protocol_run_id, ProtocolStatus.BLOCKED)
            return

        if repo_path.exists() and not repo_preexisting:
            db.append_event(
                protocol_run_id,
                "setup_cloned",
                "Repository cloned for project setup.",
                metadata={"path": str(repo_path), "git_url": project.git_url},
            )

        try:
            ensure_assets(repo_path)
            db.append_event(
                protocol_run_id,
                "setup_assets",
                "Ensured starter assets (docs/prompts/CI scripts).",
                metadata={"path": str(repo_path)},
            )
        except Exception as exc:  # pragma: no cover - best effort
            db.append_event(
                protocol_run_id,
                "setup_warning",
                f"Skipped asset provisioning: {exc}",
                metadata={"path": str(repo_path)},
            )
        db.update_protocol_status(protocol_run_id, ProtocolStatus.COMPLETED)
        db.append_event(protocol_run_id, "setup_completed", "Project setup job finished.")
    except Exception as exc:  # pragma: no cover - defensive
        log.exception(
            "Project setup failed",
            extra={
                **log_extra(project_id=project_id, protocol_run_id=protocol_run_id),
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            },
        )
        db.update_protocol_status(protocol_run_id, ProtocolStatus.FAILED)
        db.append_event(protocol_run_id, "setup_failed", f"Setup failed: {exc}")
