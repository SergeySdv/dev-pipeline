from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from devgodzilla.config import Config

REPO_MODE_MANAGED = "managed_clone"
REPO_MODE_EXTERNAL = "external_repo"
VALID_REPO_MODES = {REPO_MODE_MANAGED, REPO_MODE_EXTERNAL}
_APP_REPO_ROOT = Path(__file__).resolve().parents[2]


def normalize_storage_path(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    return str(Path(text).expanduser().resolve(strict=False))


def infer_repo_mode(repo_mode: str | None, local_path: str | None) -> str:
    if repo_mode in VALID_REPO_MODES:
        return repo_mode
    if (local_path or "").strip():
        return REPO_MODE_EXTERNAL
    return REPO_MODE_MANAGED


def project_repo_mode(project: Any) -> str:
    return infer_repo_mode(getattr(project, "repo_mode", None), getattr(project, "local_path", None))


def project_repo_slug(project: Any) -> str:
    git_url = str(getattr(project, "git_url", "") or "").strip()
    if git_url:
        slug = git_url.rstrip("/").split("/")[-1].removesuffix(".git")
        if slug:
            return slug
    name = str(getattr(project, "name", "") or "").strip()
    if not name:
        return "project"
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip("-._").lower()
    return slug or "project"


def _project_scope_suffix(project: Any) -> Path:
    project_id = getattr(project, "id", None)
    repo_slug = project_repo_slug(project)
    if project_id is None:
        return Path(repo_slug)
    return Path(str(project_id)) / repo_slug


def resolve_managed_repo_root(project: Any, config: Config) -> Path:
    override = normalize_storage_path(getattr(project, "managed_repo_root_override", None))
    if override:
        return Path(override)
    return config.projects_root


def resolve_effective_repo_path(project: Any, config: Config) -> Path | None:
    local_path = normalize_storage_path(getattr(project, "local_path", None))
    mode = project_repo_mode(project)
    if mode == REPO_MODE_EXTERNAL:
        return Path(local_path) if local_path else None
    if local_path:
        return Path(local_path)
    return resolve_managed_repo_root(project, config) / _project_scope_suffix(project)


def resolve_effective_worktrees_root(project: Any, config: Config) -> Path | None:
    override = normalize_storage_path(getattr(project, "worktrees_root_override", None))
    if override:
        return Path(override)
    repo_path = resolve_effective_repo_path(project, config)
    if config.worktrees_root:
        return config.worktrees_root / _project_scope_suffix(project)
    if repo_path is None:
        return None
    return repo_path / "worktrees"


def resolve_effective_artifacts_root(project: Any, config: Config) -> Path | None:
    override = normalize_storage_path(getattr(project, "artifacts_root_override", None))
    if override:
        return Path(override)
    if config.artifacts_root:
        return config.artifacts_root / _project_scope_suffix(project)
    return None


def project_storage_payload(project: Any, config: Config) -> dict[str, str | None]:
    repo_path = resolve_effective_repo_path(project, config)
    worktrees_root = resolve_effective_worktrees_root(project, config)
    artifacts_root = resolve_effective_artifacts_root(project, config)
    return {
        "repo_mode": project_repo_mode(project),
        "managed_repo_root_override": normalize_storage_path(
            getattr(project, "managed_repo_root_override", None)
        ),
        "worktrees_root_override": normalize_storage_path(
            getattr(project, "worktrees_root_override", None)
        ),
        "artifacts_root_override": normalize_storage_path(
            getattr(project, "artifacts_root_override", None)
        ),
        "effective_repo_path": str(repo_path) if repo_path else None,
        "effective_worktrees_root": str(worktrees_root) if worktrees_root else None,
        "effective_artifacts_root": str(artifacts_root) if artifacts_root else None,
    }


def validate_project_storage_settings(
    *,
    repo_mode: str | None,
    local_path: str | None,
    managed_repo_root_override: str | None,
    worktrees_root_override: str | None,
    artifacts_root_override: str | None,
    git_url: str | None,
    config: Config,
) -> list[str]:
    errors: list[str] = []
    mode = infer_repo_mode(repo_mode, local_path)
    normalized_local_path = normalize_storage_path(local_path)

    if repo_mode and repo_mode not in VALID_REPO_MODES:
        errors.append("repo_mode must be managed_clone or external_repo")

    def _check_override(name: str, value: str | None) -> None:
        normalized = normalize_storage_path(value)
        if not normalized:
            return
        candidate = Path(normalized)
        if candidate == _APP_REPO_ROOT or candidate.is_relative_to(_APP_REPO_ROOT):
            errors.append(f"{name} must not point inside the DevGodzilla app repo")

    _check_override("managed_repo_root_override", managed_repo_root_override)
    _check_override("worktrees_root_override", worktrees_root_override)
    _check_override("artifacts_root_override", artifacts_root_override)

    if mode == REPO_MODE_EXTERNAL:
        if not normalized_local_path:
            errors.append("local_path is required when repo_mode is external_repo")
        else:
            candidate = Path(normalized_local_path)
            if not candidate.exists():
                errors.append(f"existing repository path does not exist: {candidate}")
            elif not (candidate / ".git").exists():
                errors.append(f"existing repository path is not a git repository: {candidate}")
            allowed_roots = config.allowed_external_repo_roots
            if allowed_roots and not any(
                candidate == allowed_root or candidate.is_relative_to(allowed_root)
                for allowed_root in allowed_roots
            ):
                errors.append("existing repository path is outside allowed external repo roots")
    else:
        if not (git_url or "").strip():
            errors.append("git_url is required when repo_mode is managed_clone")

    return errors
