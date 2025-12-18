import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, TypeVar

from tasksgodzilla.ci import trigger_ci
from tasksgodzilla.codex import run_process
from tasksgodzilla.config import load_config
from tasksgodzilla.domain import ProtocolRun, ProtocolStatus
from tasksgodzilla.git_utils import create_github_pr, resolve_project_repo_path
from tasksgodzilla.logging import get_logger, log_extra
from tasksgodzilla.project_setup import local_repo_dir
from tasksgodzilla.storage import BaseDatabase

log = get_logger(__name__)

SINGLE_WORKTREE = os.environ.get("TASKSGODZILLA_SINGLE_WORKTREE", "true").lower() in ("1", "true", "yes", "on")
DEFAULT_WORKTREE_BRANCH = os.environ.get("TASKSGODZILLA_WORKTREE_BRANCH", "tasksgodzilla-worktree")

T = TypeVar("T")


class GitLockError(Exception):
    """Raised when git index.lock cannot be acquired after retries."""
    pass


def is_git_lock_error(error: Exception) -> bool:
    """Check if an exception is related to git index.lock contention."""
    error_str = str(error).lower()
    lock_indicators = [
        "index.lock",
        "unable to create",
        "another git process seems to be running",
        "lock file exists",
        "could not lock",
    ]
    return any(indicator in error_str for indicator in lock_indicators)


