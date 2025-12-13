"""
Codex worker: thin adapters that delegate to service layer.

All business logic has been moved to the services layer:
- PlanningService: Protocol planning
- ExecutionService: Step execution
- QualityService: QA validation
- OrchestratorService: PR/MR operations

These worker functions exist for RQ job compatibility and backward compatibility.
"""

import re
import shutil  # kept for test backward compatibility (monkeypatching)
from pathlib import Path
from typing import Optional

from tasksgodzilla.logging import get_logger, log_extra
from tasksgodzilla.domain import ProtocolRun, StepRun
from tasksgodzilla.pipeline import step_markdown_files
from tasksgodzilla.storage import BaseDatabase

log = get_logger(__name__)


def _ensure_required_step_sections(protocol_root: Path, required_sections: list[str]) -> list[str]:
    """
    Best-effort normalization: ensure each step markdown file contains headings for required sections.
    Returns a list of step filenames modified.
    """
    if not required_sections:
        return []
    modified: list[str] = []
    for step_file in step_markdown_files(protocol_root, include_setup=True):
        try:
            content = step_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lower = content.lower()
        missing: list[str] = []
        for section in required_sections:
            sec = (section or "").strip()
            if not sec:
                continue
            pattern = r"(?m)^#{1,6}\\s+" + re.escape(sec.lower()) + r"\\s*$"
            if re.search(pattern, lower):
                continue
            missing.append(sec)
        if not missing:
            continue
        blocks = []
        for sec in missing:
            blocks.append(f"\\n\\n## {sec}\\n\\n- TBD\\n")
        new_content = content.rstrip() + "".join(blocks) + "\\n"
        try:
            step_file.write_text(new_content, encoding="utf-8")
            modified.append(step_file.name)
        except Exception:
            continue
    return modified


def load_project(repo_root: Path, protocol_name: str, base_branch: str) -> Path:
    """
    Backward-compatible helper kept for tests and older integrations.

    Historically this function prepared a project worktree for a protocol run.
    The worker now delegates repo/worktree setup to GitService, so this is a
    no-op that returns the given repo_root.
    """
    return repo_root


def _load_project_with_context(repo_root: Path, *args, **kwargs) -> Path:
    """
    Legacy helper kept for unit tests.

    Previous versions enriched the repo with protocol context before execution.
    Context resolution is now handled by ExecutionService/QualityService.
    """
    return repo_root


def git_push_and_open_pr(*_args, **_kwargs) -> bool:
    """Legacy stub for tests; GitService handles push/PR now."""
    return False


def trigger_ci_pipeline(*_args, **_kwargs) -> bool:
    """Legacy stub for tests; GitService handles CI triggers now."""
    return False


def _log_context(
    run: Optional[ProtocolRun] = None,
    step: Optional[StepRun] = None,
    job_id: Optional[str] = None,
    project_id: Optional[int] = None,
    protocol_run_id: Optional[int] = None,
) -> dict:
    """
    Build a standard extra payload so job/protocol/step IDs are always populated.
    """
    return log_extra(
        job_id=job_id,
        project_id=project_id or (run.project_id if run else None),
        protocol_run_id=protocol_run_id or (run.id if run else None),
        step_run_id=step.id if step else None,
    )



def handle_plan_protocol(protocol_run_id: int, db: BaseDatabase, job_id: Optional[str] = None) -> None:
    """Plan a protocol run (thin adapter to PlanningService)."""
    from tasksgodzilla.services.planning import PlanningService
    planning_service = PlanningService(db)
    planning_service.plan_protocol(protocol_run_id, job_id=job_id)


def handle_execute_step(step_run_id: int, db: BaseDatabase, job_id: Optional[str] = None) -> None:
    """Execute a protocol step (thin adapter to ExecutionService)."""
    from tasksgodzilla.services.execution import ExecutionService
    execution_service = ExecutionService(db)
    execution_service.execute_step(step_run_id, job_id=job_id)


def handle_quality(step_run_id: int, db: BaseDatabase, job_id: Optional[str] = None) -> None:
    """Run QA for a protocol step (thin adapter to QualityService)."""
    from tasksgodzilla.services.quality import QualityService
    quality_service = QualityService(db=db)
    quality_service.run_for_step_run(step_run_id, job_id=job_id)


def handle_open_pr(protocol_run_id: int, db: BaseDatabase, job_id: Optional[str] = None) -> None:
    """Open PR/MR for a protocol (thin adapter to OrchestratorService)."""
    from tasksgodzilla.services.orchestrator import OrchestratorService
    orchestrator = OrchestratorService(db)
    orchestrator.open_protocol_pr(protocol_run_id, job_id=job_id)
