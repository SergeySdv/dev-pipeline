#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a TerraformManager repo layout (lightweight checklist).")
    parser.add_argument("--repo-root", required=True, help="Path to the TerraformManager repo root")
    parser.add_argument("--strict", action="store_true", help="Fail (non-zero) when required assets are missing")
    parser.add_argument("--smoke", action="store_true", help="Run a small smoke check against discovered commands")
    return parser.parse_args(argv)


def _repo_has_backend_cli(repo_root: Path) -> bool:
    return (repo_root / "backend" / "cli" / "__init__.py").exists() or (repo_root / "backend" / "cli.py").exists()


def _required_missing(repo_root: Path) -> list[str]:
    required = [
        repo_root / "scripts" / "service_manager.py",
        repo_root / "frontend",
        repo_root / "sample",
        repo_root / "payloads",
    ]
    missing = [str(p.relative_to(repo_root)) for p in required if not p.exists()]
    if not _repo_has_backend_cli(repo_root):
        missing.append("backend/cli/__init__.py (or backend/cli.py)")
    return missing


def _run_smoke(repo_root: Path) -> list[str]:
    failures: list[str] = []
    service_manager = repo_root / "scripts" / "service_manager.py"
    if service_manager.exists():
        proc = subprocess.run([sys.executable, str(service_manager)], cwd=repo_root, capture_output=True, text=True)
        if proc.returncode != 0:
            failures.append(f"scripts/service_manager.py (rc={proc.returncode})")

    backend_cli = repo_root / "backend" / "cli.py"
    if backend_cli.exists():
        proc = subprocess.run([sys.executable, str(backend_cli)], cwd=repo_root, capture_output=True, text=True)
        if proc.returncode != 0:
            failures.append(f"backend/cli.py (rc={proc.returncode})")

    return failures


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).expanduser()

    if not repo_root.exists():
        print(f"Skipping: repo not found at {repo_root}")
        return 0
    if not repo_root.is_dir():
        print(f"Skipping: repo root is not a directory: {repo_root}")
        return 0

    missing = _required_missing(repo_root)
    if missing:
        print("Skipping: missing required assets:\n- " + "\n- ".join(missing))
        return 1 if args.strict else 0

    if args.smoke:
        failures = _run_smoke(repo_root)
        if failures:
            print("Skipping: smoke checks failed:\n- " + "\n- ".join(failures))
            return 1 if args.strict else 0

    print(f"Validated TerraformManager repo at {repo_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

