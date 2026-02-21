import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
    from devgodzilla.api.app import app
    from devgodzilla.api.dependencies import get_windmill_client
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore
    app = None  # type: ignore
    get_windmill_client = None  # type: ignore


@dataclass
class _CreateFlowCall:
    path: str
    definition: Dict[str, Any]


class FakeWindmillClient:
    def __init__(self) -> None:
        self.create_flow_calls: List[_CreateFlowCall] = []

    def list_flows(self, prefix: Optional[str] = None) -> list[Any]:
        flow = type("Flow", (), {"path": "f/devgodzilla/demo", "name": "demo", "summary": "demo", "schema": None})
        return [flow]

    def get_flow(self, path: str) -> Any:
        return type("Flow", (), {"path": path, "name": path.split("/")[-1], "summary": None, "schema": None})

    def create_flow(self, path: str, definition: Dict[str, Any], **_kwargs: Any) -> Any:
        self.create_flow_calls.append(_CreateFlowCall(path=path, definition=definition))
        return {"path": path}

    def list_jobs(self, **_kwargs: Any) -> List[Dict[str, Any]]:
        return [{"id": "job-1", "status": "running"}]

    def list_flow_runs(self, _flow_path: str, **_kwargs: Any) -> List[Dict[str, Any]]:
        return [{"id": "job-2", "status": "success"}]

    def get_job(self, job_id: str) -> Any:
        job = type(
            "Job",
            (),
            {
                "id": job_id,
                "status": type("S", (), {"value": "completed"})(),
                "created_at": None,
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
            },
        )
        return job

    def get_job_logs(self, job_id: str) -> str:
        return f"logs for {job_id}"


class _ErrorWindmillClient(FakeWindmillClient):
    def __init__(self, fail_method: str) -> None:
        super().__init__()
        self._fail_method = fail_method

    def _maybe_fail(self, name: str) -> None:
        if self._fail_method == name:
            raise RuntimeError(f"{name} failed")

    def get_flow(self, path: str) -> Any:
        self._maybe_fail("get_flow")
        return super().get_flow(path)

    def list_flow_runs(self, _flow_path: str, **_kwargs: Any) -> List[Dict[str, Any]]:
        self._maybe_fail("list_flow_runs")
        return super().list_flow_runs(_flow_path, **_kwargs)

    def list_jobs(self, **_kwargs: Any) -> List[Dict[str, Any]]:
        self._maybe_fail("list_jobs")
        return super().list_jobs(**_kwargs)

    def get_job(self, job_id: str) -> Any:
        self._maybe_fail("get_job")
        return super().get_job(job_id)

    def get_job_logs(self, job_id: str) -> str:
        self._maybe_fail("get_job_logs")
        return super().get_job_logs(job_id)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_windmill_and_runs_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"
        repo = tmp / "repo"
        repo.mkdir(parents=True, exist_ok=True)

        db = SQLiteDatabase(db_path)
        db.init_schema()

        project = db.create_project(
            name="demo",
            git_url=str(repo),
            base_branch="main",
            local_path=str(repo),
        )
        protocol_root = repo / ".protocols" / "demo-proto"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "step-01-setup.md").write_text("# step\n", encoding="utf-8")

        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="demo-proto",
            status="pending",
            base_branch="main",
            worktree_path=str(repo),
            protocol_root=str(protocol_root),
        )
        step = db.create_step_run(
            protocol_run_id=run.id,
            step_index=0,
            step_name="step-01-setup",
            step_type="execute",
            status="pending",
        )

        # Create a job run and a real artifact file
        artifact_path = tmp / "manifest.json"
        artifact_path.write_text('{"hello":"world"}\n', encoding="utf-8")
        db.create_job_run(
            run_id="run-1",
            job_type="execute_step",
            status="queued",
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=step.id,
            log_path=str(artifact_path),
            params={"step_run_id": step.id},
        )
        db.create_run_artifact(run_id="run-1", name="manifest.json", kind="json", path=str(artifact_path))

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        fake_windmill = FakeWindmillClient()
        app.dependency_overrides[get_windmill_client] = lambda: fake_windmill  # type: ignore[index]

        with TestClient(app) as client:  # type: ignore[arg-type]
            # Runs API
            runs = client.get("/runs").json()
            assert any(r["run_id"] == "run-1" for r in runs)

            artifacts = client.get("/runs/run-1/artifacts").json()
            assert any(a["name"] == "manifest.json" for a in artifacts)

            content = client.get("/runs/run-1/artifacts/manifest.json/content").json()
            assert "hello" in content["content"]

            # Windmill API passthrough (dependency-overridden)
            flows = client.get("/flows").json()
            assert flows and flows[0]["path"].startswith("f/")

            flow_runs = client.get("/flows/f/devgodzilla/demo/runs").json()
            assert flow_runs and flow_runs[0]["id"] == "job-2"

            jobs = client.get("/jobs").json()
            assert jobs and jobs[0]["id"] == "job-1"

            logs = client.get("/jobs/job-1/logs").json()
            assert "logs for job-1" in logs["logs"]

            # Protocol -> create Windmill flow from steps
            resp = client.post(f"/protocols/{run.id}/flow", json={})
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["windmill_flow_id"] == f"f/devgodzilla/protocol-{run.id}"
            assert payload["flow_definition"]["modules"]
            assert db.get_protocol_run(run.id).windmill_flow_id == payload["windmill_flow_id"]

        app.dependency_overrides.clear()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
@pytest.mark.parametrize(
    ("fail_method", "path"),
    [
        ("get_flow", "/flows/f/devgodzilla/demo"),
        ("list_flow_runs", "/flows/f/devgodzilla/demo/runs"),
        ("list_jobs", "/jobs"),
        ("get_job", "/jobs/job-1"),
        ("get_job_logs", "/jobs/job-1/logs"),
    ],
)
def test_windmill_passthrough_error_paths(
    monkeypatch: pytest.MonkeyPatch,
    fail_method: str,
    path: str,
) -> None:
    from devgodzilla.db.database import SQLiteDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "devgodzilla.sqlite"

        db = SQLiteDatabase(db_path)
        db.init_schema()

        monkeypatch.setenv("DEVGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)

        app.dependency_overrides[get_windmill_client] = lambda: _ErrorWindmillClient(fail_method)  # type: ignore[index]
        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                response = client.get(path)
            assert response.status_code == 502
            assert "Windmill error:" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
