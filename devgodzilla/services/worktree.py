"""
Enhanced Worktree Management for Parallel Development.

Provides structured worktree operations for managing multiple development
branches in parallel with proper lifecycle management.
"""

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from devgodzilla.config import get_config
from devgodzilla.errors import GitCommandError
from devgodzilla.logging import get_logger
from devgodzilla.services.git import run_process, with_git_lock_retry

logger = get_logger(__name__)


@dataclass
class WorktreeInfo:
    """Information about a git worktree."""
    
    path: Path
    branch: str
    commit: str
    is_main: bool = False
    locked: bool = False
    prunable: bool = False
    
    @property
    def name(self) -> str:
        """Get the worktree directory name."""
        return self.path.name
    
    def age_days(self) -> float:
        """Get the age of the worktree in days based on last modification."""
        try:
            mtime = self.path.stat().st_mtime
            return (time.time() - mtime) / 86400
        except OSError:
            return 0.0


@dataclass
class WorktreeManager:
    """
    Manages git worktrees for parallel feature development.
    
    Provides structured operations for creating, listing, and cleaning up
    worktrees used during protocol runs and feature development.
    
    Example:
        manager = WorktreeManager(repo_path=Path("/path/to/repo"))
        
        # List all worktrees
        worktrees = manager.list_worktrees()
        
        # Create a new worktree
        worktree = manager.create_worktree(
            branch="feature-x",
            base_branch="main"
        )
        
        # Cleanup old worktrees
        removed = manager.cleanup_stale_worktrees(max_age_days=30)
    """
    
    repo_path: Path
    
    def __post_init__(self):
        """Validate repo path exists."""
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")
        if not (self.repo_path / ".git").exists() and not (self.repo_path / ".git").is_dir():
            # Check for bare repo or worktree
            try:
                result = run_process(
                    ["git", "rev-parse", "--git-common-dir"],
                    cwd=self.repo_path,
                    check=False,
                )
                if result.returncode != 0:
                    raise ValueError(f"Not a git repository: {self.repo_path}")
            except Exception:
                raise ValueError(f"Not a git repository: {self.repo_path}")
    
    def list_worktrees(self) -> List[WorktreeInfo]:
        """
        List all worktrees for the repository.
        
        Returns:
            List of WorktreeInfo objects for each worktree.
        """
        result = run_process(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.repo_path,
        )
        
        worktrees: List[WorktreeInfo] = []
        current_info: dict = {}
        
        for line in result.stdout.strip().splitlines():
            if line.startswith("worktree "):
                if current_info:
                    worktrees.append(self._build_worktree_info(current_info))
                current_info = {"path": Path(line.split(" ", 1)[1])}
            elif line.startswith("HEAD "):
                current_info["commit"] = line.split(" ", 1)[1]
            elif line.startswith("branch "):
                branch_ref = line.split(" ", 1)[1]
                # Extract branch name from refs/heads/branch-name
                if branch_ref.startswith("refs/heads/"):
                    current_info["branch"] = branch_ref.replace("refs/heads/", "")
                else:
                    current_info["branch"] = branch_ref
            elif line == "detached":
                current_info["branch"] = "DETACHED"
            elif line == "locked":
                current_info["locked"] = True
            elif line == "prunable":
                current_info["prunable"] = True
        
        # Don't forget the last one
        if current_info:
            worktrees.append(self._build_worktree_info(current_info))
        
        logger.debug(
            "worktree_list_complete",
            extra={"repo_path": str(self.repo_path), "count": len(worktrees)},
        )
        
        return worktrees
    
    def _build_worktree_info(self, info: dict) -> WorktreeInfo:
        """Build WorktreeInfo from parsed porcelain output."""
        path = info.get("path", Path())
        is_main = path == self.repo_path or path.resolve() == self.repo_path.resolve()
        
        return WorktreeInfo(
            path=path,
            branch=info.get("branch", "unknown"),
            commit=info.get("commit", ""),
            is_main=is_main,
            locked=info.get("locked", False),
            prunable=info.get("prunable", False),
        )
    
    def create_worktree(
        self, 
        branch: str, 
        path: Optional[Path] = None,
        base_branch: str = "main",
        *,
        force: bool = False,
    ) -> WorktreeInfo:
        """
        Create a new worktree for a branch.
        
        Args:
            branch: Name of the branch for the worktree
            path: Optional custom path for the worktree (auto-generated if not provided)
            base_branch: Base branch to create from (default: main)
            force: Force creation even if branch already exists
            
        Returns:
            WorktreeInfo for the created worktree
            
        Raises:
            GitCommandError: If worktree creation fails
        """
        config = get_config()
        
        # Auto-generate path if not provided
        if path is None:
            worktrees_root = self.repo_path / "worktrees"
            path = worktrees_root / branch
        
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "creating_worktree",
            extra={
                "repo_path": str(self.repo_path),
                "branch": branch,
                "path": str(path),
                "base_branch": base_branch,
            },
        )
        
        def _create() -> None:
            # Try creating with remote base first
            try:
                run_process(
                    [
                        "git", "worktree", "add", "--checkout",
                        "-b", branch, str(path),
                        f"origin/{base_branch}",
                    ],
                    cwd=self.repo_path,
                )
                return
            except subprocess.CalledProcessError:
                pass
            
            # Try with local base
            try:
                run_process(
                    [
                        "git", "worktree", "add", "--checkout",
                        "-b", branch, str(path), base_branch,
                    ],
                    cwd=self.repo_path,
                )
                return
            except subprocess.CalledProcessError:
                pass
            
            # If branch already exists, just checkout existing branch
            if not force:
                try:
                    run_process(
                        ["git", "worktree", "add", str(path), branch],
                        cwd=self.repo_path,
                    )
                    return
                except subprocess.CalledProcessError:
                    pass
            
            # Last resort: create from HEAD
            try:
                run_process(
                    [
                        "git", "worktree", "add", "--checkout",
                        "-b", branch, str(path), "HEAD",
                    ],
                    cwd=self.repo_path,
                )
            except subprocess.CalledProcessError as exc:
                raise GitCommandError(f"Failed to create worktree for {branch}: {exc}") from exc
        
        with_git_lock_retry(
            _create,
            max_retries=config.git_lock_max_retries,
            retry_delay=config.git_lock_retry_delay,
            repo_root=self.repo_path,
        )
        
        # Return the created worktree info
        worktrees = self.list_worktrees()
        for wt in worktrees:
            if wt.path.resolve() == path.resolve():
                return wt
        
        # Fallback: construct info manually
        return WorktreeInfo(
            path=path,
            branch=branch,
            commit=self._get_head_commit(path),
            is_main=False,
        )
    
    def _get_head_commit(self, worktree_path: Path) -> str:
        """Get the HEAD commit hash for a worktree."""
        result = run_process(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree_path,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    
    def remove_worktree(self, path: Path, force: bool = False) -> bool:
        """
        Remove a worktree.
        
        Args:
            path: Path to the worktree to remove
            force: Force removal even with uncommitted changes
            
        Returns:
            True if worktree was removed, False if it didn't exist
        """
        if not path.exists():
            return False
        
        logger.info(
            "removing_worktree",
            extra={"repo_path": str(self.repo_path), "worktree_path": str(path), "force": force},
        )
        
        args = ["git", "worktree", "remove"]
        if force:
            args.append("--force")
        args.append(str(path))
        
        result = run_process(args, cwd=self.repo_path, check=False)
        
        if result.returncode == 0:
            logger.info(
                "worktree_removed",
                extra={"repo_path": str(self.repo_path), "worktree_path": str(path)},
            )
            return True
        else:
            logger.warning(
                "worktree_remove_failed",
                extra={
                    "repo_path": str(self.repo_path),
                    "worktree_path": str(path),
                    "error": result.stderr,
                },
            )
            return False
    
    def cleanup_stale_worktrees(self, max_age_days: int = 30) -> List[Path]:
        """
        Remove stale worktrees that haven't been modified recently.
        
        Args:
            max_age_days: Maximum age in days before a worktree is considered stale
            
        Returns:
            List of paths to removed worktrees
        """
        removed: List[Path] = []
        worktrees = self.list_worktrees()
        
        for wt in worktrees:
            # Never remove the main worktree
            if wt.is_main:
                continue
            
            # Skip locked worktrees
            if wt.locked:
                continue
            
            # Check age
            try:
                mtime = wt.path.stat().st_mtime
                age_days = (time.time() - mtime) / 86400
                
                if age_days > max_age_days:
                    if self.remove_worktree(wt.path, force=True):
                        removed.append(wt.path)
            except OSError:
                # Worktree path doesn't exist or is inaccessible
                pass
        
        logger.info(
            "worktree_cleanup_complete",
            extra={
                "repo_path": str(self.repo_path),
                "removed_count": len(removed),
                "max_age_days": max_age_days,
            },
        )
        
        return removed
    
    def get_worktree_for_branch(self, branch: str) -> Optional[WorktreeInfo]:
        """
        Find worktree for a specific branch.
        
        Args:
            branch: Branch name to search for
            
        Returns:
            WorktreeInfo if found, None otherwise
        """
        worktrees = self.list_worktrees()
        
        for wt in worktrees:
            if wt.branch == branch:
                return wt
        
        return None
    
    def prune_worktrees(self) -> List[str]:
        """
        Prune stale worktree references from the repository.
        
        This removes administrative files for worktrees that have been
        deleted from the file system.
        
        Returns:
            List of pruned worktree paths (as strings)
        """
        result = run_process(
            ["git", "worktree", "prune", "-v"],
            cwd=self.repo_path,
            check=False,
        )
        
        pruned: List[str] = []
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                if line.startswith("Pruning"):
                    # Extract path from "Pruning 'path'"
                    path = line.split("'", 1)[1].rsplit("'", 1)[0]
                    pruned.append(path)
        
        logger.info(
            "worktree_prune_complete",
            extra={"repo_path": str(self.repo_path), "pruned_count": len(pruned)},
        )
        
        return pruned
    
    def get_active_branches(self) -> List[str]:
        """
        Get list of branches that have active worktrees.
        
        Returns:
            List of branch names with active worktrees
        """
        worktrees = self.list_worktrees()
        return [wt.branch for wt in worktrees if not wt.is_main]
    
    def is_worktree_path(self, path: Path) -> bool:
        """
        Check if a path is a worktree for this repository.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is a worktree for this repo
        """
        worktrees = self.list_worktrees()
        resolved_path = path.resolve()
        
        for wt in worktrees:
            if wt.path.resolve() == resolved_path:
                return True
        
        return False
    
    def move_worktree(self, old_path: Path, new_path: Path) -> bool:
        """
        Move a worktree to a new location.
        
        Args:
            old_path: Current worktree path
            new_path: New location for the worktree
            
        Returns:
            True if move was successful
        """
        if not old_path.exists():
            return False
        
        result = run_process(
            ["git", "worktree", "move", str(old_path), str(new_path)],
            cwd=self.repo_path,
            check=False,
        )
        
        if result.returncode == 0:
            logger.info(
                "worktree_moved",
                extra={
                    "repo_path": str(self.repo_path),
                    "old_path": str(old_path),
                    "new_path": str(new_path),
                },
            )
            return True
        
        logger.warning(
            "worktree_move_failed",
            extra={
                "repo_path": str(self.repo_path),
                "old_path": str(old_path),
                "new_path": str(new_path),
                "error": result.stderr,
            },
        )
        return False
    
    def lock_worktree(self, path: Path, reason: str = "") -> bool:
        """
        Lock a worktree to prevent accidental removal.
        
        Args:
            path: Path to the worktree
            reason: Optional reason for locking
            
        Returns:
            True if lock was successful
        """
        args = ["git", "worktree", "lock"]
        if reason:
            args.extend(["--reason", reason])
        args.append(str(path))
        
        result = run_process(args, cwd=self.repo_path, check=False)
        
        if result.returncode == 0:
            logger.info(
                "worktree_locked",
                extra={"repo_path": str(self.repo_path), "worktree_path": str(path)},
            )
            return True
        
        return False
    
    def unlock_worktree(self, path: Path) -> bool:
        """
        Unlock a worktree.
        
        Args:
            path: Path to the worktree
            
        Returns:
            True if unlock was successful
        """
        result = run_process(
            ["git", "worktree", "unlock", str(path)],
            cwd=self.repo_path,
            check=False,
        )
        
        return result.returncode == 0
