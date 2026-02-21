#!/usr/bin/env python3
"""
Trigger CI pipelines for a branch via GitHub/GitLab CLIs.

Active implementation backed by `devgodzilla.services.git.GitService`.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from devgodzilla.config import load_config  # noqa: E402
from devgodzilla.logging import EXIT_RUNTIME_ERROR, init_cli_logging, json_logging_from_env  # noqa: E402
from devgodzilla.services.base import ServiceContext  # noqa: E402
from devgodzilla.services.git import GitService  # noqa: E402


def main() -> None:
    config = load_config()
    init_cli_logging(config.log_level, json_output=json_logging_from_env())

    parser = argparse.ArgumentParser(description="Trigger CI for a protocol branch.")
    parser.add_argument("--branch", required=True, help="Branch name.")
    parser.add_argument("--repo-root", default=".", help="Repo root (default: cwd).")
    parser.add_argument("--platform", choices=["github", "gitlab"], required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    service = GitService(ServiceContext(config=config))
    triggered = service.trigger_ci(repo_root, args.branch, ci_provider=args.platform)
    if not triggered:
        sys.exit(EXIT_RUNTIME_ERROR)


if __name__ == "__main__":
    main()
