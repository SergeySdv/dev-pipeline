import os
from pathlib import Path

from deksdenflow.domain import ProtocolStatus, StepStatus
from deksdenflow.storage import Database
from deksdenflow.workers import codex_worker


def test_execute_step_auto_qa_runs_quality(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DEKSDENFLOW_AUTO_QA_AFTER_EXEC", "true")
    db_path = tmp_path / "db.sqlite"
    db = Database(db_path)
    db.init_schema()

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)

    project = db.create_project("demo", str(repo_root), "main", None, None)
    run = db.create_protocol_run(
        project.id,
        "0001-demo",
        ProtocolStatus.RUNNING,
        "main",
        None,
        None,
        "demo protocol",
    )
    step = db.create_step_run(run.id, 0, "00-setup.md", "setup", StepStatus.PENDING, model=None)

    # Ensure stub path (no codex)
    monkeypatch.setattr(codex_worker.shutil, "which", lambda _: None)

    codex_worker.handle_execute_step(step.id, db)

    step_after = db.get_step_run(step.id)
    assert step_after.status == StepStatus.COMPLETED
    run_after = db.get_protocol_run(run.id)
    assert run_after.status in (ProtocolStatus.RUNNING, ProtocolStatus.COMPLETED)
