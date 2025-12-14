from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from tasksgodzilla.codex import enforce_token_budget, run_codex_exec
from tasksgodzilla.config import load_config
from tasksgodzilla.logging import get_logger
from tasksgodzilla.pipeline import decompose_step_prompt, is_simple_step, classify_step_complexity, step_markdown_files

log = get_logger(__name__)


COMPLEXITY_LOW = "low"
COMPLEXITY_MEDIUM = "medium"
COMPLEXITY_HIGH = "high"


@dataclass
class DecompositionService:
    """Service for protocol step decomposition.
    
    This service handles the decomposition of high-level protocol steps into
    more detailed, actionable sub-steps using LLM-based decomposition.
    
    Responsibilities:
    - Decompose protocol step files into detailed sub-steps
    - Skip simple steps that don't need decomposition
    - Enforce token budgets during decomposition
    - Track which steps were decomposed vs skipped
    
    Decomposition Process:
    1. Read protocol plan and step files
    2. Determine if step is simple (skip if configured)
    3. Build decomposition prompt with plan and step context
    4. Execute decomposition via Codex
    5. Replace step file with decomposed version
    
    Simple Step Detection:
    Steps are considered "simple" if they:
    - Are very short (< 100 characters)
    - Contain only a single action
    - Don't require detailed planning
    
    Usage:
        decomposition_service = DecompositionService()
        
        # Decompose all steps in a protocol
        result = decomposition_service.decompose_protocol(
            protocol_root=Path("/path/to/.protocols/feature-123"),
            model="zai-coding-plan/glm-4.6",
            skip_simple=True
        )
        
        # Result contains:
        # {
        #     "decomposed": ["01-setup.md", "02-implement.md"],
        #     "skipped": ["03-simple-task.md"]
        # }
    """

    def decompose_protocol(
        self,
        protocol_root: Path,
        *,
        model: Optional[str] = None,
        skip_simple: Optional[bool] = None,
        policy_guidelines: Optional[str] = None,
        use_complexity_scoring: bool = True,
    ) -> Dict[str, List[str]]:
        """Decompose all eligible step files under the given protocol root.

        Uses complexity-based decomposition by default:
        - low: Skip decomposition entirely (execute directly)
        - medium: Single-pass decomposition
        - high: Recursive decomposition (decompose sub-steps)

        Set use_complexity_scoring=False to fall back to the legacy skip_simple behavior.
        """
        config = load_config()

        if protocol_root.parent.name == ".protocols":
            workspace_root = protocol_root.parent.parent
        else:
            workspace_root = protocol_root.parent

        plan_md_path = protocol_root / "plan.md"
        plan_md = plan_md_path.read_text(encoding="utf-8") if plan_md_path.is_file() else ""

        decompose_model = model or config.decompose_model or "zai-coding-plan/glm-4.6"
        budget_limit = config.max_tokens_per_step or config.max_tokens_per_protocol
        effective_skip_simple = skip_simple if skip_simple is not None else getattr(config, "skip_simple_decompose", False)

        step_files = step_markdown_files(protocol_root)
        tmp_dir = protocol_root / ".tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        decomposed: List[str] = []
        skipped: List[str] = []
        complexity_map: Dict[str, str] = {}

        for step_file in step_files:
            step_content = step_file.read_text(encoding="utf-8")

            if use_complexity_scoring:
                complexity = classify_step_complexity(step_content)
                complexity_map[step_file.name] = complexity

                if complexity == COMPLEXITY_LOW:
                    skipped.append(step_file.name)
                    log.info(
                        "decompose_step_skipped",
                        extra={
                            "protocol_root": str(protocol_root),
                            "step_file": step_file.name,
                            "reason": "complexity_low",
                            "complexity": complexity,
                        },
                    )
                    continue
            else:
                if effective_skip_simple and is_simple_step(step_content):
                    skipped.append(step_file.name)
                    log.info(
                        "decompose_step_skipped",
                        extra={"protocol_root": str(protocol_root), "step_file": step_file.name, "reason": "simple_step"},
                    )
                    continue
                complexity = COMPLEXITY_MEDIUM

            decompose_text = decompose_step_prompt(
                protocol_name=protocol_root.name,
                protocol_number=protocol_root.name.split("-", 1)[0],
                plan_md=plan_md,
                step_filename=step_file.name,
                step_content=step_content,
                policy_guidelines=policy_guidelines,
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
                extra={
                    "protocol_root": str(protocol_root),
                    "step_file": step_file.name,
                    "model": decompose_model,
                    "complexity": complexity,
                },
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

            if use_complexity_scoring and complexity == COMPLEXITY_HIGH:
                self._recursive_decompose(
                    step_file,
                    plan_md,
                    protocol_root,
                    workspace_root,
                    decompose_model,
                    budget_limit,
                    config.token_budget_mode,
                    policy_guidelines,
                    tmp_dir,
                )

        return {"decomposed": decomposed, "skipped": skipped, "complexity": complexity_map}

    def _recursive_decompose(
        self,
        step_file: Path,
        plan_md: str,
        protocol_root: Path,
        workspace_root: Path,
        model: str,
        budget_limit: Optional[int],
        budget_mode: str,
        policy_guidelines: Optional[str],
        tmp_dir: Path,
        max_depth: int = 2,
        current_depth: int = 0,
    ) -> None:
        """Recursively decompose high-complexity steps for additional granularity."""
        if current_depth >= max_depth:
            log.info(
                "decompose_recursive_max_depth",
                extra={"step_file": step_file.name, "max_depth": max_depth},
            )
            return

        step_content = step_file.read_text(encoding="utf-8")
        complexity = classify_step_complexity(step_content)

        if complexity != COMPLEXITY_HIGH:
            log.info(
                "decompose_recursive_done",
                extra={"step_file": step_file.name, "complexity": complexity, "depth": current_depth},
            )
            return

        decompose_text = decompose_step_prompt(
            protocol_name=protocol_root.name,
            protocol_number=protocol_root.name.split("-", 1)[0],
            plan_md=plan_md,
            step_filename=step_file.name,
            step_content=step_content,
            policy_guidelines=policy_guidelines,
        )
        enforce_token_budget(
            decompose_text,
            budget_limit,
            f"decompose:{step_file.name}:pass{current_depth + 2}",
            mode=budget_mode,
        )

        tmp_step = tmp_dir / f"{step_file.name}.decomposed.{current_depth + 1}"
        log.info(
            "decompose_step_recursive",
            extra={
                "protocol_root": str(protocol_root),
                "step_file": step_file.name,
                "model": model,
                "depth": current_depth + 1,
            },
        )
        run_codex_exec(
            model=model,
            cwd=workspace_root,
            prompt_text=decompose_text,
            sandbox="read-only",
            output_last_message=tmp_step,
        )

        new_content = tmp_step.read_text(encoding="utf-8")
        step_file.write_text(new_content, encoding="utf-8")

        self._recursive_decompose(
            step_file,
            plan_md,
            protocol_root,
            workspace_root,
            model,
            budget_limit,
            budget_mode,
            policy_guidelines,
            tmp_dir,
            max_depth,
            current_depth + 1,
        )

