#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from deksdenflow.project_setup import (  # noqa: E402
    BASE_FILES,
    PLACEHOLDER,
    clone_repo,
    ensure_assets,
    ensure_base_branch,
    ensure_git_repo,
    ensure_remote_origin,
    run_codex_discovery,
)
from deksdenflow.config import load_config  # noqa: E402
from deksdenflow.logging import init_cli_logging  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare an existing or new project with DeksdenFlow_Ilyas_Edition_1.0 starter assets.",
    )
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch name (default: main).",
    )
    parser.add_argument(
        "--init-if-needed",
        action="store_true",
        help="Initialize git repo if not already initialized.",
    )
    parser.add_argument(
        "--clone-url",
        help="Optional: git clone this repository before preparing assets.",
    )
    parser.add_argument(
        "--clone-dir",
        help="Optional: directory name for clone (default: repo name from URL).",
    )
    parser.add_argument(
        "--run-discovery",
        action="store_true",
        help="Run Codex-driven repository discovery/config prep (requires codex CLI).",
    )
    parser.add_argument(
        "--discovery-model",
        help="Model for discovery (default from PROTOCOL_DISCOVERY_MODEL or gpt-5.1-codex-max).",
    )
    return parser.parse_args()


def main() -> None:
    config = load_config()
    init_cli_logging(config.log_level)
    args = parse_args()

    repo_root: Path
    if args.clone_url:
        default_dir = (
            Path(args.clone_dir)
            if args.clone_dir
            else Path(args.clone_url.rstrip("/").split("/")[-1].replace(".git", ""))
        )
        repo_root = clone_repo(args.clone_url, default_dir.resolve())
    else:
        repo_root = ensure_git_repo(args.base_branch, args.init_if_needed)

    # Ensure subsequent commands operate inside the repo
    os.chdir(repo_root)
    repo_root = Path(os.getcwd())

    ensure_remote_origin(repo_root)
    ensure_base_branch(repo_root, args.base_branch)
    ensure_assets(repo_root)

    if args.run_discovery:
        discovery_model = args.discovery_model or os.environ.get("PROTOCOL_DISCOVERY_MODEL", "gpt-5.1-codex-max")
        run_codex_discovery(repo_root, discovery_model)

    print("Project setup completed. Review any placeholders and customize CI scripts for your stack.")


if __name__ == "__main__":
    main()
