import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tasksgodzilla.domain import CodexRun, CodexRunStatus
from tasksgodzilla.logging import get_logger, log_extra
from tasksgodzilla.storage import BaseDatabase

RUNS_DIR_ENV = "CODEX_RUNS_DIR"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRegistry:
    """
    Lightweight lifecycle helper for Codex runs. Records start/success/failure/cancel
    and ensures log files live under a predictable runs/<run_id>/logs.txt path.
    """

    def __init__(self, db: BaseDatabase, runs_dir: Optional[Path] = None):
        self.db = db
        self.runs_dir = Path(runs_dir or os.environ.get(RUNS_DIR_ENV, "runs")).expanduser()
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.log = get_logger(__name__)

    def ensure_log_path(self, run_id: str, override: Optional[str] = None) -> Path:
        """
        Create the log file for a run if needed and return its path.
        """
        if override:
            path = Path(override).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.touch()
            return path
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        log_file = run_dir / "logs.txt"
        if not log_file.exists():
            log_file.touch()
        return log_file

    def start_run(
        self,
        job_type: str,
        *,
        run_id: Optional[str] = None,
        run_kind: Optional[str] = None,
        project_id: Optional[int] = None,
        protocol_run_id: Optional[int] = None,
        step_run_id: Optional[int] = None,
        queue: Optional[str] = None,
        attempt: Optional[int] = None,
        worker_id: Optional[str] = None,
        params: Optional[dict] = None,
        prompt_version: Optional[str] = None,
        log_path: Optional[Path] = None,
        cost_tokens: Optional[int] = None,
        cost_cents: Optional[int] = None,
    ) -> CodexRun:
        run_id = run_id or str(uuid.uuid4())
        existing: Optional[CodexRun] = None
        try:
            existing = self.db.get_codex_run(run_id)
        except Exception:
            existing = None
        log_file = self.ensure_log_path(run_id, (log_path or (existing.log_path if existing else None)))
        if existing:
            run = self.db.update_codex_run(
                run_id,
                status=CodexRunStatus.RUNNING,
                run_kind=run_kind if run_kind is not None else existing.run_kind,
                project_id=project_id if project_id is not None else existing.project_id,
                protocol_run_id=protocol_run_id if protocol_run_id is not None else existing.protocol_run_id,
                step_run_id=step_run_id if step_run_id is not None else existing.step_run_id,
                queue=queue if queue is not None else existing.queue,
                attempt=attempt if attempt is not None else existing.attempt,
                worker_id=worker_id if worker_id is not None else existing.worker_id,
                params=params if params is not None else existing.params,
                prompt_version=prompt_version if prompt_version is not None else existing.prompt_version,
                log_path=str(log_file),
                started_at=_now_iso(),
            )
        else:
            run = self.db.create_codex_run(
                run_id=run_id,
                job_type=job_type,
                status=CodexRunStatus.RUNNING,
                run_kind=run_kind,
                project_id=project_id,
                protocol_run_id=protocol_run_id,
                step_run_id=step_run_id,
                queue=queue,
                attempt=attempt,
                worker_id=worker_id,
                prompt_version=prompt_version,
                params=params,
                log_path=str(log_file),
                started_at=_now_iso(),
                cost_tokens=cost_tokens,
                cost_cents=cost_cents,
            )
        self.log.info(
            "codex_run_started",
            extra={**log_extra(run_id=run_id), "job_type": job_type, "status": run.status},
        )
        return run

    def mark_succeeded(
        self,
        run_id: str,
        *,
        result: Optional[dict] = None,
        cost_tokens: Optional[int] = None,
        cost_cents: Optional[int] = None,
    ) -> CodexRun:
        existing: Optional[CodexRun] = None
        try:
            existing = self.db.get_codex_run(run_id)
        except Exception:
            existing = None
        merged_result: Optional[dict] = result
        if isinstance(existing.result, dict) and isinstance(result, dict):
            merged_result = dict(existing.result)
            merged_result.update(result)
        run = self.db.update_codex_run(
            run_id,
            status=CodexRunStatus.SUCCEEDED,
            result=merged_result,
            cost_tokens=cost_tokens,
            cost_cents=cost_cents,
            finished_at=_now_iso(),
        )
        self.log.info(
            "codex_run_succeeded",
            extra={**log_extra(run_id=run_id), "status": run.status},
        )
        return run

    def mark_failed(self, run_id: str, *, error: str, result: Optional[dict] = None) -> CodexRun:
        existing: Optional[CodexRun] = None
        try:
            existing = self.db.get_codex_run(run_id)
        except Exception:
            existing = None
        merged_result: Optional[dict] = result
        if isinstance(existing.result, dict) and isinstance(result, dict):
            merged_result = dict(existing.result)
            merged_result.update(result)
        run = self.db.update_codex_run(
            run_id,
            status=CodexRunStatus.FAILED,
            error=error,
            result=merged_result,
            finished_at=_now_iso(),
        )
        self.log.warning(
            "codex_run_failed",
            extra={**log_extra(run_id=run_id), "status": run.status, "error": error},
        )
        return run

    def mark_cancelled(self, run_id: str, *, error: Optional[str] = None) -> CodexRun:
        run = self.db.update_codex_run(
            run_id,
            status=CodexRunStatus.CANCELLED,
            error=error,
            finished_at=_now_iso(),
        )
        self.log.info(
            "codex_run_cancelled",
            extra={**log_extra(run_id=run_id), "status": run.status, "error": error},
        )
        return run

    def get(self, run_id: str) -> CodexRun:
        return self.db.get_codex_run(run_id)

    def list(
        self,
        *,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        project_id: Optional[int] = None,
        protocol_run_id: Optional[int] = None,
        step_run_id: Optional[int] = None,
        run_kind: Optional[str] = None,
        limit: int = 100,
    ) -> list[CodexRun]:
        return self.db.list_codex_runs(
            job_type=job_type,
            status=status,
            project_id=project_id,
            protocol_run_id=protocol_run_id,
            step_run_id=step_run_id,
            run_kind=run_kind,
            limit=limit,
        )
