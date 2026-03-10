import json
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
        (artifacts_dir / "changes.diff").write_text("diff --git a/README.md b/README.md\n", encoding="utf-8")

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

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                context_resp = client.post(f"/work-items/{step.id}/build-context", json={"refresh": False})
                assert context_resp.status_code == 200

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
                listed_ids = [item["id"] for item in listed.json()]
                assert payload["work_items"][0]["id"] in listed_ids
                assert other_step.id not in listed_ids
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
