from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tasksgodzilla.storage import BaseDatabase
from tasksgodzilla.workers.codex_worker import handle_execute_step


@dataclass
class ExecutionService:
    """Minimal facade for executing a single step.

    This delegates directly to the existing Codex worker implementation so
    callers can be migrated to a stable service API without changing behaviour.
    """

    db: BaseDatabase

    def execute_step(self, step_run_id: int, job_id: Optional[str] = None) -> None:
        """Execute the given StepRun via the Codex worker."""
        handle_execute_step(step_run_id, self.db, job_id=job_id)

