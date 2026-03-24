"""
Provider-specific pull request and merge request helpers.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx


@dataclass
class PRResult:
    """Result of a PR/MR creation operation."""

    provider: str
    pr_number: int
    pr_url: str
    status: str
    title: Optional[str] = None
    body: Optional[str] = None
    source_branch: Optional[str] = None
    target_branch: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "status": self.status,
            "title": self.title,
            "source_branch": self.source_branch,
            "target_branch": self.target_branch,
        }


class PRError(Exception):
    """Error during PR/MR creation."""


def create_github_pr_api(
    repo_root: Path,
    *,
    head: str,
    base: str,
    title: str,
    body: str,
    run_process: Callable[..., Any],
    github_token: Optional[str] = None,
) -> bool:
    """Create a GitHub PR via REST API."""
    owner_repo = parse_github_remote(repo_root, run_process=run_process)
    if not owner_repo:
        return False

    owner, repo = owner_repo
    gh_token = github_token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not gh_token:
        return False

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {
        "title": title,
        "head": head,
        "base": base,
        "body": body,
        "maintainer_can_modify": True,
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=30)
    except Exception:
        return False
    return response.status_code in (201, 422)


def parse_github_remote(
    repo_root: Path,
    *,
    run_process: Callable[..., Any],
) -> Optional[tuple[str, str]]:
    """Parse origin remote into (owner, repo) for GitHub URLs."""
    remote_url = _read_origin_remote(repo_root, run_process=run_process)
    if not remote_url or "github.com" not in remote_url:
        return None

    if remote_url.startswith("http"):
        parts = remote_url.split("github.com/", 1)[-1]
    elif remote_url.startswith("git@"):
        parts = remote_url.split(":", 1)[-1]
    else:
        return None

    owner_repo_parts = parts.rstrip("/").removesuffix(".git").split("/")
    if len(owner_repo_parts) < 2:
        return None
    owner, repo = owner_repo_parts[0], owner_repo_parts[1]
    if not owner or not repo:
        return None
    return owner, repo


def parse_gitlab_url(git_url: str) -> Optional[tuple[str, str]]:
    """Parse GitLab URL into (instance_url, encoded_project_path)."""
    if "gitlab" not in git_url:
        return None

    if git_url.startswith("https://") or git_url.startswith("http://"):
        match = re.match(r"(https?://[^/]+)/(.+?)(?:\.git)?/?$", git_url)
        if match:
            instance_url = match.group(1)
            project_path = match.group(2).rstrip("/")
            return instance_url, project_path.replace("/", "%2F")

    if git_url.startswith("git@"):
        match = re.match(r"git@([^:]+):(.+?)(?:\.git)?$", git_url)
        if match:
            domain = match.group(1)
            project_path = match.group(2)
            return f"https://{domain}", project_path.replace("/", "%2F")

    return None


def parse_gitlab_remote(
    repo_root: Path,
    *,
    run_process: Callable[..., Any],
) -> Optional[tuple[str, str]]:
    """Parse origin remote into (instance_url, encoded_project_path) for GitLab."""
    remote_url = _read_origin_remote(repo_root, run_process=run_process)
    if not remote_url:
        return None
    return parse_gitlab_url(remote_url)


async def resolve_gitlab_users(
    client: httpx.AsyncClient,
    gitlab_url: str,
    token: str,
    usernames: Optional[List[str]],
    *,
    logger: Any,
) -> List[int]:
    """Resolve GitLab usernames to user IDs."""
    if not usernames:
        return []

    user_ids: List[int] = []
    for username in usernames:
        try:
            response = await client.get(
                f"{gitlab_url}/api/v4/users",
                headers={"PRIVATE-TOKEN": token},
                params={"username": username},
            )
        except Exception as exc:
            logger.warning(
                "gitlab_user_resolve_failed",
                extra={"username": username, "error": str(exc)},
            )
            continue

        if response.status_code == 200:
            users = response.json()
            if users:
                user_ids.append(users[0]["id"])

    return user_ids


def detect_git_provider(
    repo_root: Path,
    *,
    run_process: Callable[..., Any],
) -> str:
    """Detect the Git provider for a repository."""
    remote_url = (_read_origin_remote(repo_root, run_process=run_process) or "").lower()
    if "github.com" in remote_url:
        return "github"
    if "gitlab" in remote_url:
        return "gitlab"
    if "bitbucket" in remote_url:
        return "bitbucket"
    return "unknown"


async def open_gitlab_mr(
    repo_root: Path,
    title: str,
    body: str,
    source_branch: str,
    target_branch: str = "main",
    draft: bool = False,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
    milestone_id: Optional[int] = None,
    remove_source_branch: bool = True,
    squash: bool = False,
    *,
    gitlab_token: Optional[str] = None,
    run_process: Callable[..., Any],
    logger: Any,
) -> PRResult:
    """Open a GitLab merge request via API."""
    parsed = parse_gitlab_remote(repo_root, run_process=run_process)
    if not parsed:
        raise PRError("Not a GitLab repository or could not parse URL")

    gitlab_url, project_path = parsed
    token = gitlab_token or os.environ.get("GITLAB_TOKEN")
    if not token:
        raise PRError(
            "No GitLab token found. Set GITLAB_TOKEN environment variable or pass gitlab_token parameter."
        )

    mr_title = f"Draft: {title}" if draft else title
    payload: Dict[str, Any] = {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": mr_title,
        "description": body,
        "remove_source_branch": remove_source_branch,
        "squash": squash,
    }
    if labels:
        payload["labels"] = ",".join(labels)
    if milestone_id:
        payload["milestone_id"] = milestone_id

    logger.info(
        "creating_gitlab_mr",
        extra={
            "gitlab_url": gitlab_url,
            "project_path": project_path,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "draft": draft,
        },
    )

    async with httpx.AsyncClient(timeout=30) as client:
        if assignees:
            assignee_ids = await resolve_gitlab_users(
                client,
                gitlab_url,
                token,
                assignees,
                logger=logger,
            )
            if assignee_ids:
                payload["assignee_ids"] = assignee_ids

        response = await client.post(
            f"{gitlab_url}/api/v4/projects/{project_path}/merge_requests",
            headers={"PRIVATE-TOKEN": token},
            json=payload,
        )

        if response.status_code in (200, 201):
            return _gitlab_created_result(
                response.json(),
                title=title,
                body=body,
                source_branch=source_branch,
                target_branch=target_branch,
                draft=draft,
                logger=logger,
            )
        if response.status_code == 409:
            return await _existing_gitlab_mr(
                client,
                gitlab_url=gitlab_url,
                project_path=project_path,
                token=token,
                source_branch=source_branch,
                target_branch=target_branch,
                logger=logger,
            )

        error_detail = response.text
        logger.error(
            "gitlab_mr_creation_failed",
            extra={"status_code": response.status_code, "error": error_detail},
        )
        raise PRError(f"GitLab MR creation failed (status {response.status_code}): {error_detail}")


async def open_pr_async(
    repo_root: Path,
    title: str,
    body: str,
    source_branch: str,
    target_branch: str = "main",
    draft: bool = False,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
    *,
    run_process: Callable[..., Any],
    logger: Any,
) -> PRResult:
    """Open a PR/MR using the detected provider."""
    provider = detect_git_provider(repo_root, run_process=run_process)
    if provider == "gitlab":
        return await open_gitlab_mr(
            repo_root=repo_root,
            title=title,
            body=body,
            source_branch=source_branch,
            target_branch=target_branch,
            draft=draft,
            labels=labels,
            assignees=assignees,
            run_process=run_process,
            logger=logger,
        )
    if provider == "github":
        return await open_github_pr_async(
            repo_root=repo_root,
            title=title,
            body=body,
            head=source_branch,
            base=target_branch,
            draft=draft,
            labels=labels,
            assignees=assignees,
            run_process=run_process,
            logger=logger,
        )
    raise PRError(f"Unsupported Git provider: {provider}")


async def open_github_pr_async(
    repo_root: Path,
    title: str,
    body: str,
    head: str,
    base: str = "main",
    draft: bool = False,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
    *,
    run_process: Callable[..., Any],
    logger: Any,
) -> PRResult:
    """Open a GitHub pull request via API."""
    owner_repo = parse_github_remote(repo_root, run_process=run_process)
    if not owner_repo:
        raise PRError("Not a GitHub repository or could not parse URL")

    owner, repo = owner_repo
    gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not gh_token:
        raise PRError("No GitHub token found. Set GITHUB_TOKEN or GH_TOKEN environment variable.")

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
    }
    payload: Dict[str, Any] = {
        "title": title,
        "head": head,
        "base": base,
        "body": body,
        "draft": draft,
        "maintainer_can_modify": True,
    }

    logger.info(
        "creating_github_pr",
        extra={"owner": owner, "repo": repo, "head": head, "base": base, "draft": draft},
    )

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            return await _created_github_pr(
                client,
                response.json(),
                owner=owner,
                repo=repo,
                headers=headers,
                title=title,
                body=body,
                head=head,
                base=base,
                draft=draft,
                labels=labels,
                assignees=assignees,
                logger=logger,
            )
        if response.status_code == 422:
            return await _existing_github_pr(
                client,
                owner=owner,
                repo=repo,
                head=head,
                base=base,
                headers=headers,
                logger=logger,
            )

        error_detail = response.text
        logger.error(
            "github_pr_creation_failed",
            extra={"status_code": response.status_code, "error": error_detail},
        )
        raise PRError(f"GitHub PR creation failed (status {response.status_code}): {error_detail}")


def _read_origin_remote(repo_root: Path, *, run_process: Callable[..., Any]) -> Optional[str]:
    try:
        result = run_process(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_root,
            check=False,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    remote_url = (result.stdout or "").strip()
    return remote_url or None


def _gitlab_created_result(
    data: dict[str, Any],
    *,
    title: str,
    body: str,
    source_branch: str,
    target_branch: str,
    draft: bool,
    logger: Any,
) -> PRResult:
    logger.info(
        "gitlab_mr_created",
        extra={"mr_iid": data["iid"], "mr_url": data["web_url"]},
    )
    return PRResult(
        provider="gitlab",
        pr_number=data["iid"],
        pr_url=data["web_url"],
        status="draft" if draft else "open",
        title=title,
        body=body,
        source_branch=source_branch,
        target_branch=target_branch,
    )


async def _existing_gitlab_mr(
    client: httpx.AsyncClient,
    *,
    gitlab_url: str,
    project_path: str,
    token: str,
    source_branch: str,
    target_branch: str,
    logger: Any,
) -> PRResult:
    logger.info(
        "gitlab_mr_exists",
        extra={"source_branch": source_branch, "target_branch": target_branch},
    )
    list_response = await client.get(
        f"{gitlab_url}/api/v4/projects/{project_path}/merge_requests",
        headers={"PRIVATE-TOKEN": token},
        params={
            "source_branch": source_branch,
            "target_branch": target_branch,
            "state": "opened",
        },
    )
    if list_response.status_code == 200:
        mrs = list_response.json()
        if mrs:
            existing = mrs[0]
            return PRResult(
                provider="gitlab",
                pr_number=existing["iid"],
                pr_url=existing["web_url"],
                status="draft" if existing.get("draft", False) else "open",
                title=existing.get("title"),
                source_branch=source_branch,
                target_branch=target_branch,
            )
    raise PRError("GitLab MR already exists but could not retrieve it")


async def _created_github_pr(
    client: httpx.AsyncClient,
    data: dict[str, Any],
    *,
    owner: str,
    repo: str,
    headers: dict[str, str],
    title: str,
    body: str,
    head: str,
    base: str,
    draft: bool,
    labels: Optional[List[str]],
    assignees: Optional[List[str]],
    logger: Any,
) -> PRResult:
    pr_number = data["number"]
    pr_url = data["html_url"]
    if labels or assignees:
        issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}"
        issue_payload: Dict[str, Any] = {}
        if labels:
            issue_payload["labels"] = labels
        if assignees:
            issue_payload["assignees"] = assignees
        await client.patch(issue_url, headers=headers, json=issue_payload)

    logger.info(
        "github_pr_created",
        extra={"pr_number": pr_number, "pr_url": pr_url},
    )
    return PRResult(
        provider="github",
        pr_number=pr_number,
        pr_url=pr_url,
        status="draft" if draft else "open",
        title=title,
        body=body,
        source_branch=head,
        target_branch=base,
    )


async def _existing_github_pr(
    client: httpx.AsyncClient,
    *,
    owner: str,
    repo: str,
    head: str,
    base: str,
    headers: dict[str, str],
    logger: Any,
) -> PRResult:
    logger.info("github_pr_exists", extra={"head": head, "base": base})
    list_response = await client.get(
        f"https://api.github.com/repos/{owner}/{repo}/pulls",
        headers=headers,
        params={"head": f"{owner}:{head}", "state": "open"},
    )
    if list_response.status_code == 200:
        prs = list_response.json()
        if prs:
            existing = prs[0]
            return PRResult(
                provider="github",
                pr_number=existing["number"],
                pr_url=existing["html_url"],
                status="draft" if existing.get("draft", False) else "open",
                title=existing.get("title"),
                source_branch=head,
                target_branch=base,
            )
    raise PRError("GitHub PR already exists but could not retrieve it")
