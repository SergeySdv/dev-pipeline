#!/usr/bin/env python3
"""
Legacy compatibility shim for the old CI discovery bootstrap script.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run discovery bootstrap via the active discovery script.")
    parser.add_argument("--repo-root", default=".", help="Repository root to analyze.")
    parser.add_argument("--model", default=None, help="Model override for discovery engine.")
    parser.add_argument("--engine", default="opencode", help="Engine ID (default: opencode).")
    parser.add_argument("--run-id", default=None, help="Accepted for compatibility; ignored.")
    parser.add_argument("--skip-git-check", action="store_true", help="Accepted for compatibility; ignored.")
    parser.add_argument("--no-strict", dest="strict", action="store_false", help="Disable strict output checks.")
    parser.add_argument("--sandbox", default="workspace-write", help="Accepted for compatibility; ignored.")
    parser.add_argument("--prompt-file", default=None, help="Accepted for compatibility; ignored.")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "discovery_pipeline.py"),
        "--repo-root",
        str(args.repo_root),
        "--engine",
        str(args.engine),
    ]
    if args.model:
        cmd.extend(["--model", args.model])
    if not args.strict:
        cmd.append("--no-strict")

    print("scripts/codex_ci_bootstrap.py is in compatibility mode; delegating to scripts/discovery_pipeline.py")
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
