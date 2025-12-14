#!/usr/bin/env python3
"""
Unified onboarding helper: clone/prepare a repo, run discovery, and register the project
in the local TasksGodzilla database (no ProtocolSpec generation).
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tasksgodzilla.config import load_config
from tasksgodzilla.domain import ProtocolStatus
from tasksgodzilla.logging import EXIT_RUNTIME_ERROR, get_logger, init_cli_logging, json_logging_from_env
from tasksgodzilla.project_setup import ensure_assets, ensure_local_repo, run_codex_discovery
from tasksgodzilla.storage import create_database

log = get_logger(__name__)


def parse_json_arg(value: Optional[str]) -> Optional[dict]:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc


def default_project_name(source: str) -> str:
    tail = source.rstrip("/").split("/")[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    return tail or "project"


def run_discovery(repo_root: Path, model: Optional[str], skip: bool) -> None:
    if skip:
        log.info("Skipping Codex discovery (--skip-discovery).")
        return
    discovery_model = model or os.environ.get("PROTOCOL_DISCOVERY_MODEL", "zai-coding-plan/glm-4.6")
    try:
        run_codex_discovery(repo_root, discovery_model, use_pipeline=True)
    except FileNotFoundError as exc:
        log.warning("Discovery skipped: %s", exc)
    except Exception as exc:  # pragma: no cover - best effort
        log.warning("Discovery failed: %s", exc)


def register_project(
    *,
    name: str,
    git_url: str,
    base_branch: str,
    ci_provider: Optional[str],
    default_models: Optional[dict],
    local_path: Path,
) -> dict:
    config = load_config()
    db = create_database(db_path=config.db_path, db_url=config.db_url, pool_size=config.db_pool_size)
    db.init_schema()

    project = db.create_project(
        name=name,
        git_url=git_url,
        base_branch=base_branch,
        ci_provider=ci_provider,
        default_models=default_models,
        local_path=str(local_path),
    )
    protocol_name = f"setup-{project.id}"
    run = db.create_protocol_run(
        project_id=project.id,
        protocol_name=protocol_name,
        status=ProtocolStatus.RUNNING,
        base_branch=base_branch,
        worktree_path=None,
        protocol_root=None,
        description="Project onboarded via scripts/onboard_repo.py",
        template_config=None,
        template_source=None,
    )

    # No ProtocolSpec persistence; onboarding is considered complete once discovery/assets are done.
    db.update_protocol_status(run.id, ProtocolStatus.COMPLETED)
    db.append_event(protocol_run_id=run.id, event_type="setup_completed", message="Onboarding completed (no ProtocolSpec persisted).")

    return {
        "project": project,
        "protocol_run": run,
        "repo_path": str(local_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Onboard a GitHub/GitLab/local repo: clone, discovery, and project registration (no ProtocolSpec).",
    )
    parser.add_argument("--git-url", required=True, help="Git URL or local path to the repo.")
    parser.add_argument("--name", help="Project name (default: derived from git URL/path).")
    parser.add_argument("--base-branch", default="main", help="Base branch name (default: main).")
    parser.add_argument("--ci-provider", choices=["github", "gitlab"], default=None, help="CI provider hint.")
    parser.add_argument("--default-models", help='JSON string of default models, e.g. {"planning":"zai-coding-plan/glm-4.6"}.')
    parser.add_argument(
        "--discovery-model",
        help="Model for discovery (default PROTOCOL_DISCOVERY_MODEL or zai-coding-plan/glm-4.6).",
    )
    parser.add_argument("--skip-discovery", action="store_true", help="Skip Codex repository discovery.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    init_cli_logging(config.log_level, json_output=json_logging_from_env())

    project_name = args.name or default_project_name(args.git_url)
    try:
        default_models = parse_json_arg(args.default_models)
    except ValueError as exc:
        log.error(str(exc))
        sys.exit(EXIT_RUNTIME_ERROR)

    try:
        repo_root = ensure_local_repo(args.git_url, project_name, project_id=None)
        ensure_assets(repo_root)
        run_discovery(repo_root, args.discovery_model, args.skip_discovery)
        result = register_project(
            name=project_name,
            git_url=args.git_url,
            base_branch=args.base_branch,
            ci_provider=args.ci_provider,
            default_models=default_models,
            local_path=repo_root,
        )
    except Exception as exc:  # pragma: no cover - CLI surface
        log.error("Onboarding failed: %s", exc)
        sys.exit(EXIT_RUNTIME_ERROR)

    print(f"Project {result['project'].id} onboarded at {result['repo_path']}.")
    print(f"Setup run: {result['protocol_run'].protocol_name} (status=completed, spec=skipped)")


if __name__ == "__main__":
    main()
