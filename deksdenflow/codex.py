import subprocess
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a subprocess command with optional working directory."""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
    )


def run_codex_exec(
    model: str,
    cwd: Path,
    prompt_text: str,
    sandbox: str = "read-only",
    output_schema: Optional[Path] = None,
    output_last_message: Optional[Path] = None,
) -> None:
    """Invoke codex exec with common flags."""
    cmd = [
        "codex",
        "exec",
        "-m",
        model,
        "--sandbox",
        sandbox,
        "--cd",
        str(cwd),
        "--skip-git-repo-check",
    ]
    if output_schema is not None:
        cmd.extend(["--output-schema", str(output_schema)])
    if output_last_message is not None:
        cmd.extend(["--output-last-message", str(output_last_message)])
    cmd.append("-")
    subprocess.run(
        cmd,
        input=prompt_text.encode("utf-8"),
        check=True,
    )
