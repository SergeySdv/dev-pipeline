#!/usr/bin/env python3
"""
Lightweight guard for the TerraformManager workflow plan.

By default it reports missing assets but exits 0 unless --strict is set.
This helps catch drifts between docs/terraformmanager-workflow-plan.md
and the repository layout without requiring the full stack to run.
"""

import argparse
import subprocess
from pathlib import Path
import sys
from typing import Iterable


def _exists_any(paths: Iterable[Path]) -> bool:
    return any(p.exists() for p in paths)


def _validate(repo_root: Path) -> list[str]:
    required = [
        repo_root / "scripts" / "service_manager.py",
        repo_root / "frontend",
        repo_root / "sample",
        repo_root / "payloads",
    ]
    backend_candidates = [
        repo_root / "backend" / "cli.py",
        repo_root / "backend" / "cli" / "__init__.py",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if not _exists_any(backend_candidates):
        missing.append(str(backend_candidates[0].parent))
    return missing


def _run_smoke(repo_root: Path, strict: bool) -> list[str]:
    """
    Attempt lightweight smoke commands. Returns a list of failures (empty on pass/skip).
    Commands are best-effort and skip when targets are absent.
    """
    failures: list[str] = []
    commands = []
    svc = repo_root / "scripts" / "service_manager.py"
    if svc.exists():
        commands.append([sys.executable, str(svc), "--help"])
    backend_cli = repo_root / "backend"
    if backend_cli.exists():
        commands.append([sys.executable, "-m", "backend.cli", "--help"])

    for cmd in commands:
        try:
            subprocess.run(cmd, cwd=repo_root, check=True, capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            failures.append(f"Command not found: {' '.join(cmd)}")
        except subprocess.CalledProcessError as exc:
            failures.append(f"Command failed ({' '.join(cmd)}): {exc.stderr.strip() or exc.stdout.strip()}")
        except Exception as exc:  # pragma: no cover - defensive
            failures.append(f"Command error ({' '.join(cmd)}): {exc}")
    if failures and not strict:
        print("Smoke checks failed (non-strict); continuing:")
        for fail in failures:
            print(f"- {fail}")
        return []
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate TerraformManager checklist assets.")
    parser.add_argument("--repo-root", type=Path, help="Path to the TerraformManager repository.")
    parser.add_argument("--strict", action="store_true", help="Fail (non-zero) when checks are skipped or missing.")
    parser.add_argument("--smoke", action="store_true", help="Run lightweight smoke commands when assets exist.")
    args = parser.parse_args()

    if not args.repo_root:
        print("TerraformManager repo path not provided; skipping checks.")
        return 1 if args.strict else 0
    repo_root = args.repo_root.expanduser().resolve()
    if not repo_root.exists():
        print(f"TerraformManager repo not found at {repo_root}; skipping.")
        return 1 if args.strict else 0

    missing = _validate(repo_root)
    if missing:
        print("Missing required TerraformManager assets:")
        for path in missing:
            print(f"- {path}")
        return 1 if args.strict else 0

    if args.smoke:
        failures = _run_smoke(repo_root, args.strict)
        if failures:
            for fail in failures:
                print(fail)
            return 1

    print(f"TerraformManager checklist validated at {repo_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
