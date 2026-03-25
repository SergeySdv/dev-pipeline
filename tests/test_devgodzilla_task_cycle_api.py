import json
import os
import subprocess
import tempfile
import time
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
    (path / "AGENTS.md").write_text("# Guidance\n", encoding="utf-8")
    (path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (path / "tests").mkdir(exist_ok=True)
    (path / "tests" / "test_demo.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
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
def test_task_cycle_build_context_creates_reusable_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.setenv("DEVGODZILLA_EXEC_ENGINE_ID", "opencode")
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n- keep current behavior\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text(
            "# Add demo behavior\n\n- [ ] update README.md\n- [ ] add tests\n",
            encoding="utf-8",
        )
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="pending",
            assigned_agent="dev",
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                resp = client.post(f"/work-items/{step.id}/build-context", json={"refresh": False})
                assert resp.status_code == 200
                payload = resp.json()
                assert payload["context_status"] == "ready"
                assert payload["plan_status"] == "missing"
                expected_task_dir = (repo / ".devgodzilla" / "task-cycle" / "protocols" / str(run.id) / "work-items" / str(step.id)).resolve()
                assert Path(payload["task_dir"]).resolve() == expected_task_dir
                context_path = Path(payload["artifact_refs"]["context_pack_json"])
                assert context_path.exists()
                assert context_path.resolve().is_relative_to(repo.resolve())
                assert not context_path.resolve().is_relative_to(projects_root.resolve())
                context = json.loads(context_path.read_text(encoding="utf-8"))
                assert context["project_id"] == project.id
                assert context["step_run_id"] == step.id
                assert any(item["path"] == "AGENTS.md" for item in context["style_guides"])
                assert any(command == "pytest -q" for command in context["test_commands"])
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_plan_creates_artifacts_and_gates_implementation(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n- update README.md\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n\n- [ ] update README.md\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="pending",
            assigned_agent="dev",
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                assert client.post(f"/work-items/{step.id}/build-context", json={"refresh": False}).status_code == 200

                implement_resp = client.post(f"/work-items/{step.id}/actions/implement", json={})
                assert implement_resp.status_code == 409
                assert "Generate a plan before implementation" in implement_resp.json()["detail"]

                plan_resp = client.post(f"/work-items/{step.id}/plan", json={"refresh": False})
                assert plan_resp.status_code == 200
                payload = plan_resp.json()
                assert payload["plan_status"] == "ready"
                plan_path = Path(payload["artifact_refs"]["plan_pack_json"])
                assert plan_path.exists()
                plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
                assert "files_to_modify" in plan_payload
                assert plan_payload["scope_assessment"]["status"] == "bounded"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_review_qa_and_pr_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.qa.gates.interface import GateResult, GateVerdict
    from devgodzilla.services.quality import QAResult, QAVerdict

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n\n- [ ] update README.md\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="completed",
            assigned_agent="dev",
        )
        artifacts_dir = protocol_root / ".devgodzilla" / "steps" / str(step.id) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "execution.log").write_text("implemented\n", encoding="utf-8")
        (artifacts_dir / "git-status.txt").write_text("M README.md\n", encoding="utf-8")
        (artifacts_dir / "changes.diff").write_text("diff --git a/README.md b/README.md\n", encoding="utf-8")
        (artifacts_dir / "git-status.txt").write_text("M README.md\n", encoding="utf-8")
        (artifacts_dir / "git-status.txt").write_text("M README.md\n", encoding="utf-8")

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.PolicyService.evaluate_step",
            lambda self, step_run_id, repo_root=None: [],
        )

        qa_call = {}

        def _fake_run_qa(self, step_run_id, gates=None, skip_gates=None, **kwargs):
            qa_call["gate_ids"] = [gate.gate_id for gate in (gates or [])]
            qa_call["skip_gates"] = list(skip_gates or [])
            return QAResult(
                step_run_id=step_run_id,
                verdict=QAVerdict.PASS,
                gate_results=[
                    GateResult(gate_id="lint", gate_name="Lint", verdict=GateVerdict.PASS),
                ],
                duration_seconds=0.1,
            )

        monkeypatch.setattr("devgodzilla.services.task_cycle.QualityService.run_qa", _fake_run_qa)
        monkeypatch.setattr("devgodzilla.services.task_cycle.QualityService.persist_verdict", lambda self, qa_result, step_run_id, report_path=None: None)
        monkeypatch.setattr("devgodzilla.services.task_cycle.GitService.push_and_open_pr", lambda self, *args, **kwargs: True)

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                context_resp = client.post(f"/work-items/{step.id}/build-context", json={"refresh": False})
                assert context_resp.status_code == 200

                plan_resp = client.post(f"/work-items/{step.id}/plan", json={"refresh": False})
                assert plan_resp.status_code == 200

                review_resp = client.post(f"/work-items/{step.id}/actions/review")
                assert review_resp.status_code == 200
                assert review_resp.json()["verdict"] == "passed"

                qa_resp = client.post(f"/work-items/{step.id}/actions/qa", json={"gates": ["lint"]})
                assert qa_resp.status_code == 200
                assert qa_resp.json()["qa"]["verdict"] == "passed"
                assert qa_resp.json()["work_item"]["status"] == "ready_for_pr"
                assert qa_call["gate_ids"] == ["lint"]
                assert qa_call["skip_gates"] == ["prompt_qa"]

                pr_resp = client.post(f"/work-items/{step.id}/actions/mark-pr-ready")
                assert pr_resp.status_code == 200
                assert pr_resp.json()["pr_ready"] is True
                assert pr_resp.json()["status"] == "pr_ready"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_mark_pr_ready_creates_rework_on_precommit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.qa.gates.interface import GateResult, GateVerdict
    from devgodzilla.services.quality import QAResult, QAVerdict

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url="https://github.com/example/demo.git",
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n\n- [ ] update README.md\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="completed",
            assigned_agent="dev",
        )
        artifacts_dir = protocol_root / ".devgodzilla" / "steps" / str(step.id) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "execution.log").write_text("implemented\n", encoding="utf-8")
        (artifacts_dir / "git-status.txt").write_text("M README.md\n", encoding="utf-8")
        (artifacts_dir / "changes.diff").write_text("diff --git a/README.md b/README.md\n", encoding="utf-8")

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.PolicyService.evaluate_step",
            lambda self, step_run_id, repo_root=None: [],
        )

        def _fake_run_qa(self, step_run_id, gates=None, skip_gates=None, **kwargs):
            return QAResult(
                step_run_id=step_run_id,
                verdict=QAVerdict.PASS,
                gate_results=[
                    GateResult(gate_id="lint", gate_name="Lint", verdict=GateVerdict.PASS),
                ],
                duration_seconds=0.1,
            )

        monkeypatch.setattr("devgodzilla.services.task_cycle.QualityService.run_qa", _fake_run_qa)
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.QualityService.persist_verdict",
            lambda self, qa_result, step_run_id, report_path=None: None,
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.TaskCycleService._run_pr_ready_precommit",
            lambda self, workspace_root, changed_files: {
                "status": "failed",
                "summary": "Pre-commit validation failed; rework is required before PR creation",
                "command": ".venv/bin/pre-commit run --files README.md",
                "checked_files": ["README.md"],
                "findings": ["ruff.....................................................................Failed", "README.md:1 unused import"],
                "warnings": [],
            },
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.GitService.push_and_open_pr",
            lambda self, *args, **kwargs: (_ for _ in ()).throw(AssertionError("push_and_open_pr should not run after pre-commit failure")),
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                assert client.post(f"/work-items/{step.id}/build-context", json={"refresh": False}).status_code == 200
                assert client.post(f"/work-items/{step.id}/plan", json={"refresh": False}).status_code == 200
                assert client.post(f"/work-items/{step.id}/actions/review").status_code == 200
                assert client.post(f"/work-items/{step.id}/actions/qa", json={"gates": ["lint"]}).status_code == 200

                pr_resp = client.post(f"/work-items/{step.id}/actions/mark-pr-ready")
                assert pr_resp.status_code == 200
                payload = pr_resp.json()
                assert payload["pr_ready"] is False
                assert payload["status"] == "needs_rework"
                assert payload["blocking_reason"] == "PR-ready validation failed; rework required"

                work_item_dir = repo / ".devgodzilla" / "task-cycle" / "protocols" / str(run.id) / "work-items" / str(step.id)
                rework_pack = json.loads((work_item_dir / "rework_pack.json").read_text(encoding="utf-8"))
                assert rework_pack["source"] == "pr_ready"
                assert "README.md:1 unused import" in rework_pack["findings"]

                pr_ready_report = json.loads((work_item_dir / "pr_ready_report.json").read_text(encoding="utf-8"))
                assert pr_ready_report["precommit"]["status"] == "failed"
                assert pr_ready_report["pull_request"]["status"] == "skipped"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_mark_pr_ready_filters_generated_files_from_commit_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url="https://github.com/example/demo.git",
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n\n- [ ] update README.md\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root.relative_to(repo)),
        )
        run = db.update_protocol_windmill(
            run.id,
            speckit_metadata={
                "task_cycle": True,
                "brownfield_output_mode": "task_cycle",
                "protocol_root": str(protocol_root.relative_to(repo)),
                "spec_path": str((repo / "specs" / "demo-feature" / "spec.md").relative_to(repo)),
                "plan_path": str((repo / "specs" / "demo-feature" / "plan.md").relative_to(repo)),
                "tasks_path": str((repo / "specs" / "demo-feature" / "tasks.md").relative_to(repo)),
            },
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="pending",
            assigned_agent="opencode",
        )
        refs_root = repo / ".devgodzilla" / "task-cycle" / "protocols" / str(run.id) / "work-items" / str(step.id)
        refs_root.mkdir(parents=True, exist_ok=True)
        (refs_root / "context_pack.json").write_text(
            json.dumps(
                {
                    "goal": "Demo feature",
                    "required_files": [{"path": "README.md", "reason": "doc"}],
                    "candidate_files": [{"path": "README.md", "reason": "doc"}],
                    "allowed_files": ["README.md", "src/telegram_bot_app/telegram_bot.py"],
                    "test_commands": ["pytest -q"],
                    "repo_root": str(repo),
                }
            ),
            encoding="utf-8",
        )
        (refs_root / "context_pack.md").write_text("# Context\n", encoding="utf-8")
        (refs_root / "plan_pack.json").write_text(
            json.dumps(
                {
                    "goal": "Demo feature",
                    "files_to_modify": ["README.md", "src/telegram_bot_app/telegram_bot.py"],
                    "scope_assessment": {"status": "bounded"},
                }
            ),
            encoding="utf-8",
        )
        (refs_root / "plan_pack.md").write_text("# Plan\n", encoding="utf-8")
        (refs_root / "review_report.json").write_text(json.dumps({"verdict": "passed"}), encoding="utf-8")
        (refs_root / "review_report.md").write_text("# Review\n", encoding="utf-8")
        (refs_root / "test_report.json").write_text(
            json.dumps(
                {
                    "verdict": "passed",
                    "gates": [
                        {"id": "lint", "status": "passed", "findings": []},
                        {"id": "test", "status": "passed", "findings": []},
                    ],
                }
            ),
            encoding="utf-8",
        )
        (refs_root / "test_report.md").write_text("# Test\n", encoding="utf-8")

        artifacts_dir = protocol_root / ".devgodzilla" / "steps" / str(step.id) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "execution.json").write_text("{}", encoding="utf-8")
        (artifacts_dir / "stdout.log").write_text("ok\n", encoding="utf-8")
        (artifacts_dir / "stderr.log").write_text("", encoding="utf-8")
        (artifacts_dir / "git-status.txt").write_text(
            "\n".join(
                [
                    "M README.md",
                    " M src/telegram_bot_app/telegram_bot.py",
                    "?? .devgodzilla/",
                    "?? .specify/",
                    "?? specs/",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (artifacts_dir / "changes.diff").write_text(
            "\n".join(
                [
                    "diff --git a/README.md b/README.md",
                    "+++ b/README.md",
                    "diff --git a/src/telegram_bot_app/telegram_bot.py b/src/telegram_bot_app/telegram_bot.py",
                    "+++ b/src/telegram_bot_app/telegram_bot.py",
                    "diff --git a/.devgodzilla/task-cycle/report.json b/.devgodzilla/task-cycle/report.json",
                    "+++ b/.devgodzilla/task-cycle/report.json",
                    "diff --git a/specs/demo-feature/plan.md b/specs/demo-feature/plan.md",
                    "+++ b/specs/demo-feature/plan.md",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        state = {
            "status": "ready_for_pr",
            "context_status": "ready",
            "plan_status": "ready",
            "review_status": "passed",
            "qa_status": "passed",
            "refactor_status": "not_needed",
            "pr_ready": False,
        }
        db.update_step_run(step.id, runtime_state={"task_cycle": state})

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.PolicyService.evaluate_step",
            lambda self, step_run_id, repo_root=None: [],
        )

        captured: dict[str, object] = {}

        def _fake_precommit(self, workspace_root, *, changed_files):
            captured["precommit_files"] = list(changed_files)
            return {
                "status": "passed",
                "summary": "pre-commit passed",
                "command": "pre-commit run --files README.md src/telegram_bot_app/telegram_bot.py",
                "checked_files": list(changed_files),
                "findings": [],
                "warnings": [],
            }

        def _fake_push_and_open_pr(self, worktree, protocol_name, base_branch, *, changed_files=None, **kwargs):
            captured["push_files"] = list(changed_files or [])
            return True

        monkeypatch.setattr("devgodzilla.services.task_cycle.TaskCycleService._run_pr_ready_precommit", _fake_precommit)
        monkeypatch.setattr("devgodzilla.services.task_cycle.GitService.push_and_open_pr", _fake_push_and_open_pr)

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.post(f"/work-items/{step.id}/actions/mark-pr-ready")
                assert response.status_code == 200
                payload = response.json()
                assert payload["pr_ready"] is True
                assert payload["status"] == "pr_ready"

                assert captured["precommit_files"] == ["README.md", "src/telegram_bot_app/telegram_bot.py"]
                assert captured["push_files"] == ["README.md", "src/telegram_bot_app/telegram_bot.py"]

                report = json.loads((refs_root / "pr_ready_report.json").read_text(encoding="utf-8"))
                assert report["commit_scope"]["staged_files"] == [
                    "README.md",
                    "src/telegram_bot_app/telegram_bot.py",
                ]
                assert sorted(report["commit_scope"]["excluded_generated_files"]) == [
                    ".devgodzilla",
                    ".devgodzilla/task-cycle/report.json",
                    ".specify",
                    "specs",
                    "specs/demo-feature/plan.md",
                ]
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_runtime_projection_exposes_stage_timeline_and_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.qa.gates.interface import GateResult, GateVerdict
    from devgodzilla.services.quality import QAResult, QAVerdict

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text(
            "# Demo step\n\n- [ ] update README.md\n- [ ] add tests\n",
            encoding="utf-8",
        )
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="running",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        run = db.update_protocol_windmill(run.id, windmill_flow_id="f/devgodzilla/brownfield_feature")
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="completed",
            assigned_agent="dev",
        )
        artifacts_dir = protocol_root / ".devgodzilla" / "steps" / str(step.id) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "execution.log").write_text("implemented\n", encoding="utf-8")
        (artifacts_dir / "changes.diff").write_text("diff --git a/README.md b/README.md\n", encoding="utf-8")
        db.create_job_run(
            run_id="run-step-1",
            job_type="execute",
            status="succeeded",
            run_kind="engine",
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
            params={"flow_id": "f/devgodzilla/brownfield_feature", "module_id": "step_execute"},
            windmill_job_id="wm-123",
        )

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.PolicyService.evaluate_step",
            lambda self, step_run_id, repo_root=None: [],
        )

        def _fake_run_qa(self, step_run_id, gates=None, skip_gates=None, **kwargs):
            return QAResult(
                step_run_id=step_run_id,
                verdict=QAVerdict.PASS,
                gate_results=[
                    GateResult(gate_id="lint", gate_name="Lint", verdict=GateVerdict.PASS),
                ],
                duration_seconds=0.1,
            )

        monkeypatch.setattr("devgodzilla.services.task_cycle.QualityService.run_qa", _fake_run_qa)
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.QualityService.persist_verdict",
            lambda self, qa_result, step_run_id, report_path=None: None,
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                assert client.post(f"/work-items/{step.id}/build-context", json={"refresh": False}).status_code == 200
                assert client.post(f"/work-items/{step.id}/plan", json={"refresh": False}).status_code == 200
                assert client.post(f"/work-items/{step.id}/actions/review").status_code == 200
                assert client.post(f"/work-items/{step.id}/actions/qa", json={"gates": ["lint"]}).status_code == 200

                runtime_resp = client.get(f"/work-items/{step.id}/runtime")
                assert runtime_resp.status_code == 200
                payload = runtime_resp.json()
                assert payload["active_stage"] == "pr_ready"
                assert payload["active_stage_status"] == "pending"
                assert payload["windmill"]["job_id"] == "wm-123"
                assert payload["windmill"]["module_id"] == "step_execute"
                assert payload["work_item"]["active_stage"] == "pr_ready"
                assert payload["stage_runs"][0]["stage_id"] == "build_context"
                assert payload["stage_runs"][0]["status"] == "completed"
                assert payload["stage_runs"][0]["mode"] == "fresh_context"
                assert payload["stage_runs"][1]["stage_id"] == "plan"
                assert payload["stage_runs"][1]["status"] == "completed"
                assert payload["stage_runs"][2]["stage_id"] == "implement"
                assert payload["stage_runs"][2]["status"] == "completed"
                assert any(
                    artifact["name"] == "execution.log"
                    for artifact in payload["stage_runs"][2]["artifacts"]
                )
                assert payload["stage_runs"][3]["status"] == "completed"
                assert payload["stage_runs"][4]["status"] == "completed"
                assert payload["stage_runs"][5]["stage_id"] == "refactor"
                assert payload["stage_runs"][5]["status"] == "skipped"
                assert payload["stage_runs"][6]["stage_id"] == "pr_ready"
                assert payload["stage_runs"][6]["status"] == "pending"
                assert payload["latest_artifacts"]
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_legacy_pr_ready_item_does_not_regress_to_plan_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.services.task_cycle import TaskCycleService

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "legacy-demo" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="legacy-demo",
            status="completed",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="completed",
            assigned_agent="dev",
        )

        work_item_dir = repo / ".devgodzilla" / "task-cycle" / "protocols" / str(run.id) / "work-items" / str(step.id)
        work_item_dir.mkdir(parents=True, exist_ok=True)
        (work_item_dir / "context_pack.json").write_text(json.dumps({"goal": "Legacy task"}), encoding="utf-8")
        (work_item_dir / "context_pack.md").write_text("# Context\n", encoding="utf-8")
        (work_item_dir / "review_report.json").write_text(json.dumps({"verdict": "passed"}), encoding="utf-8")
        (work_item_dir / "review_report.md").write_text("# Review\n", encoding="utf-8")
        (work_item_dir / "test_report.json").write_text(
            json.dumps({"verdict": "passed", "gates": [{"gate_id": "lint", "verdict": "passed"}]}),
            encoding="utf-8",
        )
        (work_item_dir / "test_report.md").write_text("# QA\n", encoding="utf-8")

        artifacts_dir = protocol_root / ".devgodzilla" / "steps" / str(step.id) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "execution.log").write_text("implemented\n", encoding="utf-8")
        (artifacts_dir / "changes.diff").write_text("diff --git a/README.md b/README.md\n", encoding="utf-8")
        (artifacts_dir / "git-status.txt").write_text("M README.md\n", encoding="utf-8")

        runtime_state = {
            TaskCycleService.RUNTIME_KEY: {
                "status": "pr_ready",
                "context_status": "ready",
                "review_status": "passed",
                "qa_status": "passed",
                "refactor_status": "not_needed",
                "pr_ready": True,
            }
        }
        db.update_step_run(step.id, runtime_state=runtime_state)

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                resp = client.get(f"/projects/{project.id}/task-cycle")
                assert resp.status_code == 200
                payload = resp.json()
                assert len(payload) == 1
                item = payload[0]
                assert item["status"] == "pr_ready"
                assert item["pr_ready"] is True
                assert item["plan_status"] == "legacy"
                assert item["active_stage"] == "pr_ready"
                assert item["active_stage_status"] == "completed"
                assert item["latest_completed_stage"] == "PR Ready"
                assert item["blocking_reason"] is None
                assert item["progress_summary"] == "Work item marked PR ready"

                runtime_resp = client.get(f"/work-items/{step.id}/runtime")
                assert runtime_resp.status_code == 200
                runtime = runtime_resp.json()
                assert runtime["stage_runs"][1]["stage_id"] == "plan"
                assert runtime["stage_runs"][1]["status"] == "completed"
                assert runtime["stage_runs"][1]["summary"] == "Legacy work item predates explicit plan artifacts"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_qa_defaults_to_deterministic_repo_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.qa.gates.interface import GateResult, GateVerdict
    from devgodzilla.services.quality import QAResult, QAVerdict

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="completed",
            assigned_agent="dev",
        )
        artifacts_dir = protocol_root / ".devgodzilla" / "steps" / str(step.id) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "execution.log").write_text("implemented\n", encoding="utf-8")
        (artifacts_dir / "changes.diff").write_text("diff --git a/README.md b/README.md\n", encoding="utf-8")
        (artifacts_dir / "git-status.txt").write_text("M README.md\n", encoding="utf-8")

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.PolicyService.evaluate_step",
            lambda self, step_run_id, repo_root=None: [],
        )

        captured = {}

        def _fake_run_qa(self, step_run_id, gates=None, skip_gates=None, **kwargs):
            captured["gate_ids"] = [gate.gate_id for gate in (gates or [])]
            captured["skip_gates"] = list(skip_gates or [])
            return QAResult(
                step_run_id=step_run_id,
                verdict=QAVerdict.PASS,
                gate_results=[
                    GateResult(gate_id="lint", gate_name="Lint", verdict=GateVerdict.PASS),
                    GateResult(gate_id="type", gate_name="Type", verdict=GateVerdict.PASS),
                    GateResult(gate_id="test", gate_name="Test", verdict=GateVerdict.PASS),
                ],
                duration_seconds=0.1,
            )

        monkeypatch.setattr("devgodzilla.services.task_cycle.QualityService.run_qa", _fake_run_qa)
        monkeypatch.setattr("devgodzilla.services.task_cycle.QualityService.persist_verdict", lambda self, qa_result, step_run_id, report_path=None: None)

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                assert client.post(f"/work-items/{step.id}/build-context", json={"refresh": False}).status_code == 200
                assert client.post(f"/work-items/{step.id}/plan", json={"refresh": False}).status_code == 200
                assert client.post(f"/work-items/{step.id}/actions/review").status_code == 200

                qa_resp = client.post(f"/work-items/{step.id}/actions/qa", json={})
                assert qa_resp.status_code == 200
                assert captured["gate_ids"] == ["lint", "type", "test"]
                assert captured["skip_gates"] == ["prompt_qa"]
                report = qa_resp.json()["qa"]
                assert report["verdict"] == "passed"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_refactor_stage_unblocks_after_review_requires_structure_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.qa.gates.interface import GateResult, GateVerdict
    from devgodzilla.services.quality import QAResult, QAVerdict

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        service_path = repo / "app.py"
        service_path.write_text(
            "def deeply_nested(a, b, c, d, e, f, g):\n"
            "    if a:\n"
            "        if b:\n"
            "            if c:\n"
            "                if d:\n"
            "                    if e:\n"
            "                        return f + g\n"
            "    return 0\n",
            encoding="utf-8",
        )

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n- update app.py\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n\n- [ ] update app.py\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="completed",
            assigned_agent="dev",
        )
        artifacts_dir = protocol_root / ".devgodzilla" / "steps" / str(step.id) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "execution.log").write_text("implemented\n", encoding="utf-8")
        (artifacts_dir / "git-status.txt").write_text("M app.py\n", encoding="utf-8")
        (artifacts_dir / "changes.diff").write_text("diff --git a/app.py b/app.py\n+++ b/app.py\n", encoding="utf-8")

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.PolicyService.evaluate_step",
            lambda self, step_run_id, repo_root=None: [],
        )

        def _fake_run_qa(self, step_run_id, gates=None, skip_gates=None, **kwargs):
            return QAResult(
                step_run_id=step_run_id,
                verdict=QAVerdict.PASS,
                gate_results=[
                    GateResult(gate_id="lint", gate_name="Lint", verdict=GateVerdict.PASS),
                    GateResult(gate_id="test", gate_name="Test", verdict=GateVerdict.PASS),
                ],
                duration_seconds=0.1,
            )

        def _fake_execute(self, step_run_id):
            db.update_step_status(step_run_id, "completed", summary="refactor applied")
            return type("ExecutionResult", (), {"success": True, "error": None})()

        monkeypatch.setattr("devgodzilla.services.task_cycle.QualityService.run_qa", _fake_run_qa)
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.QualityService.persist_verdict",
            lambda self, qa_result, step_run_id, report_path=None: None,
        )
        monkeypatch.setattr("devgodzilla.services.task_cycle.ExecutionService.execute_step", _fake_execute)

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                assert client.post(f"/work-items/{step.id}/build-context", json={"refresh": False}).status_code == 200
                assert client.post(f"/work-items/{step.id}/plan", json={"refresh": False}).status_code == 200

                review_resp = client.post(f"/work-items/{step.id}/actions/review")
                assert review_resp.status_code == 200
                assert review_resp.json()["verdict"] == "needs_refactor"
                assert review_resp.json()["maintainability_findings"]

                qa_resp = client.post(f"/work-items/{step.id}/actions/qa", json={})
                assert qa_resp.status_code == 200
                assert qa_resp.json()["work_item"]["status"] == "needs_refactor"
                assert qa_resp.json()["work_item"]["refactor_status"] == "required"

                refactor_resp = client.post(f"/work-items/{step.id}/actions/refactor", json={})
                assert refactor_resp.status_code == 200
                assert refactor_resp.json()["refactor_status"] == "completed"
                assert refactor_resp.json()["review_status"] == "pending"

                runtime_resp = client.get(f"/work-items/{step.id}/runtime")
                assert runtime_resp.status_code == 200
                runtime = runtime_resp.json()
                artifact_ids = [
                    artifact["id"]
                    for stage_run in runtime["stage_runs"]
                    for artifact in stage_run["artifacts"]
                ]
                assert len(artifact_ids) == len(set(artifact_ids))
                refactor_stage = next(
                    stage_run for stage_run in runtime["stage_runs"] if stage_run["stage_id"] == "refactor"
                )
                assert refactor_stage["artifacts"]
                assert all(
                    artifact["stage_id"] == "refactor" for artifact in refactor_stage["artifacts"]
                )
                assert all(
                    artifact["id"].startswith("refactor:step:") for artifact in refactor_stage["artifacts"]
                )
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_start_brownfield_run_creates_protocol_and_work_items(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.services.specification import PlanResult, SpecifyResult, TasksResult

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        spec_dir = repo / "specs" / "001-demo-feature"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_path = spec_dir / "spec.md"
        plan_path = spec_dir / "plan.md"
        tasks_path = spec_dir / "tasks.md"
        spec_path.write_text("# Demo feature\n", encoding="utf-8")
        plan_path.write_text("# Plan\n", encoding="utf-8")
        tasks_path.write_text(
            "## Phase 1: Setup\n- [ ] update README.md\n\n## Phase 2: Tests\n- [ ] add tests/test_demo.py\n",
            encoding="utf-8",
        )

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        other_protocol_root = repo / "specs" / "other-protocol" / "_runtime"
        other_protocol_root.mkdir(parents=True, exist_ok=True)
        other_run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="other-protocol",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(other_protocol_root),
        )
        other_step = db.create_step_run(
            protocol_run_id=other_run.id,
            step_index=1,
            step_name="step-01-other",
            step_type="execute",
            status="pending",
            assigned_agent="dev",
        )

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_specify",
            lambda self, project_path, description, feature_name=None, base_branch=None, project_id=None: SpecifyResult(
                success=True,
                spec_path=str(spec_path),
                spec_number=1,
                feature_name="demo-feature",
                spec_run_id=None,
                worktree_path=str(repo),
                branch_name="001-demo-feature",
                base_branch="main",
                spec_root=str(spec_dir),
            ),
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_plan",
            lambda self, project_path, spec_path, spec_run_id=None, project_id=None: PlanResult(
                success=True,
                plan_path=str(plan_path),
                spec_run_id=spec_run_id,
                worktree_path=str(repo),
            ),
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_tasks",
            lambda self, project_path, plan_path, spec_run_id=None, project_id=None: TasksResult(
                success=True,
                tasks_path=str(tasks_path),
                task_count=2,
                parallelizable_count=0,
                spec_run_id=spec_run_id,
                worktree_path=str(repo),
            ),
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                resp = client.post(
                    f"/projects/{project.id}/brownfield/run",
                    json={
                        "feature_request": "Add demo behavior to the brownfield project",
                        "feature_name": "demo-feature",
                        "output_mode": "task_cycle",
                        "owner_agent": "dev",
                        "helper_agents": ["trace", "tests"],
                    },
                )
                assert resp.status_code == 200
                payload = resp.json()
                assert payload["success"] is True
                assert payload["protocol"] is not None
                assert payload["next_work_item_id"] is not None
                assert len(payload["work_items"]) == 1
                assert payload["work_items"][0]["title"].startswith("step-01-")
                assert "demo-feature" in payload["work_items"][0]["title"]
                assert payload["work_items"][0]["owner_agent"] == "opencode"
                assert payload["work_items"][0]["helper_agents"] == ["trace", "tests"]

                listed = client.get(f"/projects/{project.id}/task-cycle")
                assert listed.status_code == 200
                listed_payload = listed.json()
                listed_ids = [item["id"] for item in listed_payload]
                assert payload["work_items"][0]["id"] in listed_ids
                assert other_step.id not in listed_ids
                hydrated_item = next(item for item in listed_payload if item["id"] == payload["work_items"][0]["id"])
                assert hydrated_item["context_status"] == "ready"
                assert hydrated_item["plan_status"] == "ready"
                assert hydrated_item["status"] == "plan_ready"
                assert Path(hydrated_item["artifact_refs"]["context_pack_json"]).exists()
                assert Path(hydrated_item["artifact_refs"]["plan_pack_json"]).exists()

                event_types = [event.event_type for event in db.list_recent_events(project_id=project.id, limit=20)]
                assert "brownfield_run_started" in event_types
                assert "brownfield_specify_completed" in event_types
                assert "brownfield_plan_completed" in event_types
                assert "brownfield_tasks_completed" in event_types
                assert "brownfield_protocol_seed_completed" in event_types
                assert "brownfield_run_completed" in event_types
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_autonomous_mode_runs_from_start_to_pr_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api import schemas
    from devgodzilla.cli.main import get_service_context as cli_get_service_context
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.qa.gates.interface import GateResult, GateVerdict
    from devgodzilla.services.quality import QAResult, QAVerdict
    from devgodzilla.services.specification import PlanResult, SpecifyResult, TasksResult
    from devgodzilla.services.task_cycle import TaskCycleService

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        spec_dir = repo / "specs" / "001-demo-feature"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_path = spec_dir / "spec.md"
        plan_path = spec_dir / "plan.md"
        tasks_path = spec_dir / "tasks.md"
        spec_path.write_text("# Demo feature\n", encoding="utf-8")
        plan_path.write_text("# Plan\n", encoding="utf-8")
        tasks_path.write_text(
            "## Phase 1: Setup\n- [ ] update README.md\n",
            encoding="utf-8",
        )

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
            task_cycle_autonomous=True,
        )

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_specify",
            lambda self, project_path, description, feature_name=None, base_branch=None, project_id=None: SpecifyResult(
                success=True,
                spec_path=str(spec_path),
                spec_number=1,
                feature_name="demo-feature",
                spec_run_id=None,
                worktree_path=str(repo),
                branch_name="001-demo-feature",
                base_branch="main",
                spec_root=str(spec_dir),
            ),
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_plan",
            lambda self, project_path, spec_path, spec_run_id=None, project_id=None: PlanResult(
                success=True,
                plan_path=str(plan_path),
                spec_run_id=spec_run_id,
                worktree_path=str(repo),
            ),
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_tasks",
            lambda self, project_path, plan_path, spec_run_id=None, project_id=None: TasksResult(
                success=True,
                tasks_path=str(tasks_path),
                task_count=1,
                parallelizable_count=0,
                spec_run_id=spec_run_id,
                worktree_path=str(repo),
            ),
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.PolicyService.evaluate_step",
            lambda self, step_run_id, repo_root=None: [],
        )

        def _fake_execute(self, step_run_id):
            step = db.get_step_run(step_run_id)
            run = db.get_protocol_run(step.protocol_run_id)
            protocol_root = Path(run.protocol_root)
            if not protocol_root.is_absolute():
                protocol_root = Path(run.worktree_path) / protocol_root
            artifacts_dir = protocol_root / ".devgodzilla" / "steps" / str(step_run_id) / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            (artifacts_dir / "execution.log").write_text("implemented\n", encoding="utf-8")
            (artifacts_dir / "git-status.txt").write_text("M README.md\n", encoding="utf-8")
            (artifacts_dir / "changes.diff").write_text(
                "diff --git a/README.md b/README.md\n+++ b/README.md\n",
                encoding="utf-8",
            )
            db.update_step_status(step_run_id, "completed", summary="implemented")
            return type("ExecutionResult", (), {"success": True, "error": None})()

        def _fake_run_qa(self, step_run_id, gates=None, skip_gates=None, **kwargs):
            return QAResult(
                step_run_id=step_run_id,
                verdict=QAVerdict.PASS,
                gate_results=[
                    GateResult(gate_id="lint", gate_name="Lint", verdict=GateVerdict.PASS),
                    GateResult(gate_id="type", gate_name="Type", verdict=GateVerdict.PASS),
                    GateResult(gate_id="test", gate_name="Test", verdict=GateVerdict.PASS),
                ],
                duration_seconds=0.1,
            )

        monkeypatch.setattr("devgodzilla.services.task_cycle.ExecutionService.execute_step", _fake_execute)
        monkeypatch.setattr("devgodzilla.services.task_cycle.QualityService.run_qa", _fake_run_qa)
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.QualityService.persist_verdict",
            lambda self, qa_result, step_run_id, report_path=None: None,
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.TaskCycleService._run_pr_ready_precommit",
            lambda self, workspace_root, changed_files=None: {
                "status": "passed",
                "summary": "pre-commit passed",
                "findings": [],
                "warnings": [],
                "command": "./.venv/bin/pre-commit run --files README.md",
            },
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.GitService.push_and_open_pr",
            lambda self, worktree, protocol_name, base_branch, github_token=None, changed_files=None, **kwargs: {
                "success": True,
                "status": "created",
                "url": "https://github.com/example/demo/pull/1",
                "message": "Pull request created",
            },
        )

        try:
            service = TaskCycleService(cli_get_service_context(), db)
            request = schemas.BrownfieldRunRequest(
                feature_request="Add demo behavior to the brownfield project",
                feature_name="demo-feature",
                output_mode="task_cycle",
                owner_agent="dev",
            )
            result = service.start_brownfield_run(project.id, request)
            work_item_id = result.next_work_item_id
            assert work_item_id is not None

            service.run_brownfield_bootstrap(
                project.id,
                request,
                protocol_run_id=result.protocol.id,
                step_run_id=work_item_id,
            )

            work_item = None
            for _ in range(20):
                work_item = service.get_work_item(work_item_id)
                if work_item.pr_ready or work_item.status in {"needs_rework", "blocked"}:
                    break
                time.sleep(0.05)

            assert work_item is not None
            assert work_item.pr_ready is True
            assert work_item.status == "pr_ready"
            assert work_item.plan_status == "ready"
            assert work_item.review_status == "passed"
            assert work_item.qa_status == "passed"
            assert Path(work_item.artifact_refs.pr_ready_report_json).exists()

            event_types = [event.event_type for event in db.list_recent_events(project_id=project.id, limit=30)]
            assert "brownfield_task_cycle_autonomous_started" in event_types
            assert "brownfield_task_cycle_autonomous_completed" in event_types
        finally:
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_reconciles_stale_brownfield_bootstrap_from_runtime_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )

        spec_dir = repo / "specs" / "026-demo-feature"
        runtime_dir = spec_dir / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "spec.md").write_text("# Demo feature\n", encoding="utf-8")
        (spec_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (spec_dir / "tasks.md").write_text("## Phase 1: Setup\n- [ ] update README.md\n", encoding="utf-8")
        (runtime_dir / "plan.md").write_text("# Runtime plan\n", encoding="utf-8")
        (runtime_dir / "step-01-demo-feature.md").write_text("# Step\n", encoding="utf-8")

        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planning",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=None,
        )
        db.update_protocol_windmill(
            run.id,
            speckit_metadata={
                "task_cycle": True,
                "brownfield_output_mode": "task_cycle",
                "brownfield_bootstrap_stage": "tasks",
                "brownfield_bootstrap_status": "running",
            },
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo-feature",
            step_type="execute",
            status="pending",
            assigned_agent="opencode",
        )
        db.update_step_run(
            step.id,
            runtime_state={
                "task_cycle": {
                    "status": "queued",
                    "bootstrap_stage": "tasks",
                    "bootstrap_status": "running",
                }
            },
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                resp = client.get(f"/work-items/{step.id}")
                assert resp.status_code == 200
                payload = resp.json()
                assert payload["active_stage"] == "build_context"
                assert payload["active_stage_status"] == "pending"
                assert payload["blocking_reason"] == "Context must be ready before planning"

                run_resp = client.get(f"/protocols/{run.id}")
                assert run_resp.status_code == 200
                run_payload = run_resp.json()
                assert run_payload["status"] == "planned"
                assert run_payload["protocol_root"] == "specs/026-demo-feature/_runtime"
                assert run_payload["speckit_metadata"]["brownfield_bootstrap_status"] == "completed"
                assert run_payload["speckit_metadata"]["tasks_path"].endswith("/specs/026-demo-feature/tasks.md")
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_start_brownfield_run_reuses_existing_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.services.specification import PlanResult, SpecifyResult, TasksResult

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        spec_dir = repo / "specs" / "001-demo-feature"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_path = spec_dir / "spec.md"
        plan_path = spec_dir / "plan.md"
        tasks_path = spec_dir / "tasks.md"
        spec_path.write_text("# Demo feature\n", encoding="utf-8")
        plan_path.write_text("# Plan\n", encoding="utf-8")
        tasks_path.write_text(
            "## Phase 1: Setup\n- [ ] update README.md\n\n## Phase 2: Tests\n- [ ] add tests/test_demo.py\n",
            encoding="utf-8",
        )

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_specify",
            lambda self, project_path, description, feature_name=None, base_branch=None, project_id=None: SpecifyResult(
                success=True,
                spec_path=str(spec_path),
                spec_number=1,
                feature_name="demo-feature",
                spec_run_id=None,
                worktree_path=str(repo),
                branch_name="001-demo-feature",
                base_branch="main",
                spec_root=str(spec_dir),
            ),
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_plan",
            lambda self, project_path, spec_path, spec_run_id=None, project_id=None: PlanResult(
                success=True,
                plan_path=str(plan_path),
                spec_run_id=spec_run_id,
                worktree_path=str(repo),
            ),
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_tasks",
            lambda self, project_path, plan_path, spec_run_id=None, project_id=None: TasksResult(
                success=True,
                tasks_path=str(tasks_path),
                task_count=2,
                parallelizable_count=0,
                spec_run_id=spec_run_id,
                worktree_path=str(repo),
            ),
        )

        payload = {
            "feature_request": "Add demo behavior to the brownfield project",
            "feature_name": "demo-feature",
            "output_mode": "task_cycle",
            "owner_agent": "dev",
        }

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                resp1 = client.post(f"/projects/{project.id}/brownfield/run", json=payload)
                resp2 = client.post(f"/projects/{project.id}/brownfield/run", json=payload)

                assert resp1.status_code == 200
                assert resp2.status_code == 200

                first = resp1.json()
                second = resp2.json()
                assert first["protocol"] is not None
                assert second["protocol"] is not None
                assert second["protocol"]["id"] == first["protocol"]["id"]
                assert "Reusing existing brownfield run" in second["warnings"]
                assert second["work_items"][0]["id"] == first["work_items"][0]["id"]

                protocol_runs = [
                    run
                    for run in db.list_protocol_runs(project.id)
                    if run.protocol_name == first["protocol"]["protocol_name"]
                ]
                assert len(protocol_runs) == 1
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_start_brownfield_run_emits_failure_events_for_plan_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.services.specification import PlanResult, SpecifyResult

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        spec_dir = repo / "specs" / "001-demo-feature"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_path = spec_dir / "spec.md"
        spec_path.write_text("# Demo feature\n", encoding="utf-8")

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_specify",
            lambda self, project_path, description, feature_name=None, base_branch=None, project_id=None: SpecifyResult(
                success=True,
                spec_path=str(spec_path),
                spec_number=1,
                feature_name="demo-feature",
                spec_run_id=11,
                worktree_path=str(repo),
                branch_name="001-demo-feature",
                base_branch="main",
                spec_root=str(spec_dir),
            ),
        )
        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.SpecificationService.run_plan",
            lambda self, project_path, spec_path, spec_run_id=None, project_id=None: PlanResult(
                success=False,
                error="Plan generation produced incomplete outputs",
                spec_run_id=spec_run_id,
                worktree_path=str(repo),
            ),
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                resp = client.post(
                    f"/projects/{project.id}/brownfield/run",
                    json={
                        "feature_request": "Add demo behavior to the brownfield project",
                        "feature_name": "demo-feature",
                        "output_mode": "task_cycle",
                    },
                )
                assert resp.status_code == 200
                payload = resp.json()
                assert payload["protocol"] is not None
                assert payload["next_work_item_id"] is not None

                event_types = [event.event_type for event in db.list_recent_events(project_id=project.id, limit=20)]
                assert "brownfield_specify_completed" in event_types
                assert "brownfield_plan_failed" in event_types
                assert "brownfield_run_failed" in event_types
                work_item = client.get(f"/work-items/{payload['next_work_item_id']}").json()
                assert work_item["status"] == "blocked"
                assert "Plan generation produced incomplete outputs" in (work_item["blocking_reason"] or "")
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_failed_review_writes_rework_pack_and_exposes_artifact_content(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="failed",
            assigned_agent="dev",
        )

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.PolicyService.evaluate_step",
            lambda self, step_run_id, repo_root=None: [],
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                context_resp = client.post(f"/work-items/{step.id}/build-context", json={"refresh": False})
                assert context_resp.status_code == 200
                assert client.post(f"/work-items/{step.id}/plan", json={"refresh": False}).status_code == 200

                review_resp = client.post(f"/work-items/{step.id}/actions/review")
                assert review_resp.status_code == 200
                assert review_resp.json()["verdict"] == "failed"

                work_item_resp = client.get(f"/work-items/{step.id}")
                assert work_item_resp.status_code == 200
                rework_path = Path(work_item_resp.json()["artifact_refs"]["rework_pack_json"])
                assert rework_path.exists()
                rework = json.loads(rework_path.read_text(encoding="utf-8"))
                assert rework["source"] == "review"

                artifact_resp = client.get(f"/work-items/{step.id}/artifacts/rework_pack_json/content")
                assert artifact_resp.status_code == 200
                assert "\"source\": \"review\"" in artifact_resp.json()["content"]
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_implement_respects_max_iterations(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.models.domain import StepStatus
    from devgodzilla.services.execution import ExecutionResult

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.setenv("DEVGODZILLA_TASK_CYCLE_MAX_ITERATIONS", "2")
        monkeypatch.setenv("DEVGODZILLA_EXEC_ENGINE_ID", "opencode")
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="pending",
            assigned_agent="dev",
        )

        def _fake_execute(self, step_run_id):
            self.db.update_step_status(step_run_id, StepStatus.FAILED, summary="forced failure")
            return ExecutionResult(success=False, step_run_id=step_run_id, engine_id="dummy", error="forced failure")

        monkeypatch.setattr("devgodzilla.services.task_cycle.ExecutionService.execute_step", _fake_execute)

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                assert client.post(f"/work-items/{step.id}/build-context", json={"refresh": False}).status_code == 200
                assert client.post(f"/work-items/{step.id}/plan", json={"refresh": False}).status_code == 200
                first = client.post(f"/work-items/{step.id}/actions/implement", json={"owner_agent": "dev"})
                assert first.status_code == 200
                assert first.json()["iteration_count"] == 1

                second = client.post(f"/work-items/{step.id}/actions/implement", json={"owner_agent": "dev"})
                assert second.status_code == 200
                assert second.json()["iteration_count"] == 2

                third = client.post(f"/work-items/{step.id}/actions/implement", json={"owner_agent": "dev"})
                assert third.status_code == 409
                assert "Max task-cycle iterations reached" in third.json()["detail"]
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_qa_requires_reviewable_implementation_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="failed",
            assigned_agent="dev",
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                context_resp = client.post(f"/work-items/{step.id}/build-context", json={"refresh": False})
                assert context_resp.status_code == 200
                assert client.post(f"/work-items/{step.id}/plan", json={"refresh": False}).status_code == 200

                qa_resp = client.post(f"/work-items/{step.id}/actions/qa", json={"gates": ["lint"]})
                assert qa_resp.status_code == 400
                assert "qa-ready state" in qa_resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_implement_applies_project_stage_override(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.models.domain import StepStatus
    from devgodzilla.services.execution import ExecutionResult

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        db.upsert_agent_assignment(
            project.id,
            "task_cycle_implement",
            {
                "agent_id": "codex",
                "model_override": "gpt-5.3-codex",
                "metadata": {"reasoning_effort": "high"},
            },
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="pending",
            assigned_agent="opencode",
        )

        captured = {}

        def _fake_execute(self, step_run_id):
            current = self.db.get_step_run(step_run_id)
            task_cycle = dict((current.runtime_state or {}).get("task_cycle") or {})
            captured["active_stage_override"] = task_cycle.get("active_stage_override")
            self.db.update_step_status(step_run_id, StepStatus.COMPLETED, summary="implemented")
            return ExecutionResult(success=True, step_run_id=step_run_id, engine_id="codex")

        monkeypatch.setattr("devgodzilla.services.task_cycle.ExecutionService.execute_step", _fake_execute)

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                assert client.post(f"/work-items/{step.id}/build-context", json={"refresh": False}).status_code == 200
                assert client.post(f"/work-items/{step.id}/plan", json={"refresh": False}).status_code == 200
                resp = client.post(f"/work-items/{step.id}/actions/implement", json={})
                assert resp.status_code == 200
                assert resp.json()["status"] == "awaiting_review"
                assert captured["active_stage_override"] == {
                    "stage": "implement",
                    "agent_id": "codex",
                    "model_override": "gpt-5.3-codex",
                    "reasoning_effort": "high",
                }
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_qa_applies_project_stage_override(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.qa.gates.interface import GateResult, GateVerdict
    from devgodzilla.services.quality import QAResult, QAVerdict

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        db.upsert_agent_assignment(
            project.id,
            "task_cycle_qa",
            {
                "agent_id": "codex",
                "model_override": "gpt-5.4-codex",
                "metadata": {"reasoning_effort": "xhigh"},
            },
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (protocol_root / "step-01-demo.md").write_text("# Demo step\n", encoding="utf-8")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="completed",
            assigned_agent="opencode",
        )
        artifacts_dir = protocol_root / ".devgodzilla" / "steps" / str(step.id) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "execution.log").write_text("implemented\n", encoding="utf-8")

        monkeypatch.setattr(
            "devgodzilla.services.task_cycle.PolicyService.evaluate_step",
            lambda self, step_run_id, repo_root=None: [],
        )

        captured = {}

        def _fake_run_qa(self, step_run_id, gates=None, skip_gates=None, engine_id=None, model=None, runtime_options=None):
            captured["engine_id"] = engine_id
            captured["model"] = model
            captured["runtime_options"] = runtime_options
            return QAResult(
                step_run_id=step_run_id,
                verdict=QAVerdict.PASS,
                gate_results=[
                    GateResult(gate_id="lint", gate_name="Lint", verdict=GateVerdict.PASS),
                ],
                duration_seconds=0.1,
            )

        monkeypatch.setattr("devgodzilla.services.task_cycle.QualityService.run_qa", _fake_run_qa)
        monkeypatch.setattr("devgodzilla.services.task_cycle.QualityService.persist_verdict", lambda self, qa_result, step_run_id, report_path=None: None)

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                context_resp = client.post(f"/work-items/{step.id}/build-context", json={"refresh": False})
                assert context_resp.status_code == 200

                review_resp = client.post(f"/work-items/{step.id}/actions/review")
                assert review_resp.status_code == 200

                qa_resp = client.post(f"/work-items/{step.id}/actions/qa", json={"gates": ["lint"]})
                assert qa_resp.status_code == 200
                assert captured["engine_id"] == "codex"
                assert captured["model"] == "gpt-5.4-codex"
                assert captured["runtime_options"] == {"reasoning_effort": "xhigh"}
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_lifecycle_actions_and_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        active_step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-active",
            step_type="execute",
            status="pending",
            assigned_agent="dev",
        )
        archived_step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=2,
            step_name="step-02-archived",
            step_type="execute",
            status="pending",
            assigned_agent="dev",
        )
        canceled_step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=3,
            step_name="step-03-canceled",
            step_type="execute",
            status="pending",
            assigned_agent="dev",
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                archive_resp = client.post(
                    f"/work-items/{archived_step.id}/actions/archive",
                    json={"reason": "duplicate work item"},
                )
                assert archive_resp.status_code == 200
                assert archive_resp.json()["lifecycle_state"] == "archived"

                cancel_resp = client.post(
                    f"/work-items/{canceled_step.id}/actions/cancel",
                    json={"reason": "wrong feature"},
                )
                assert cancel_resp.status_code == 200
                assert cancel_resp.json()["lifecycle_state"] == "canceled"

                active_list = client.get(f"/projects/{project.id}/task-cycle")
                assert active_list.status_code == 200
                assert [item["id"] for item in active_list.json()] == [active_step.id]

                all_list = client.get(f"/projects/{project.id}/task-cycle?lifecycle=all")
                assert all_list.status_code == 200
                assert {item["id"] for item in all_list.json()} == {
                    active_step.id,
                    archived_step.id,
                    canceled_step.id,
                }

                archived_list = client.get(f"/projects/{project.id}/task-cycle?lifecycle=archived")
                assert archived_list.status_code == 200
                assert [item["id"] for item in archived_list.json()] == [archived_step.id]

                canceled_list = client.get(f"/projects/{project.id}/task-cycle?lifecycle=canceled")
                assert canceled_list.status_code == 200
                assert [item["id"] for item in canceled_list.json()] == [canceled_step.id]

                implement_resp = client.post(f"/work-items/{archived_step.id}/actions/implement", json={})
                assert implement_resp.status_code == 409
                assert "read-only" in implement_resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_task_cycle_can_reassign_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        projects_root = tmp / "projects-root"
        _init_repo(repo)

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(projects_root))
        monkeypatch.setenv("DEVGODZILLA_EXEC_ENGINE_ID", "opencode")
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / "specs" / "demo-feature" / "_runtime"
        protocol_root.mkdir(parents=True, exist_ok=True)
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-feature",
            status="planned",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="pending",
            assigned_agent="dev",
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                reassign_resp = client.post(
                    f"/work-items/{step.id}/actions/reassign-owner",
                    json={"owner_agent": "codex"},
                )
                assert reassign_resp.status_code == 200
                assert reassign_resp.json()["owner_agent"] == "codex"
                assert db.get_step_run(step.id).assigned_agent == "codex"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()