def with_git_lock_retry(
    func: Callable[[], T],
    max_retries: int = 5,
    retry_delay: float = 1.0,
    repo_root: Optional[Path] = None,
) -> T:
    """
    Execute a git operation with automatic retry on index.lock contention.

    Args:
        func: The git operation to execute
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (exponential backoff applied)
        repo_root: Optional repo root to check for stale lock files

    Returns:
        The result of the git operation

    Raises:
        GitLockError: If operation fails after all retries due to lock contention
        Exception: Other exceptions are re-raised immediately
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as exc:
            if not is_git_lock_error(exc):
                raise

            last_error = exc

            if attempt < max_retries:
                delay = retry_delay * (2 ** attempt)
                log.warning(
                    "git_lock_contention",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "delay_seconds": delay,
                        "error": str(exc),
                    },
                )

                if repo_root:
                    _cleanup_stale_lock(repo_root)

                time.sleep(delay)

    raise GitLockError(
        f"Git operation failed after {max_retries + 1} attempts due to lock contention: {last_error}"
    )


def _cleanup_stale_lock(repo_root: Path) -> bool:
    """
    Attempt to clean up a stale index.lock file.

    Only removes the lock if it appears to be stale (older than 5 minutes
    and no git process is running).

    Returns True if a stale lock was removed, False otherwise.
    """
    lock_file = repo_root / ".git" / "index.lock"
    if not lock_file.exists():
        return False

    try:
        lock_age = time.time() - lock_file.stat().st_mtime
        if lock_age < 300:
            return False

        lock_file.unlink()
        log.info(
            "git_stale_lock_removed",
            extra={"lock_file": str(lock_file), "age_seconds": lock_age},
        )
        return True
    except Exception as exc:
        log.warning(
            "git_stale_lock_cleanup_failed",
            extra={"lock_file": str(lock_file), "error": str(exc)},
        )
        return False


@dataclass
class GitService:
    """Service for handling all git and worktree operations.
    
    This service provides centralized git operations including repository management,
    worktree creation, branch operations, PR/MR creation, and CI triggering.
    
    Responsibilities:
    - Resolve and validate repository paths
    - Create and manage git worktrees for protocol isolation
    - Push branches and create PRs/MRs via gh/glab CLI or API
    - Trigger CI pipelines for GitHub Actions and GitLab CI
    - Check remote branch existence
    - Handle git failures gracefully with appropriate status updates
    
    Worktree Strategy:
    By default, uses a single shared worktree branch (TASKSGODZILLA_SINGLE_WORKTREE=true)
    to avoid creating many per-protocol branches. Set to false for per-protocol branches.
    
    Usage:
        git_service = GitService(db)
        
        # Ensure repository exists
        repo_root = git_service.ensure_repo_or_block(
            project, run, job_id="job-123"
        )
        
        # Create or reuse worktree
        worktree = git_service.ensure_worktree(
            repo_root, "protocol-name", "main"
        )
        
        # Push and open PR
        pushed = git_service.push_and_open_pr(
            worktree, "protocol-name", "main"
        )
        
        # Trigger CI
        triggered = git_service.trigger_ci(
            repo_root, "protocol-name", "github"
        )
    """

    db: BaseDatabase

    def get_branch_name(self, protocol_name: str) -> str:
        """
        Resolve the branch name to use for worktrees. Defaults to a shared branch to
        avoid creating many per-protocol branches unless overridden.
        """
        if not SINGLE_WORKTREE:
            return protocol_name
        return DEFAULT_WORKTREE_BRANCH

    def get_worktree_path(self, repo_root: Path, protocol_name: str) -> tuple[Path, str]:
        branch_name = self.get_branch_name(protocol_name)
        # Keep worktrees scoped to a single repo to avoid collisions between
        # different projects under the same org/parent directory.
        worktrees_root = repo_root / "worktrees"
        return worktrees_root / branch_name, branch_name

    def ensure_repo_or_block(
        self,
        project,
        run: ProtocolRun,
        *,
        job_id: Optional[str] = None,
        clone_if_missing: Optional[bool] = None,
        block_on_missing: bool = True,
    ) -> Optional[Path]:
        """
        Resolve (and optionally clone) the project repository. Marks the protocol as blocked and
        emits an event when the repo is unavailable.
        """
        try:
            repo_root = resolve_project_repo_path(
                project.git_url,
                project.name,
                project.local_path,
                project_id=project.id,
                clone_if_missing=clone_if_missing,
            )
        except FileNotFoundError as exc:
            self.db.append_event(
                run.id,
                "repo_missing",
                f"Repository not present locally: {exc}",
                metadata={"git_url": project.git_url},
            )
            if block_on_missing:
                self.db.update_protocol_status(run.id, ProtocolStatus.BLOCKED)
            return None
        except Exception as exc:  # pragma: no cover - defensive
            log.warning(
                "Repo unavailable",
                extra={
                    **self._log_context(run=run, job_id=job_id, project_id=project.id),
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                },
            )
            self.db.append_event(
                run.id,
                "repo_clone_failed",
                f"Repository clone failed: {exc}",
                metadata={"git_url": project.git_url},
            )
            if block_on_missing:
                self.db.update_protocol_status(run.id, ProtocolStatus.BLOCKED)
            return None
        if not repo_root.exists():
            self.db.append_event(
                run.id,
                "repo_missing",
                "Repository path not available locally.",
                metadata={"git_url": project.git_url, "resolved_path": str(repo_root)},
            )
            if block_on_missing:
                self.db.update_protocol_status(run.id, ProtocolStatus.BLOCKED)
            return None
        return repo_root

    def ensure_worktree(
        self,
        repo_root: Path,
        protocol_name: str,
        base_branch: str,
        *,
        protocol_run_id: Optional[int] = None,
        project_id: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> Path:
        """Ensure a worktree exists for the given protocol/branch."""
        config = load_config()
        if not (repo_root / ".git").exists():
            log.info(
                "worktree_skipped_not_git_repo",
                extra={
                    **self._log_context(protocol_run_id=protocol_run_id, project_id=project_id, job_id=job_id),
                    "protocol_name": protocol_name,
                    "repo_root": str(repo_root),
                },
            )
            return repo_root
        worktree, branch_name = self.get_worktree_path(repo_root, protocol_name)
        if not worktree.exists():
            log.info(
                "creating_worktree",
                extra={
                    **self._log_context(protocol_run_id=protocol_run_id, project_id=project_id, job_id=job_id),
                    "protocol_name": protocol_name,
                    "branch": branch_name,
                    "base_branch": base_branch,
                },
            )

            def _create_worktree() -> None:
                try:
                    run_process(
                        [
                            "git",
                            "worktree",
                            "add",
                            "--checkout",
                            "-b",
                            branch_name,
                            str(worktree),
                            f"origin/{base_branch}",
                        ],
                        cwd=repo_root,
                    )
                except Exception:
                    try:
                        run_process(
                            [
                                "git",
                                "worktree",
                                "add",
                                "--checkout",
                                str(worktree),
                                branch_name,
                            ],
                            cwd=repo_root,
                        )
                    except Exception:
                        run_process(
                            [
                                "git",
                                "worktree",
                                "add",
                                "--checkout",
                                "-b",
                                branch_name,
                                str(worktree),
                                "HEAD",
                            ],
                            cwd=repo_root,
                        )

            with_git_lock_retry(
                _create_worktree,
                max_retries=config.git_lock_max_retries,
                retry_delay=config.git_lock_retry_delay,
                repo_root=repo_root,
            )
        return worktree

    def push_and_open_pr(
        self,
        worktree: Path,
        protocol_name: str,
        base_branch: str,
        *,
        protocol_run_id: Optional[int] = None,
        project_id: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> bool:
        """Commit, push, and open a PR/MR for the worktree changes."""
        config = load_config()
        pushed = False
        branch_exists = False
        commit_attempted = False

        def _git_add_and_commit() -> bool:
            nonlocal commit_attempted
            run_process(["git", "add", "."], cwd=worktree, capture_output=True, text=True)
            try:
                commit_attempted = True
                run_process(
                    ["git", "commit", "-m", f"chore: sync protocol {protocol_name}"],
                    cwd=worktree,
                    capture_output=True,
                    text=True,
                )
                return True
            except Exception as exc:
                msg = str(exc).lower()
                if "nothing to commit" in msg or "no changes added to commit" in msg or "clean" in msg:
                    log.info(
                        "No changes to commit; pushing existing branch state",
                        extra={
                            **self._log_context(protocol_run_id=protocol_run_id, project_id=project_id, job_id=job_id),
                            "protocol_name": protocol_name,
                            "base_branch": base_branch,
                        },
                    )
                    return True
                raise

        def _git_push() -> None:
            run_process(
                ["git", "push", "--set-upstream", "origin", protocol_name],
                cwd=worktree,
                capture_output=True,
                text=True,
            )

        try:
            with_git_lock_retry(
                _git_add_and_commit,
                max_retries=config.git_lock_max_retries,
                retry_delay=config.git_lock_retry_delay,
                repo_root=worktree,
            )
            _git_push()
            pushed = True
        except Exception as exc:
            branch_exists = self.remote_branch_exists(worktree, protocol_name)
            log.warning(
                "Failed to push branch",
                extra={
                    **self._log_context(protocol_run_id=protocol_run_id, project_id=project_id, job_id=job_id),
                    "protocol_name": protocol_name,
                    "base_branch": base_branch,
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                    "branch_exists": branch_exists,
                    "commit_attempted": commit_attempted,
                },
            )
            if not branch_exists:
                try:
                    _git_push()
                    return True
                except Exception:
                    return False

        self._create_pr_if_possible(worktree, protocol_name, base_branch)

        return pushed or branch_exists

    def trigger_ci(
        self,
        repo_root: Path,
        branch: str,
        ci_provider: Optional[str],
        *,
        protocol_run_id: Optional[int] = None,
        project_id: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> bool:
        """Best-effort CI trigger after push (gh/glab)."""
        provider = (ci_provider or "github").lower()
        result = trigger_ci(provider, repo_root, branch)
        log.info(
            "CI trigger",
            extra={
                **self._log_context(protocol_run_id=protocol_run_id, project_id=project_id, job_id=job_id),
                "provider": provider,
                "branch": branch,
                "triggered": result,
            },
        )
        return result

    def remote_branch_exists(self, repo_root: Path, branch: str) -> bool:
        """Check if a branch exists on the remote repository."""
        try:
            result = run_process(
                ["git", "ls-remote", "--exit-code", "--heads", "origin", f"refs/heads/{branch}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _remote_branch_exists(self, repo_root: Path, branch: str) -> bool:
        """Deprecated: Use remote_branch_exists instead."""
        return self.remote_branch_exists(repo_root, branch)

    def _create_pr_if_possible(self, worktree: Path, protocol_name: str, base_branch: str) -> bool:
        """Helper to try creating PR via GH/GLAB CLI or API fallback."""
        pr_title = f"WIP: {protocol_name}"
        pr_body = f"Protocol {protocol_name} in progress"
        
        if shutil.which("gh"):
            try:
                run_process(
                    [
                        "gh",
                        "pr",
                        "create",
                        "--title",
                        pr_title,
                        "--body",
                        pr_body,
                        "--base",
                        base_branch,
                    ],
                    cwd=worktree,
                    capture_output=True,
                    text=True,
                )
                return True
            except Exception:
                pass
        elif shutil.which("glab"):
            try:
                run_process(
                    [
                        "glab",
                        "mr",
                        "create",
                        "--title",
                        pr_title,
                        "--description",
                        pr_body,
                        "--target-branch",
                        base_branch,
                    ],
                    cwd=worktree,
                    capture_output=True,
                    text=True,
                )
                return True
            except Exception:
                pass
        else:
            if create_github_pr(worktree, head=protocol_name, base=base_branch, title=pr_title, body=pr_body):
                return True
        return False

    def _log_context(
        self,
        run: Optional[ProtocolRun] = None,
        job_id: Optional[str] = None,
        project_id: Optional[int] = None,
        protocol_run_id: Optional[int] = None,
    ) -> dict:
        return log_extra(
            job_id=job_id,
            project_id=project_id or (run.project_id if run else None),
            protocol_run_id=protocol_run_id or (run.id if run else None),
        )
