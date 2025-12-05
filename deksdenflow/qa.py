import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class QualityResult:
    report_path: Path
    verdict: str
    output: str


def run(cmd, cwd=None, check=True, capture=True, input_text=None):
    """
    Run a subprocess with optional text input.

    When capture=True (default), text mode is enabled and input_text should be
    a string. When capture=False, callers may pass bytes via input_text if they
    need to stream raw data.
    """
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        input=input_text if input_text is not None else None,
        check=check,
        capture_output=capture,
        text=capture,
    )


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def build_prompt(protocol_root: Path, step_file: Path) -> str:
    plan = read_file(protocol_root / "plan.md")
    context = read_file(protocol_root / "context.md")
    log = read_file(protocol_root / "log.md")
    step = read_file(step_file)

    git_status = run(
        ["git", "status", "--porcelain"], cwd=protocol_root.parent.parent
    ).stdout.strip()
    last_commit = ""
    try:
        last_commit = run(
            ["git", "log", "-1", "--pretty=format:%s"],
            cwd=protocol_root.parent.parent,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        last_commit = "(no commits yet)"

    return f"""You are a QA orchestrator. Validate the current protocol step. Follow the checklist and output Markdown only (no fences).

plan.md:
{plan}

context.md:
{context}

log.md (may be empty):
{log}

Step file ({step_file.name}):
{step}

Git status (porcelain):
{git_status}

Latest commit message:
{last_commit}

Use the format from the quality-validator prompt. If any blocking issue, verdict = FAIL."""


def determine_verdict(report_text: str) -> str:
    upper = report_text.upper()
    if "VERDICT: FAIL" in upper:
        return "FAIL"
    lines = [line.strip().upper() for line in report_text.splitlines() if line.strip()]
    if lines and lines[-1].startswith("VERDICT") and "FAIL" in lines[-1]:
        return "FAIL"
    return "PASS"


def run_quality_check(
    protocol_root: Path,
    step_file: Path,
    model: str,
    prompt_file: Path,
    sandbox: str = "read-only",
    report_file: Optional[Path] = None,
) -> QualityResult:
    if shutil.which("codex") is None:
        raise FileNotFoundError("codex CLI not found in PATH")
    if not step_file.is_file():
        raise FileNotFoundError(f"Step file not found: {step_file}")
    if not prompt_file.is_file():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    prompt_prefix = prompt_file.read_text(encoding="utf-8")
    prompt_body = build_prompt(protocol_root, step_file)
    full_prompt = f"{prompt_prefix}\n\n{prompt_body}"

    report_path = report_file if report_file else protocol_root / "quality-report.md"

    cmd = [
        "codex",
        "exec",
        "-m",
        model,
        "--cd",
        str(protocol_root.parent.parent),
        "--sandbox",
        sandbox,
        "-",
    ]

    result = run(cmd, input_text=full_prompt, capture=True, check=False)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )

    report_text = result.stdout.strip()
    report_path.write_text(report_text, encoding="utf-8")
    verdict = determine_verdict(report_text)

    return QualityResult(report_path=report_path, verdict=verdict, output=report_text)
