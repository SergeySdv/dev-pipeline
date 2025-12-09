from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from tasksgodzilla.codex import run_process
from tasksgodzilla.domain import StepRun
from tasksgodzilla.logging import get_logger
from tasksgodzilla.prompt_utils import prompt_version
from tasksgodzilla.spec import resolve_spec_path

log = get_logger(__name__)


@dataclass
class PromptService:
    """Minimal prompt helper facade.

    This service focuses on resolving prompt files under a workspace root and
    attaching a stable version fingerprint. Higher-level naming and policy can
    be added later without changing call sites.
    """

    workspace_root: Path

    def resolve(self, relative_path: str) -> Tuple[Path, str, str]:
        """Return (path, text, version_hash) for the given prompt path."""
        path = (self.workspace_root / relative_path).resolve()
        text = path.read_text(encoding="utf-8")
        version = prompt_version(path)
        return path, text, version

    def resolve_qa_prompt(
        self, qa_config: Dict, protocol_root: Path, workspace_root: Path
    ) -> Tuple[Path, str]:
        """
        Resolve the QA prompt path (default or spec-provided) against the protocol
        root and workspace, allowing prompts outside `.protocols/`.
        
        Returns:
            Tuple of (prompt_path, prompt_version)
        """
        prompt_ref = qa_config.get("prompt") if isinstance(qa_config, dict) else None
        if prompt_ref:
            prompt_path = resolve_spec_path(str(prompt_ref), protocol_root, workspace=workspace_root)
        else:
            prompt_path = (workspace_root / "prompts" / "quality-validator.prompt.md").resolve()
        
        version = prompt_version(prompt_path)
        
        log.debug(
            "qa_prompt_resolved",
            extra={
                "prompt_path": str(prompt_path),
                "version": version,
                "from_config": bool(prompt_ref),
            },
        )
        return prompt_path, version

    def build_qa_context(
        self, protocol_root: Path, step_path: Path, workspace_root: Path
    ) -> Dict[str, str]:
        """
        Build context for QA prompt (plan, context, log, step file, git status).
        
        Returns:
            Dictionary with context components
        """
        def read_file(path: Path) -> str:
            return path.read_text(encoding="utf-8") if path.is_file() else ""
        
        plan = read_file(protocol_root / "plan.md")
        context = read_file(protocol_root / "context.md")
        log_content = read_file(protocol_root / "log.md")
        step = read_file(step_path)
        
        # Get git status
        repo_root = workspace_root
        git_status = "(not a git repo)"
        last_commit = "(no commits yet)"
        
        if (repo_root / ".git").exists():
            try:
                git_status = run_process(
                    ["git", "status", "--porcelain"],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                last_commit = run_process(
                    ["git", "log", "-1", "--pretty=format:%s"],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            except Exception:
                git_status = "(git status unavailable)"
                last_commit = "(no commits yet)"
        
        result = {
            "plan": plan,
            "context": context,
            "log": log_content,
            "step": step,
            "step_name": step_path.name,
            "git_status": git_status,
            "last_commit": last_commit,
        }
        
        log.debug(
            "qa_context_built",
            extra={
                "protocol_root": str(protocol_root),
                "step_path": str(step_path),
                "has_plan": bool(plan),
                "has_context": bool(context),
                "has_log": bool(log_content),
                "has_step": bool(step),
            },
        )
        return result

    def resolve_step_path_for_qa(
        self, protocol_root: Path, step_name: str, workspace_root: Path
    ) -> Path:
        """
        Resolve a step path for QA purposes, falling back to spec path resolution.
        """
        step_path = (protocol_root / step_name).resolve()
        if step_path.exists():
            return step_path
        
        alt = (protocol_root / f"{step_name}.md").resolve()
        if alt.exists():
            return alt
        
        return resolve_spec_path(step_name, protocol_root, workspace=workspace_root)

