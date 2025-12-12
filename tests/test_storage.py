import tempfile
from pathlib import Path

from tasksgodzilla.domain import CodexRunStatus, ProtocolStatus, StepStatus
from tasksgodzilla.storage import Database


def test_storage_round_trip_creates_records() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "orchestrator.sqlite"
        db = Database(db_path)
        db.init_schema()

        project = db.create_project(
            name="demo",
            git_url="git@example.com/demo.git",
            base_branch="main",
            ci_provider="github",
            default_models={"planning": "gpt-5.1-high"},
        )
        assert project.id > 0

        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="0001-demo",
            status=ProtocolStatus.PLANNING,
            base_branch="main",
            worktree_path="/tmp/worktree",
            protocol_root="/tmp/worktree/.protocols/0001-demo",
            description="demo run",
        )
        assert run.id > 0
        assert run.template_config is None
        assert run.template_source is None

        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=0,
            step_name="00-setup",
            step_type="setup",
            status=StepStatus.PENDING,
            model=None,
        )
        assert step.id > 0
        assert step.engine_id is None
        assert step.policy is None
        assert step.runtime_state is None

        db.append_event(
            protocol_run_id=run.id,
            step_run_id=step.id,
            event_type="note",
            message="created",
        )

        # Verify readbacks
        projects = db.list_projects()
        assert len(projects) == 1
        runs = db.list_protocol_runs(project.id)
        assert len(runs) == 1
        steps = db.list_step_runs(run.id)
        assert len(steps) == 1
        events = db.list_events(run.id)
        assert len(events) == 1
        recent = db.list_recent_events()
        assert len(recent) == 1
        assert recent[0].protocol_name == "0001-demo"
        assert recent[0].project_name == "demo"

        db.create_codex_run(run_id="run-artifacts", job_type="bootstrap", status=CodexRunStatus.RUNNING)
        artifact_path = Path(tmpdir) / "artifact.txt"
        artifact_path.write_text("hello", encoding="utf-8")
        artifact = db.upsert_run_artifact(
            "run-artifacts",
            "demo",
            kind="test",
            path=str(artifact_path),
        )
        assert artifact.id > 0
        items = db.list_run_artifacts("run-artifacts")
        assert any(a.name == "demo" for a in items)
        got = db.get_run_artifact(artifact.id)
        assert got.run_id == "run-artifacts"


def test_codex_run_registry_round_trip() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "orchestrator.sqlite"
        db = Database(db_path)
        db.init_schema()

        run_id = "run-123"
        created = db.create_codex_run(
            run_id=run_id,
            job_type="bootstrap",
            status=CodexRunStatus.RUNNING,
            prompt_version="v1",
            params={"hello": "world"},
            log_path="/tmp/runs/run-123/logs.txt",
            started_at="2024-01-01T00:00:00Z",
        )
        assert created.run_id == run_id
        assert created.job_type == "bootstrap"
        assert created.prompt_version == "v1"
        assert created.params == {"hello": "world"}
        assert created.log_path.endswith("logs.txt")

        updated = db.update_codex_run(
            run_id,
            status=CodexRunStatus.SUCCEEDED,
            result={"ok": True},
            cost_tokens=42,
            cost_cents=5,
            finished_at="2024-01-01T00:30:00Z",
        )
        assert updated.status == CodexRunStatus.SUCCEEDED
        assert updated.result == {"ok": True}
        assert updated.cost_tokens == 42
        assert updated.cost_cents == 5
        assert updated.finished_at is not None

        runs = db.list_codex_runs(job_type="bootstrap")
        assert runs
        assert runs[0].run_id == run_id
