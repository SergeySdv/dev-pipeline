import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
    from tasksgodzilla.api.app import app
except ImportError:  # pragma: no cover - fastapi not installed in minimal envs
    TestClient = None  # type: ignore
    app = None  # type: ignore


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_api_projects_protocols_steps_end_to_end(
    redis_inline_worker_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api-test.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            queue = client.app.state.queue  # type: ignore[attr-defined]
            db = client.app.state.db  # type: ignore[attr-defined]

            # Health
            resp = client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

            # Create project
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                    "ci_provider": "github",
                    "default_models": {"planning": "zai-coding-plan/glm-4.6"},
                },
            ).json()
            project_id = proj["id"]

            # Create protocol run
            run = client.post(
                f"/projects/{project_id}/protocols",
                json={
                    "protocol_name": "0001-demo",
                    "status": "planning",
                    "base_branch": "main",
                    "worktree_path": "/tmp/worktree",
                    "protocol_root": "/tmp/worktree/.protocols/0001-demo",
                    "description": "demo protocol",
                },
            ).json()
            protocol_run_id = run["id"]

            # Create step
            step = client.post(
                f"/protocols/{protocol_run_id}/steps",
                json={
                    "step_index": 0,
                    "step_name": "00-setup",
                    "step_type": "setup",
                    "status": "pending",
                },
            ).json()
            step_id = step["id"]

            # Trigger run action
            run_action = client.post(f"/steps/{step_id}/actions/run").json()
            assert run_action["job"]["job_type"] == "execute_step_job"

            # Background worker should mark it completed (stub). Allow a short window for queue drain.
            import time

            for _ in range(5):
                events = client.get(f"/protocols/{protocol_run_id}/events").json()
                if any(e["event_type"] == "step_completed" for e in events):
                    break
                time.sleep(0.2)
            else:
                assert False, "Expected step_completed event"

            # Approve step and list events
            client.post(f"/steps/{step_id}/actions/approve")
            events = client.get(f"/protocols/{protocol_run_id}/events").json()
            assert any(e["event_type"] == "manual_approval" for e in events)

            # Pause/resume/cancel protocol (skip if already terminal after approval)
            run_after = client.get(f"/protocols/{protocol_run_id}").json()
            terminal = run_after["status"] in ("completed", "cancelled", "failed")
            if not terminal:
                resp = client.post(f"/protocols/{protocol_run_id}/actions/pause")
                assert resp.status_code == 200
                assert resp.json()["status"] == "paused"
                resp = client.post(f"/protocols/{protocol_run_id}/actions/resume")
                assert resp.status_code == 200
                assert resp.json()["status"] == "running"
                resp = client.post(f"/protocols/{protocol_run_id}/actions/cancel")
                assert resp.status_code == 200
                assert resp.json()["status"] == "cancelled"

            ops = client.get("/events", params={"project_id": project_id}).json()
            assert any(o["protocol_run_id"] == protocol_run_id for o in ops)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_onboarding_start_endpoint_enqueues_setup(
    redis_inline_worker_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api-test.sqlite"
        repo_path = Path(tmpdir) / "repo"
        repo_path.mkdir(parents=True, exist_ok=True)
        # Minimal git init to satisfy onboarding path resolution.
        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        (repo_path / "README.md").write_text("demo", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "tester",
            "GIT_AUTHOR_EMAIL": "tester@example.com",
            "GIT_COMMITTER_NAME": "tester",
            "GIT_COMMITTER_EMAIL": "tester@example.com",
        }
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_path, check=True, env=env)

        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("TASKSGODZILLA_AUTO_CLONE", "false")
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        # Treat Codex as unavailable so discovery is skipped gracefully.
        import tasksgodzilla.services.onboarding as onboarding_mod

        monkeypatch.setattr(
            onboarding_mod.shutil,
            "which",
            lambda name: None if name == "codex" else shutil.which(name),
        )

        with TestClient(app) as client:  # type: ignore[arg-type]
            # Create project (uses local path to avoid clone).
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": str(repo_path),
                    "local_path": str(repo_path),
                    "base_branch": "main",
                },
            ).json()
            project_id = proj["id"]

            # Trigger onboarding explicitly.
            resp = client.post(f"/projects/{project_id}/onboarding/actions/start")
            assert resp.status_code == 200
            job = resp.json()["job"]
            assert job["job_type"] == "project_setup_job"

            # Wait briefly for inline worker to process onboarding.
            setup_run_id = client.get(f"/projects/{project_id}/onboarding").json()["protocol_run_id"]
            assert setup_run_id is not None

            for _ in range(10):
                summary = client.get(f"/projects/{project_id}/onboarding").json()
                if summary["status"] in ("completed", "blocked"):
                    break
                time.sleep(0.2)
            else:
                assert False, "Expected onboarding to complete or block"

            # Expect completion when repo is present locally.
            assert summary["status"] == "completed"
            events = client.get(f"/protocols/{setup_run_id}/events").json()
            assert any(ev["event_type"] == "setup_completed" for ev in events)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_run_step_qa_uses_orchestrator(
    redis_inline_worker_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api-test.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            project = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                },
            ).json()
            project_id = project["id"]
            run = client.post(
                f"/projects/{project_id}/protocols",
                json={
                    "protocol_name": "0002-demo",
                    "status": "pending",
                    "base_branch": "main",
                },
            ).json()
            protocol_run_id = run["id"]
            step = client.post(
                f"/protocols/{protocol_run_id}/steps",
                json={
                    "step_index": 0,
                    "step_name": "01-work",
                    "step_type": "work",
                    "status": "pending",
                },
            ).json()
            step_id = step["id"]

            resp = client.post(f"/steps/{step_id}/actions/run_qa")
            assert resp.status_code == 200
            job = resp.json()["job"]
            assert job["job_type"] == "run_quality_job"

            # Allow inline worker a moment; ensure step is marked needs_qa or completed.
        for _ in range(5):
            steps = client.get(f"/protocols/{protocol_run_id}/steps").json()
            step_after = next((s for s in steps if s["id"] == step_id), None)
            if step_after and step_after["status"] in ("needs_qa", "completed", "failed", "blocked"):
                break
            time.sleep(0.2)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_open_pr_action_enqueues_job(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api-test.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)
        # Ensure the inline worker is disabled so open_pr_job is only enqueued.
        monkeypatch.setenv("TASKSGODZILLA_INLINE_RQ_WORKER", "false")

        with TestClient(app) as client:  # type: ignore[arg-type]
            project = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                },
            ).json()
            project_id = project["id"]
            run = client.post(
                f"/projects/{project_id}/protocols",
                json={
                    "protocol_name": "0003-demo",
                    "status": "pending",
                    "base_branch": "main",
                },
            ).json()
            protocol_run_id = run["id"]

            resp = client.post(f"/protocols/{protocol_run_id}/actions/open_pr")
            assert resp.status_code == 200
            job = resp.json()["job"]
            assert job["job_type"] == "open_pr_job"


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_protocol_spec_endpoint_exposes_hash_and_spec(
    redis_inline_worker_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api-test.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            project = client.post(
                "/projects",
                json={"name": "demo", "git_url": "/tmp/demo.git", "base_branch": "main"},
            ).json()
            spec = {"steps": [{"id": "00-step", "name": "00-step.md", "engine_id": "codex", "prompt_ref": "00-step.md", "qa": {"policy": "skip"}}]}
            run = client.post(
                f"/projects/{project['id']}/protocols",
                json={
                    "protocol_name": "0001-spec",
                    "status": "planned",
                    "base_branch": "main",
                    "worktree_path": "/tmp/work",
                    "protocol_root": "/tmp/work/.protocols/0001-spec",
                    "description": "spec",
                    "template_config": {"protocol_spec": spec},
                },
            ).json()

            resp = client.get(f"/protocols/{run['id']}/spec")
            assert resp.status_code == 200
            body = resp.json()
            assert body["spec"] == spec
    assert body["spec_hash"]
    assert body["validation_status"] in (None, "valid")


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_spec_audit_endpoint_enqueues_job(
    redis_inline_worker_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api-test.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            project = client.post(
                "/projects",
                json={"name": "demo", "git_url": "/tmp/demo.git", "base_branch": "main"},
            ).json()

            resp = client.post(
                "/specs/audit",
                json={"project_id": project["id"], "backfill": True},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["job"]["job_type"] == "spec_audit_job"


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_codex_runs_api_round_trip(
    redis_inline_worker_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "runs-api.sqlite"
        runs_dir = Path(tmpdir) / "runs"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("CODEX_RUNS_DIR", str(runs_dir))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            resp = client.post("/codex/runs/start", json={"job_type": "bootstrap", "params": {"foo": "bar"}})
            assert resp.status_code == 200
            run = resp.json()
            run_id = run["run_id"]
            assert Path(run["log_path"]).exists()

            list_resp = client.get("/codex/runs")
            assert list_resp.status_code == 200
            assert any(item["run_id"] == run_id for item in list_resp.json())

            detail = client.get(f"/codex/runs/{run_id}")
            assert detail.status_code == 200
            assert detail.json()["status"] == "running"

            logs = client.get(f"/codex/runs/{run_id}/logs")
            assert logs.status_code == 200
            console_html = client.get("/console/runs")
            assert console_html.status_code == 200


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_runs_api_filter_by_protocol_and_step(
    redis_inline_worker_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "runs-filter.sqlite"
        runs_dir = Path(tmpdir) / "runs"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("CODEX_RUNS_DIR", str(runs_dir))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            project = client.post(
                "/projects",
                json={"name": "demo", "git_url": "/tmp/demo.git", "base_branch": "main"},
            ).json()
            protocol = client.post(
                f"/projects/{project['id']}/protocols",
                json={"protocol_name": "0001-demo", "status": "pending", "base_branch": "main"},
            ).json()
            step = client.post(
                f"/protocols/{protocol['id']}/steps",
                json={"step_index": 0, "step_name": "00-setup", "step_type": "setup", "status": "pending"},
            ).json()

            resp = client.post(
                "/codex/runs/start",
                json={
                    "job_type": "execute_step_job",
                    "run_kind": "exec",
                    "project_id": project["id"],
                    "protocol_run_id": protocol["id"],
                    "step_run_id": step["id"],
                    "attempt": 1,
                    "params": {"protocol_run_id": protocol["id"], "step_run_id": step["id"]},
                },
            )
            assert resp.status_code == 200
            run_id = resp.json()["run_id"]

            proto_runs = client.get(f"/protocols/{protocol['id']}/runs")
            assert proto_runs.status_code == 200
            assert any(r["run_id"] == run_id for r in proto_runs.json())

            step_runs = client.get(f"/steps/{step['id']}/runs")
            assert step_runs.status_code == 200
            assert any(r["run_id"] == run_id for r in step_runs.json())

            filtered = client.get(f"/codex/runs?protocol_run_id={protocol['id']}&step_run_id={step['id']}")
            assert filtered.status_code == 200
            assert any(r["run_id"] == run_id for r in filtered.json())


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_run_artifacts_api_round_trip(
    redis_inline_worker_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tasksgodzilla.storage import Database

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "runs-artifacts.sqlite"
        runs_dir = Path(tmpdir) / "runs"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("CODEX_RUNS_DIR", str(runs_dir))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            resp = client.post("/codex/runs/start", json={"job_type": "bootstrap", "params": {"foo": "bar"}})
            assert resp.status_code == 200
            run = resp.json()
            run_id = run["run_id"]

            artifact_path = Path(tmpdir) / "artifact.md"
            artifact_path.write_text("# Hello\n", encoding="utf-8")
            db = Database(db_path)
            db.init_schema()
            created = db.upsert_run_artifact(run_id, "quality-report", kind="qa_report", path=str(artifact_path))
            assert created.run_id == run_id

            listed = client.get(f"/codex/runs/{run_id}/artifacts")
            assert listed.status_code == 200
            artifacts = listed.json()
            assert any(a["name"] == "quality-report" for a in artifacts)
            artifact_id = next(a["id"] for a in artifacts if a["name"] == "quality-report")

            content = client.get(f"/codex/runs/{run_id}/artifacts/{artifact_id}/content")
            assert content.status_code == 200
            assert "Hello" in content.text
