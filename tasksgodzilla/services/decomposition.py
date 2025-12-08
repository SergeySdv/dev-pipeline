from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from tasksgodzilla.codex import enforce_token_budget, run_codex_exec
from tasksgodzilla.config import load_config
from tasksgodzilla.logging import get_logger
from tasksgodzilla.pipeline import decompose_step_prompt, is_simple_step, step_markdown_files

log = get_logger(__name__)


@dataclass
class DecompositionService:
    """Facade for step decomposition using the existing pipeline helpers.

    This mirrors the decomposition loop used in the protocol pipeline and Codex
    worker, making it easier to migrate orchestration logic into a dedicated
    service while preserving behaviour.
    """

    def decompose_protocol(
        self,
        protocol_root: Path,
        *,
        model: Optional[str] = None,
        skip_simple: Optional[bool] = None,
    ) -> Dict[str, List[str]]:
        """Decompose all eligible step files under the given protocol root."""
        config = load_config()

        if protocol_root.parent.name == ".protocols":
            workspace_root = protocol_root.parent.parent
        else:
            workspace_root = protocol_root.parent

        plan_md_path = protocol_root / "plan.md"
        plan_md = plan_md_path.read_text(encoding="utf-8") if plan_md_path.is_file() else ""

        decompose_model = model or config.decompose_model or "gpt-5.1-high"
        budget_limit = config.max_tokens_per_step or config.max_tokens_per_protocol
        effective_skip_simple = skip_simple if skip_simple is not None else getattr(config, "skip_simple_decompose", False)

        step_files = step_markdown_files(protocol_root)
        tmp_dir = protocol_root / ".tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        decomposed: List[str] = []
        skipped: List[str] = []

        for step_file in step_files:
            step_content = step_file.read_text(encoding="utf-8")
            if effective_skip_simple and is_simple_step(step_content):
                skipped.append(step_file.name)
                log.info(
                    "decompose_step_skipped",
                    extra={"protocol_root": str(protocol_root), "step_file": step_file.name, "reason": "simple_step"},
                )
                continue

            decompose_text = decompose_step_prompt(
                protocol_name=protocol_root.name,
                protocol_number=protocol_root.name.split("-", 1)[0],
                plan_md=plan_md,
                step_filename=step_file.name,
                step_content=step_content,
            )
            enforce_token_budget(
                decompose_text,
                budget_limit,
                f"decompose:{step_file.name}",
                mode=config.token_budget_mode,
            )

            tmp_step = tmp_dir / f"{step_file.name}.decomposed"
            log.info(
                "decompose_step",
                extra={"protocol_root": str(protocol_root), "step_file": step_file.name, "model": decompose_model},
            )
            run_codex_exec(
                model=decompose_model,
                cwd=workspace_root,
                prompt_text=decompose_text,
                sandbox="read-only",
                output_last_message=tmp_step,
            )

            new_content = tmp_step.read_text(encoding="utf-8")
            step_file.write_text(new_content, encoding="utf-8")
            decomposed.append(step_file.name)

        return {"decomposed": decomposed, "skipped": skipped}

