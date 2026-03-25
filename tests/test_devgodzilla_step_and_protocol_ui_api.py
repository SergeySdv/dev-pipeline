from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
    from devgodzilla.api.app import app
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore
    app = None  # type: ignore


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_list_step_runs_returns_job_runs_for_step(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="running",
            base_branch="main",
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="completed",
            assigned_agent="opencode",
        )
        db.create_job_run(
            run_id="run-step-1",
            job_type="execute",
            status="succeeded",
            run_kind="engine",
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(f"/steps/{step.id}/runs")
                assert response.status_code == 200
                payload = response.json()
                assert len(payload) == 1
                assert payload[0]["run_id"] == "run-step-1"
                assert payload[0]["step_run_id"] == step.id
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_list_step_runs_syncs_windmill_status(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.api.routes import steps as steps_route
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.windmill.client import JobStatus

    class FakeWindmill:
        def get_job(self, _job_id: str):
            return type(
                "Job",
                (),
                {
                    "status": JobStatus.COMPLETED,
                    "started_at": "2026-03-09T00:00:00Z",
                    "completed_at": "2026-03-09T00:01:00Z",
                    "result": {"ok": True},
                    "error": None,
                },
            )()

        def close(self):
            return None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="running",
            base_branch="main",
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="completed",
            assigned_agent="opencode",
        )
        db.create_job_run(
            run_id="run-step-1",
            job_type="execute",
            status="queued",
            run_kind="engine",
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
            windmill_job_id="wm-1",
        )
        monkeypatch.setattr(steps_route, "_build_windmill_client", lambda: FakeWindmill())

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(f"/steps/{step.id}/runs")
                assert response.status_code == 200
                payload = response.json()
                assert payload[0]["status"] == "succeeded"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_get_protocol_sprint_filters_protocol_linked_tasks_without_db_specific_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        sprint = db.create_sprint(project.id, "Sprint 1", status="active")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="running",
            base_branch="main",
        )
        db.create_task(
            project_id=project.id,
            title="Linked task",
            sprint_id=sprint.id,
            protocol_run_id=run.id,
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(f"/protocols/{run.id}/sprint")
                assert response.status_code == 200
                payload = response.json()
                assert payload is not None
                assert payload["id"] == sprint.id
                assert payload["name"] == "Sprint 1"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_link_protocol_to_sprint_persists_explicit_protocol_link_without_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        sprint = db.create_sprint(project.id, "Sprint Link", status="active")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="running",
            base_branch="main",
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                link_response = client.post(
                    f"/sprints/{sprint.id}/actions/link-protocol",
                    json={"protocol_run_id": run.id, "auto_sync": False},
                )
                sprint_response = client.get(f"/protocols/{run.id}/sprint")
                protocol_response = client.get(f"/protocols/{run.id}")

            assert link_response.status_code == 200
            assert sprint_response.status_code == 200
            assert protocol_response.status_code == 200

            payload = sprint_response.json()
            assert payload is not None
            assert payload["id"] == sprint.id
            assert payload["name"] == "Sprint Link"
            assert protocol_response.json()["linked_sprint_id"] == sprint.id
            assert db.get_protocol_run(run.id).linked_sprint_id == sprint.id
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_create_sprint_from_protocol_persists_explicit_protocol_link_without_auto_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="running",
            base_branch="main",
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                create_response = client.post(
                    f"/protocols/{run.id}/actions/create-sprint",
                    json={"auto_sync": False},
                )
                assert create_response.status_code == 200
                sprint_payload = create_response.json()
                sprint_response = client.get(f"/protocols/{run.id}/sprint")
                protocol_response = client.get(f"/protocols/{run.id}")

            assert sprint_response.status_code == 200
            assert protocol_response.status_code == 200
            assert sprint_response.json()["id"] == sprint_payload["id"]
            assert protocol_response.json()["linked_sprint_id"] == sprint_payload["id"]
            assert db.get_protocol_run(run.id).linked_sprint_id == sprint_payload["id"]
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_protocol_sync_to_sprint_requires_body_sprint_id_and_persists_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        sprint = db.create_sprint(project.id, "Sprint Sync", status="active")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="running",
            base_branch="main",
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01-demo",
            step_type="execute",
            status="pending",
        )

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                missing_response = client.post(f"/protocols/{run.id}/actions/sync-to-sprint", json={})
                sync_response = client.post(
                    f"/protocols/{run.id}/actions/sync-to-sprint",
                    json={"sprint_id": sprint.id},
                )
                sprint_response = client.get(f"/protocols/{run.id}/sprint")
                protocol_response = client.get(f"/protocols/{run.id}")

            assert missing_response.status_code == 422
            assert sync_response.status_code == 200
            assert sync_response.json()["sprint_id"] == sprint.id
            assert sync_response.json()["protocol_run_id"] == run.id
            assert sync_response.json()["tasks_synced"] == 1
            assert sprint_response.json()["id"] == sprint.id
            assert protocol_response.json()["linked_sprint_id"] == sprint.id

            tasks = db.list_tasks(step_run_id=step.id, limit=10)
            assert len(tasks) == 1
            assert tasks[0].sprint_id == sprint.id
            assert db.get_protocol_run(run.id).linked_sprint_id == sprint.id
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_retry_latest_step_uses_orchestrator_without_leaving_manual_pending_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db, get_service_context
    from devgodzilla.api.routes import protocols as protocols_route
    from devgodzilla.config import _reset_config_for_tests, load_config
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.services.base import ServiceContext

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="blocked",
            base_branch="main",
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=0,
            step_name="step-01-demo",
            step_type="execute",
            status="blocked",
            assigned_agent="opencode",
        )

        calls: list[int] = []
        fake_orchestrator = Mock()

        def fake_retry_step(step_run_id: int):
            calls.append(step_run_id)
            db.update_protocol_status(run.id, "running")
            db.update_step_status(step_run_id, "running", retries=1)
            return type("Result", (), {"success": True, "error": None, "message": "retry started"})()

        fake_orchestrator.retry_step.side_effect = fake_retry_step
        monkeypatch.setattr(protocols_route, "_build_orchestrator", lambda ctx, db_dep: fake_orchestrator)

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_service_context] = lambda: ServiceContext(config=load_config())
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.post(f"/protocols/{run.id}/actions/retry_latest")
                assert response.status_code == 200
                payload = response.json()
                assert payload["step_run_id"] == step.id
                assert payload["step_name"] == step.step_name
                assert payload["message"] == "retry started"
                assert payload["retries"] == 1
                assert calls == [step.id]
                assert db.get_protocol_run(run.id).status == "running"
                assert db.get_step_run(step.id).status == "running"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_retry_latest_step_recovers_blocked_protocol_with_runnable_pending_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db, get_service_context
    from devgodzilla.api.routes import protocols as protocols_route
    from devgodzilla.config import _reset_config_for_tests, load_config
    from devgodzilla.db.database import SQLiteDatabase
    from devgodzilla.services.base import ServiceContext

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="blocked",
            base_branch="main",
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=0,
            step_name="step-01-demo",
            step_type="execute",
            status="pending",
            assigned_agent="opencode",
        )
        db.update_step_status(step.id, "pending", retries=1)
        db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-02-demo",
            step_type="execute",
            status="pending",
            assigned_agent="opencode",
            depends_on=[step.id],
        )

        fake_orchestrator = Mock()
        calls: list[int] = []

        def fake_run_step(step_run_id: int):
            calls.append(step_run_id)
            db.update_step_status(step_run_id, "running", retries=1)
            return type("Result", (), {"success": True, "error": None, "message": "resumed pending step"})()

        fake_orchestrator.run_step.side_effect = fake_run_step
        monkeypatch.setattr(protocols_route, "_build_orchestrator", lambda ctx, db_dep: fake_orchestrator)

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_service_context] = lambda: ServiceContext(config=load_config())
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.post(f"/protocols/{run.id}/actions/retry_latest")
                assert response.status_code == 200
                payload = response.json()
                assert payload["step_run_id"] == step.id
                assert payload["step_name"] == step.step_name
                assert payload["message"] == "resumed pending step"
                assert payload["retries"] == 1
                assert calls == [step.id]
                assert db.get_protocol_run(run.id).status == "running"
                assert db.get_step_run(step.id).status == "running"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_get_protocol_exposes_canonical_protocol_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")
        sprint = db.create_sprint(project.id, "Sprint Canonical", status="active")
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-protocol",
            status="running",
            base_branch="main",
            description="Canonical protocol description",
        )
        db.update_protocol_paths(
            run.id,
            worktree_path=str(tmp / "worktrees" / "demo"),
            protocol_root=str(tmp / "worktrees" / "demo" / ".devgodzilla" / "protocols" / "demo"),
        )
        db.update_protocol_template(
            run.id,
            template_config={"mode": "brownfield"},
            template_source={"kind": "builtin", "name": "brownfield/default"},
        )
        db.update_protocol_policy_audit(
            run.id,
            policy_pack_key="repo/default",
            policy_pack_version="1.2.3",
            policy_effective_hash="policy-hash",
            policy_effective_json={"mode": "warn"},
        )
        db.update_protocol_windmill(
            run.id,
            windmill_flow_id="flow-123",
            speckit_metadata={
                "spec_run_id": 91,
                "spec_hash": "abc123",
                "validation_status": "validated",
                "validated_at": "2026-03-09T10:00:00Z",
            },
        )
        db.update_protocol_linked_sprint(run.id, sprint.id)

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(f"/protocols/{run.id}")

            assert response.status_code == 200
            payload = response.json()
            assert payload["description"] == "Canonical protocol description"
            assert payload["protocol_root"].endswith("/.devgodzilla/protocols/demo")
            assert payload["template_config"] == {"mode": "brownfield"}
            assert payload["template_source"] == {
                "kind": "builtin",
                "name": "brownfield/default",
            }
            assert payload["policy_pack_key"] == "repo/default"
            assert payload["policy_pack_version"] == "1.2.3"
            assert payload["policy_effective_hash"] == "policy-hash"
            assert payload["policy_effective_json"] == {"mode": "warn"}
            assert payload["windmill_flow_id"] == "flow-123"
            assert payload["speckit_metadata"] == {
                "spec_run_id": 91,
                "spec_hash": "abc123",
                "validation_status": "validated",
                "validated_at": "2026-03-09T10:00:00Z",
            }
            assert payload["linked_sprint_id"] == sprint.id
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_create_project_protocol_persists_template_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.post(
                    f"/projects/{project.id}/protocols",
                    json={
                        "protocol_name": "demo-protocol",
                        "base_branch": "main",
                        "template_source": "./templates/feature.yaml",
                    },
                )

            assert response.status_code == 200
            payload = response.json()
            assert payload["template_source"] == "./templates/feature.yaml"
            assert db.get_protocol_run(payload["id"]).template_source == "./templates/feature.yaml"
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_create_global_protocol_persists_template_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.post(
                    "/protocols",
                    json={
                        "project_id": project.id,
                        "name": "demo-protocol",
                        "branch_name": "main",
                        "template": "./templates/global.yaml",
                        "inputs": {"mode": "brownfield"},
                    },
                )

            assert response.status_code == 200
            payload = response.json()
            assert payload["template_source"] == "./templates/global.yaml"
            assert payload["template_config"] == {"mode": "brownfield"}
            run = db.get_protocol_run(payload["id"])
            assert run.template_source == "./templates/global.yaml"
            assert run.template_config == {"mode": "brownfield"}
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_create_global_protocol_accepts_canonical_request_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.post(
                    "/protocols",
                    json={
                        "project_id": project.id,
                        "protocol_name": "canonical-protocol",
                        "description": "Canonical request shape",
                        "base_branch": "develop",
                        "template_source": "./templates/canonical.yaml",
                        "template_config": {"mode": "brownfield"},
                    },
                )

            assert response.status_code == 200
            payload = response.json()
            assert payload["protocol_name"] == "canonical-protocol"
            assert payload["base_branch"] == "develop"
            assert payload["template_source"] == "./templates/canonical.yaml"
            assert payload["template_config"] == {"mode": "brownfield"}
            run = db.get_protocol_run(payload["id"])
            assert run.protocol_name == "canonical-protocol"
            assert run.base_branch == "develop"
            assert run.template_source == "./templates/canonical.yaml"
            assert run.template_config == {"mode": "brownfield"}
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_create_project_protocol_accepts_legacy_aliases_for_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devgodzilla.api.dependencies import get_db
    from devgodzilla.config import _reset_config_for_tests
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        _reset_config_for_tests()

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(name="demo", git_url="git@example.com:demo/repo.git", base_branch="main")

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.post(
                    f"/projects/{project.id}/protocols",
                    json={
                        "name": "legacy-project-protocol",
                        "branch_name": "release",
                        "template": "./templates/legacy.yaml",
                        "inputs": {"mode": "guided"},
                    },
                )

            assert response.status_code == 200
            payload = response.json()
            assert payload["protocol_name"] == "legacy-project-protocol"
            assert payload["base_branch"] == "release"
            assert payload["template_source"] == "./templates/legacy.yaml"
            assert payload["template_config"] == {"mode": "guided"}
        finally:
            app.dependency_overrides.clear()
            _reset_config_for_tests()
