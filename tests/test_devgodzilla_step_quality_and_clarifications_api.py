import os
import subprocess
import tempfile
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
    from devgodzilla.api.app import app
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore
    app = None  # type: ignore


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True)
    (path / "README.md").write_text("demo", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "tester",
            "GIT_AUTHOR_EMAIL": "tester@example.com",
            "GIT_COMMITTER_NAME": "tester",
            "GIT_COMMITTER_EMAIL": "tester@example.com",
        },
    )


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_step_quality_uses_prompt_qa_report_text_for_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.db.database import SQLiteDatabase

    report_text = """Summary
Status command is not implemented yet.

Findings:
- Blocking issues
  - Missing /status command handler registration.

Next actions:
- Add a /status command handler.
- Add coverage for the command.

Verdict: FAIL
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-proto"
        protocol_root.mkdir(parents=True, exist_ok=True)
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-proto",
            status="blocked",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="01-demo",
            step_type="exec",
            status="failed",
        )
        db.create_qa_result(
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
            verdict="fail",
            summary="FAIL: 1 findings",
            gate_results=[
                {
                    "gate_id": "prompt_qa",
                    "gate_name": "Prompt QA",
                    "verdict": "fail",
                    "findings": [],
                    "metadata": {"report_text": report_text},
                }
            ],
            findings=[],
            report_text=report_text,
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(f"/steps/{step.id}/quality")
                assert response.status_code == 200
                payload = response.json()
                gate = payload["gates"][0]
                finding = gate["findings"][0]
                assert gate["article"] == "prompt_qa"
                assert finding["message"] == "Missing /status command handler registration."
                assert "Add a /status command handler." in finding["suggested_fix"]
        finally:
            app.dependency_overrides.clear()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_protocol_clarifications_enrich_prompt_qa_details(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.db.database import SQLiteDatabase

    report_text = """Summary
State tracking was not persisted.

Findings:
- Blocking issues
  - Missing persistent state store for the bot.

Next actions:
- Save state transitions to disk or database.

Verdict: FAIL
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-proto"
        protocol_root.mkdir(parents=True, exist_ok=True)
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-proto",
            status="blocked",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="01-demo",
            step_type="exec",
            status="failed",
        )
        db.create_qa_result(
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
            verdict="fail",
            summary="FAIL: 1 findings",
            gate_results=[],
            findings=[],
            report_text=report_text,
        )
        db.upsert_clarification(
            scope=f"step:{step.id}",
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
            key="qa:prompt_qa:123",
            question="Resolve QA finding: Prompt QA reported FAIL",
            recommended=None,
            applies_to="qa",
            blocking=True,
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(f"/protocols/{run.id}/clarifications?status=open")
                assert response.status_code == 200
                payload = response.json()
                assert payload[0]["question"] == "Resolve QA finding: Missing persistent state store for the bot."
                assert "Save state transitions to disk or database." in payload[0]["recommended"]["text"]
        finally:
            app.dependency_overrides.clear()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_step_quality_exposes_test_gate_command_and_output(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-proto"
        protocol_root.mkdir(parents=True, exist_ok=True)
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-proto",
            status="completed",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="03-testing",
            step_type="verify",
            status="completed",
        )
        db.create_qa_result(
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
            verdict="pass",
            summary="PASS: 0 findings",
            gate_results=[
                {
                    "gate_id": "test",
                    "gate_name": "Test Gate",
                    "verdict": "pass",
                    "findings": [],
                    "metadata": {
                        "command": "pytest --tb=short -q",
                        "stdout": "37 passed in 1.23s",
                    },
                }
            ],
            findings=[],
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(f"/steps/{step.id}/quality")
                assert response.status_code == 200
                payload = response.json()
                gate = payload["gates"][0]
                assert gate["article"] == "test"
                assert gate["details"]["command"] == "pytest --tb=short -q"
                assert gate["details"]["stdout"] == "37 passed in 1.23s"
        finally:
            app.dependency_overrides.clear()
