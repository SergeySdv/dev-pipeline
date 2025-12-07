import tempfile
from pathlib import Path

from tasksgodzilla.domain import CodexRunStatus
from tasksgodzilla.run_registry import RunRegistry
from tasksgodzilla.storage import Database


def test_run_registry_lifecycle_creates_logs_and_updates_status() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "runs.sqlite"
        runs_dir = Path(tmpdir) / "runs"
        db = Database(db_path)
        db.init_schema()

        registry = RunRegistry(db, runs_dir=runs_dir)
        run = registry.start_run("bootstrap", params={"hello": "world"}, prompt_version="v1")

        assert run.status == CodexRunStatus.RUNNING
        assert run.log_path is not None
        assert Path(run.log_path).exists()

        completed = registry.mark_succeeded(run.run_id, result={"ok": True}, cost_tokens=10)
        assert completed.status == CodexRunStatus.SUCCEEDED
        assert completed.result == {"ok": True}
        assert completed.cost_tokens == 10

        failed = registry.start_run("bootstrap")
        failed_run = registry.mark_failed(failed.run_id, error="boom")
        assert failed_run.status == CodexRunStatus.FAILED
        assert failed_run.error == "boom"

        cancelled = registry.start_run("bootstrap")
        cancelled_run = registry.mark_cancelled(cancelled.run_id, error="user_cancelled")
        assert cancelled_run.status == CodexRunStatus.CANCELLED
        assert cancelled_run.error == "user_cancelled"
