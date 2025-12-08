from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from tasksgodzilla.config import load_config
from tasksgodzilla.logging import get_logger
from tasksgodzilla.qa import QualityResult, run_quality_check
from tasksgodzilla.storage import BaseDatabase
from tasksgodzilla.workers.codex_worker import handle_quality

log = get_logger(__name__)


@dataclass
class QualityService:
    """Facade for running QA checks against protocol steps.

    This wraps `tasksgodzilla.qa.run_quality_check` with config-aware defaults so
    callers can gradually centralize QA behaviour here. For orchestrated runs,
    `run_for_step_run` delegates to the existing worker implementation.
    """

    db: Optional[BaseDatabase] = None
    default_model: Optional[str] = None

    def run_for_step_run(self, step_run_id: int, job_id: Optional[str] = None) -> None:
        """
        Run QA for a StepRun using the orchestrator's existing worker logic.

        This is primarily used by background jobs (run_quality_job) and can be
        refactored over time to move logic fully into the service layer.
        """
        if self.db is None:
            raise ValueError("QualityService.db is required for step-run QA")
        handle_quality(step_run_id, self.db, job_id=job_id)

    def evaluate_step(
        self,
        protocol_root: Path,
        step_filename: str,
        *,
        prompt_file: Optional[Path] = None,
        sandbox: str = "read-only",
        report_file: Optional[Path] = None,
        engine_id: Optional[str] = None,
    ) -> QualityResult:
        """Run QA for a single step file under the given protocol root."""
        config = load_config()

        model = self.default_model or config.qa_model or "codex-5.1-max"

        # Best-effort resolution of the workspace root for prompts.
        if protocol_root.parent.name == ".protocols":
            workspace_root = protocol_root.parent.parent
        else:
            workspace_root = protocol_root.parent

        prompt_path = prompt_file or (workspace_root / "prompts" / "quality-validator.prompt.md")
        step_path = protocol_root / step_filename

        log.info(
            "quality_service_evaluate_step",
            extra={
                "protocol_root": str(protocol_root),
                "step_file": str(step_path),
                "prompt_file": str(prompt_path),
                "model": model,
                "sandbox": sandbox,
            },
        )

        return run_quality_check(
            protocol_root=protocol_root,
            step_file=step_path,
            model=model,
            prompt_file=prompt_path,
            sandbox=sandbox,
            report_file=report_file,
            max_tokens=config.max_tokens_per_step or config.max_tokens_per_protocol,
            token_budget_mode=config.token_budget_mode,
            engine_id=engine_id,
        )
