from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import HTTPException

from devgodzilla.api import schemas
from devgodzilla.db.database import Database
from devgodzilla.services.base import ServiceContext


def project_github_token(project: Any) -> Optional[str]:
    token = ((getattr(project, "secrets", None) or {}).get("github_token") or "").strip()
    return token or None


def parse_github_owner_repo_from_url(git_url: Optional[str]) -> Optional[tuple[str, str]]:
    url = (git_url or "").strip()
    if not url or "github.com" not in url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        tail = url.split("github.com/", 1)[-1]
    elif url.startswith("git@"):
        tail = url.split(":", 1)[-1]
    elif url.startswith("ssh://git@"):
        tail = url.split("github.com/", 1)[-1]
    else:
        return None
    parts = tail.rstrip("/").removesuffix(".git").split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def project_github_owner_repo(repo_path: Path, project: Any) -> Optional[tuple[str, str]]:
    from devgodzilla.services.git import run_process

    remote_url = (project.git_url or "").strip()
    result = run_process(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=repo_path,
        check=False,
    )
    if result.returncode == 0 and (result.stdout or "").strip():
        remote_url = (result.stdout or "").strip()
    return parse_github_owner_repo_from_url(remote_url)


def require_project_repo_path(project: Any) -> Path:
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local repository path")

    repo_path = Path(project.local_path).expanduser()
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail="Project repository path does not exist")
    if not (repo_path / ".git").exists():
        raise HTTPException(status_code=400, detail="Project path is not a git repository")
    return repo_path


def existing_project_repo_path(project: Any) -> Optional[Path]:
    if not project.local_path:
        return None
    repo_path = Path(project.local_path).expanduser()
    if not repo_path.exists() or not (repo_path / ".git").exists():
        return None
    return repo_path


