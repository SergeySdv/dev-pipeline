from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from tasksgodzilla.storage import BaseDatabase

if TYPE_CHECKING:
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
        # Lazy import to avoid circular dependency
        from tasksgodzilla.workers.codex_worker import handle_execute_step
        handle_execute_step(step_run_id, self.db, job_id=job_id)

