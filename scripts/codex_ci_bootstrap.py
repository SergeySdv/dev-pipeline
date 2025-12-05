#!/usr/bin/env python3
"""
Run Codex CLI to infer stack and fill CI scripts for the current repository.

This wraps codex exec (default model: gpt-5.1-codex-max) using the repo-discovery prompt.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd=None, check=True, input_text=None):
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        input=input_text.encode("utf-8") if input_text else None,
        check=check,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Use Codex CLI to infer stack and fill CI scripts for this repo."
    )
    parser.add_argument(
        "--model",
        default="gpt-5.1-codex-max",
        help="Codex model to use (default: gpt-5.1-codex-max).",
    )
    parser.add_argument(
        "--prompt-file",
        default="prompts/repo-discovery.prompt.md",
        help="Prompt file to feed Codex (default: prompts/repo-discovery.prompt.md).",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--sandbox",
        default="workspace-write",
        help="Codex sandbox mode (default: workspace-write).",
    )
    parser.add_argument(
        "--skip-git-check",
        action="store_true",
        help="Pass --skip-git-repo-check to codex exec.",
    )
    args = parser.parse_args()

    if shutil.which("codex") is None:
        print("codex CLI not found in PATH. Install/configure codex first.", file=sys.stderr)
        sys.exit(1)

    repo_root = Path(args.repo_root).resolve()
    prompt_path = repo_root / args.prompt_file
    if not prompt_path.is_file():
        print(f"Prompt file not found: {prompt_path}", file=sys.stderr)
        sys.exit(1)

    prompt_text = prompt_path.read_text(encoding="utf-8")

    cmd = [
        "codex",
        "exec",
        "-m",
        args.model,
        "--cd",
        str(repo_root),
        "--sandbox",
        args.sandbox,
    ]
    if args.skip_git_check:
        cmd.append("--skip-git-repo-check")
    cmd.append("-")

    print(f"Running Codex discovery with model {args.model} ...")
    run(cmd, input_text=prompt_text)
    print("Codex discovery complete. Review scripts/ci/* for generated commands.")


if __name__ == "__main__":
    main()
