"""
Integration tests for agent management API endpoints.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    TestClient = None  # type: ignore

from devgodzilla.api.app import app
from devgodzilla.db.database import SQLiteDatabase


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_agents_api_defaults_prompts_overrides(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(
            """
agents:
  alpha:
    name: Alpha Agent
    kind: api
    endpoint: https://example.com/api
    capabilities: [code_gen]
    enabled: true
  beta:
    name: Beta Agent
    kind: api
    endpoint: https://example.com/qa
    capabilities: [qa]
    enabled: false
defaults:
  exec: alpha
  qa: beta
  prompts:
    exec: exec-template
    qa: qa-template
prompts:
  exec-template:
    name: Exec Template
    path: prompts/exec.prompt.md
    kind: exec
  qa-template:
    name: QA Template
    path: prompts/qa.prompt.md
    kind: qa
projects:
  "1":
    inherit: true
    agents:
      alpha:
        enabled: false
    defaults:
      exec: beta
    prompts:
      exec-template:
        name: Project Exec Template
        path: prompts/exec.project.prompt.md
""".strip()
        )
        monkeypatch.setenv("DEVGODZILLA_AGENT_CONFIG_PATH", str(config_path))

        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(db_path)
        db.init_schema()
        project = db.create_project(
            name="Agent Test",
            git_url="https://example.com/repo.git",
            base_branch="main",
        )
        run = db.create_protocol_run(
            project_id=project.id,
            protocol_name="agents-protocol",
            status="running",
            base_branch="main",
        )
        db.create_step_run(
            protocol_run_id=run.id,
            step_index=0,
            step_name="step-00",
            step_type="execute",
            status="running",
            assigned_agent="alpha",
        )
        db.create_step_run(
            protocol_run_id=run.id,
            step_index=1,
            step_name="step-01",
            step_type="execute",
            status="completed",
            assigned_agent="alpha",
        )

        from devgodzilla.api.dependencies import get_db

        app.dependency_overrides[get_db] = lambda: db

        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                resp = client.get("/agents")
                assert resp.status_code == 200
                agents = {a["id"]: a for a in resp.json()}
                assert agents["alpha"]["enabled"] is True
                assert agents["beta"]["enabled"] is False

                resp = client.get(f"/agents?project_id={project.id}")
                assert resp.status_code == 200
                project_agents = {a["id"]: a for a in resp.json()}
                assert project_agents["alpha"]["enabled"] is False
                assert project_agents["beta"]["enabled"] is False

                resp = client.get("/agents/defaults")
                assert resp.status_code == 200
                defaults = resp.json()
                assert defaults["exec"] == "alpha"
                assert defaults["qa"] == "beta"

                resp = client.get(f"/agents/defaults?project_id={project.id}")
                assert resp.status_code == 200
                project_defaults = resp.json()
                assert project_defaults["exec"] == "beta"

                resp = client.put(
                    f"/agents/defaults?project_id={project.id}",
                    json={"exec": "alpha"},
                )
                assert resp.status_code == 200
                assert resp.json()["exec"] == "alpha"

                resp = client.get(f"/agents/prompts?project_id={project.id}")
                assert resp.status_code == 200
                prompts = {p["id"]: p for p in resp.json()}
                assert prompts["exec-template"]["source"] == "project"
                assert prompts["qa-template"]["source"] == "global"

                resp = client.get(f"/agents/projects/{project.id}")
                assert resp.status_code == 200
                overrides = resp.json()
                assert overrides["inherit"] is True

                resp = client.put(
                    f"/agents/projects/{project.id}",
                    json={"inherit": False},
                )
                assert resp.status_code == 200
                assert resp.json()["inherit"] is False

                resp = client.get(f"/agents/metrics?project_id={project.id}")
                assert resp.status_code == 200
                metrics = {m["agent_id"]: m for m in resp.json()}
                assert metrics["alpha"]["active_steps"] == 1
                assert metrics["alpha"]["completed_steps"] == 1
                assert metrics["alpha"]["total_steps"] == 2
        finally:
            app.dependency_overrides.clear()
