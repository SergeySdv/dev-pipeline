#!/usr/bin/env python3
"""
Run a lightweight DevGodzilla pytest harness.

Usage:
  python scripts/demo_harness.py [--verbose]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a lightweight DevGodzilla test harness.")
    parser.add_argument("--verbose", action="store_true", help="Run pytest in verbose mode.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    venv_python = repo_root / ".venv" / "bin" / "python"
    python_bin = venv_python if venv_python.exists() else Path(sys.executable)

    pytest_args = [
        "-m",
        "pytest",
        "tests/test_devgodzilla_*.py",
        "-k",
        "not integration",
    ]
    if not args.verbose:
        pytest_args.append("-q")

    env = os.environ.copy()
    env.setdefault("DEVGODZILLA_AUTO_CLONE", "false")

    return subprocess.run([str(python_bin), *pytest_args], cwd=repo_root, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