def _github_headers(github_token: Optional[str]) -> Optional[dict[str, str]]:
    token = (github_token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def _github_pr_check_status(item: dict[str, Any]) -> str:
    if item.get("draft"):
        return "draft"
    return "unknown"


def list_github_pulls(owner: str, repo: str, *, github_token: Optional[str]) -> list[schemas.PullRequestOut]:
    headers = _github_headers(github_token)
    if headers is None:
        return []
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    try:
        response = httpx.get(
            url,
            headers=headers,
            params={"state": "open", "per_page": 100},
            timeout=30,
        )
    except Exception:
        return []
    if response.status_code != 200:
        return []
    pulls: list[schemas.PullRequestOut] = []
    for item in response.json():
        pulls.append(
            schemas.PullRequestOut(
                id=str(item.get("number", "")),
                title=item.get("title", ""),
                branch=((item.get("head") or {}).get("ref") or ""),
                status="draft" if item.get("draft") else (item.get("state", "open") or "open").lower(),
                checks=_github_pr_check_status(item),
                url=item.get("html_url", ""),
                author=((item.get("user") or {}).get("login") or ""),
                created_at=item.get("created_at", ""),
            )
        )
    return pulls


def list_project_branches_for_repo(project: Any, ctx: ServiceContext) -> list[schemas.BranchOut]:
    from devgodzilla.services.git import GitService

    repo_path = require_project_repo_path(project)
    git_service = GitService(ctx)
    github_token = project_github_token(project)
    branches = _list_local_branches(repo_path)
    local_branch_names = {branch.name for branch in branches if not branch.is_remote}
    branches.extend(_list_remote_branches(repo_path, git_service, github_token, local_branch_names))
    return branches


def _list_local_branches(repo_path: Path) -> list[schemas.BranchOut]:
    from devgodzilla.services.git import run_process

    try:
        result = run_process(
            ["git", "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads/"],
            cwd=repo_path,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to list local branches: {exc}") from exc

    branches: list[schemas.BranchOut] = []
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        branches.append(
            schemas.BranchOut(
                name=parts[0],
                sha=parts[1],
                is_remote=False,
            )
        )
    return branches


def _list_remote_branches(
    repo_path: Path,
    git_service: Any,
    github_token: Optional[str],
    local_branch_names: set[str],
) -> list[schemas.BranchOut]:
    from devgodzilla.services.git import run_process

    try:
        result = run_process(
            ["git", "ls-remote", "--heads", "origin"],
            cwd=repo_path,
            check=False,
            env=git_service.build_repo_remote_git_env(repo_path, github_token),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to list remote branches: {exc}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").lower()
        if (
            "no such remote" in stderr
            or "could not read from remote repository" in stderr
            or "could not read username" in stderr
            or "authentication failed" in stderr
        ):
            return []
        message = (result.stderr or result.stdout or "").strip()
        raise HTTPException(status_code=502, detail=f"Failed to list remote branches: {message}")

    branches: list[schemas.BranchOut] = []
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) < 2 or not parts[1].startswith("refs/heads/"):
            continue
        branch_name = parts[1].replace("refs/heads/", "")
        if branch_name in local_branch_names:
            continue
        branches.append(
            schemas.BranchOut(
                name=branch_name,
                sha=parts[0],
                is_remote=True,
            )
        )
    return branches


def create_project_branch_in_repo(
    project: Any,
    *,
    branch_name: str,
    base_ref: Optional[str],
    checkout: bool,
    push: bool,
) -> tuple[str, str]:
    from devgodzilla.services.git import run_process

    repo_path = require_project_repo_path(project)
    cleaned_branch_name = (branch_name or "").strip()
    if not cleaned_branch_name:
        raise HTTPException(status_code=400, detail="Branch name is required")

    ref_check = run_process(
        ["git", "check-ref-format", "--branch", cleaned_branch_name],
        cwd=repo_path,
        check=False,
    )
    if ref_check.returncode != 0:
        raise HTTPException(status_code=400, detail="Invalid branch name")

    resolved_base_ref = (base_ref or project.base_branch or "main").strip()
    base_commit = resolve_branch_base_commit(repo_path, resolved_base_ref)
    if base_commit is None:
        raise HTTPException(status_code=400, detail=f"Base ref not found: {resolved_base_ref}")

    exists_res = run_process(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{cleaned_branch_name}"],
        cwd=repo_path,
        check=False,
    )
    if exists_res.returncode == 0:
        raise HTTPException(status_code=409, detail=f"Branch already exists: {cleaned_branch_name}")

    run_process(["git", "branch", cleaned_branch_name, base_commit], cwd=repo_path, check=True)
    if checkout:
        run_process(["git", "checkout", cleaned_branch_name], cwd=repo_path, check=True)
    if push:
        run_process(["git", "push", "-u", "origin", cleaned_branch_name], cwd=repo_path, check=True)

    return cleaned_branch_name, base_commit


def resolve_branch_base_commit(repo_path: Path, base_ref: str) -> Optional[str]:
    from devgodzilla.services.git import run_process

    for candidate in (base_ref, f"origin/{base_ref}"):
        result = run_process(
            ["git", "rev-parse", "--verify", f"{candidate}^{{commit}}"],
            cwd=repo_path,
            check=False,
        )
        if result.returncode == 0:
            return candidate
    return None


def list_project_pulls_for_repo(project: Any) -> list[schemas.PullRequestOut]:
    repo_path = existing_project_repo_path(project)
    if repo_path is None:
        return []

    github_token = project_github_token(project)
    pulls_from_cli = _list_project_pulls_via_gh(repo_path, github_token)
    if pulls_from_cli is not None:
        return pulls_from_cli

    owner_repo = project_github_owner_repo(repo_path, project)
    if owner_repo is None:
        return []
    owner, repo = owner_repo
    return list_github_pulls(owner, repo, github_token=github_token)


def _list_project_pulls_via_gh(repo_path: Path, github_token: Optional[str]) -> Optional[list[schemas.PullRequestOut]]:
    from devgodzilla.services.git import run_process

    try:
        result = run_process(
            ["gh", "pr", "list", "--json", "number,title,headRefName,state,author,url,createdAt,statusCheckRollup"],
            cwd=repo_path,
            check=False,
            env={**os.environ, **({"GH_TOKEN": github_token, "GITHUB_TOKEN": github_token} if github_token else {})},
        )
    except FileNotFoundError:
        return None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to list pull requests: {exc}") from exc

    if result.returncode != 0:
        return None
    if not result.stdout.strip():
        return []

    try:
        pr_data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to parse GitHub PR response: {exc}") from exc

    return [_pull_from_gh_cli_payload(item) for item in pr_data]


def _pull_from_gh_cli_payload(item: dict[str, Any]) -> schemas.PullRequestOut:
    checks = "unknown"
    if item.get("statusCheckRollup"):
        check_statuses = [status.get("conclusion") or status.get("state") for status in item["statusCheckRollup"]]
        if all(state in ("SUCCESS", "success", "COMPLETED") for state in check_statuses if state):
            checks = "passing"
        elif any(state in ("FAILURE", "failure", "FAILED") for state in check_statuses if state):
            checks = "failing"
        elif any(state in ("PENDING", "pending", "IN_PROGRESS", "QUEUED") for state in check_statuses if state):
            checks = "pending"

    return schemas.PullRequestOut(
        id=str(item.get("number", "")),
        title=item.get("title", ""),
        branch=item.get("headRefName", ""),
        status=item.get("state", "open").lower(),
        checks=checks,
        url=item.get("url", ""),
        author=item.get("author", {}).get("login", "") if isinstance(item.get("author"), dict) else "",
        created_at=item.get("createdAt", ""),
    )


def list_project_worktrees_for_repo(
    project_id: int,
    project: Any,
    db: Database,
) -> list[schemas.WorktreeOut]:
    repo_path = existing_project_repo_path(project)
    if repo_path is None:
        return []

    try:
        protocols = db.list_protocol_runs(project_id=project_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load protocol runs: {exc}") from exc

    worktree_paths = list_git_worktree_paths(repo_path)
    pulls_by_branch = {
        pull.branch: pull
        for pull in list_project_pulls_for_repo(project)
        if pull.branch
    }

    worktrees: list[schemas.WorktreeOut] = []
    for branch_name, protocol in protocol_branch_map(protocols).items():
        last_sha, last_message, last_date = branch_last_commit(repo_path, branch_name)
        pull = pulls_by_branch.get(branch_name)
        worktrees.append(
            schemas.WorktreeOut(
                branch_name=branch_name,
                worktree_path=worktree_paths.get(branch_name) or protocol.worktree_path,
                protocol_run_id=protocol.id,
                protocol_name=protocol.protocol_name,
                protocol_status=protocol.status,
                spec_run_id=None,
                last_commit_sha=last_sha,
                last_commit_message=last_message,
                last_commit_date=last_date,
                pr_url=pull.url if pull is not None else None,
            )
        )
    return worktrees


def list_git_worktree_paths(repo_path: Path) -> dict[str, str]:
    from devgodzilla.services.git import run_process

    try:
        result = run_process(
            ["git", "worktree", "list", "--porcelain"],
            cwd=repo_path,
            check=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to list git worktrees: {exc}") from exc

    if result.returncode != 0:
        return {}

    worktree_paths: dict[str, str] = {}
    current_worktree: Optional[str] = None
    for line in result.stdout.strip().splitlines():
        if line.startswith("worktree "):
            current_worktree = line.split(" ", 1)[1]
            continue
        if line.startswith("branch refs/heads/") and current_worktree:
            branch_name = line.replace("branch refs/heads/", "")
            worktree_paths[branch_name] = current_worktree
            current_worktree = None
    return worktree_paths


def protocol_branch_map(protocols: list[Any]) -> dict[str, Any]:
    return {
        protocol.protocol_name: protocol
        for protocol in protocols
        if getattr(protocol, "protocol_name", None)
    }


def branch_last_commit(repo_path: Path, branch_name: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    from devgodzilla.services.git import run_process

    try:
        result = run_process(
            ["git", "log", "-1", "--format=%H|%s|%ar", branch_name],
            cwd=repo_path,
            check=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to read branch commit for {branch_name}: {exc}") from exc

    if result.returncode != 0 or not result.stdout.strip():
        return None, None, None

    parts = result.stdout.strip().split("|", 2)
    if len(parts) < 3:
        return None, None, None
    return parts[0], parts[1], parts[2]
