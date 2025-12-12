#!/usr/bin/env python3
"""
Offline discovery/doc validation.

Checks for required prompts/docs without invoking Codex or network access.
"""

import argparse
from pathlib import Path
import sys
from typing import Iterable


REQUIRED_FILES = [
    Path("prompts/repo-discovery.prompt.md"),
    Path("prompts/discovery-inventory.prompt.md"),
    Path("prompts/discovery-architecture.prompt.md"),
    Path("prompts/discovery-api-reference.prompt.md"),
    Path("prompts/discovery-ci-notes.prompt.md"),
    Path("docs/solution-design.md"),
    Path("docs/implementation-plan.md"),
    Path("docs/tasksgodzilla.md"),
    Path("docs/terraformmanager-workflow-plan.md"),
]


def _validate(repo_root: Path, required: Iterable[Path]) -> list[str]:
    missing: list[str] = []
    for rel in required:
        path = (repo_root / rel).resolve()
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(str(rel))
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline discovery/doc validation.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root (default: CWD).")
    parser.add_argument("--strict", action="store_true", help="Fail (non-zero) when files are missing/empty.")
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    missing = _validate(repo_root, REQUIRED_FILES)
    if missing:
        print("Missing or empty required files:")
        for item in missing:
            print(f"- {item}")
        return 1 if args.strict else 0

    print("Offline discovery/doc validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
