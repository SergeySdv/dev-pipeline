from __future__ import annotations

from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient
except Exception:
    TestClient = None

from devgodzilla.api.app import app
from devgodzilla.db.database import SQLiteDatabase


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_protocol_adjacent_endpoints_include_spec_review_context(tmp_path: Path) -> None:
    db = SQLiteDatabase(tmp_path / "test.db")
    db.init_schema()

    project = db.create_project(
        name="Review Context Project",
        git_url="https://github.com/example/review-context.git",
        base_branch="main",
        local_path=str(tmp_path / "repo"),
    )
    protocol = db.create_protocol_run(
        project_id=project.id,
        protocol_name="review-context-protocol",
        status="running",
        base_branch="main",
    )
    step = db.create_step_run(
        protocol_run_id=protocol.id,
        step_index=0,
        step_name="execute",
        step_type="execute",
        status="running",
    )
    spec_run = db.create_spec_run(
        project_id=project.id,
        spec_name="review-context",
        spec_path="specs/0001-review-context/spec.md",
        status="implemented",
        base_branch="main",
    )
    db.update_spec_run(spec_run.id, protocol_run_id=protocol.id)
    db.update_protocol_windmill(
        protocol.id,
        speckit_metadata={
            "spec_run_id": spec_run.id,
            "spec_hash": "abc123",
            "validation_status": "validated",
            "validated_at": "2026-03-09T10:00:00Z",
            "spec": {"name": "Review Context"},
        },
    )
    db.append_event(
        protocol_run_id=protocol.id,
        project_id=project.id,
        step_run_id=step.id,
        event_type="protocol_started",
        message="Protocol started",
    )
    db.create_job_run(
        run_id="run-review-context",
        job_type="execute_step",
        status="running",
        project_id=project.id,
        protocol_run_id=protocol.id,
        step_run_id=step.id,
        params={"step_run_id": step.id},
    )
    db.create_qa_result(
        project_id=project.id,
        protocol_run_id=protocol.id,
        step_run_id=step.id,
        verdict="error",
        findings=[
            {
                "severity": "critical",
                "message": "Missing review handoff",
                "metadata": {
                    "article": "7",
                    "article_title": "Traceability",
                },
            }
        ],
        gate_results=[],
    )

    from devgodzilla.api.dependencies import get_db

    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            protocol_spec = client.get(f"/protocols/{protocol.id}/spec")
            recent_events = client.get("/events/recent")
            protocol_events = client.get(f"/protocols/{protocol.id}/events")
            run_detail = client.get("/runs/run-review-context")
            run_list = client.get("/runs")
            protocol_runs = client.get(f"/protocols/{protocol.id}/runs")
            quality = client.get("/quality/dashboard")

        assert protocol_spec.status_code == 200
        assert protocol_spec.json()["spec_run_id"] == spec_run.id

        assert recent_events.status_code == 200
        assert recent_events.json()["events"][0]["spec_run_id"] == spec_run.id

        assert protocol_events.status_code == 200
        assert protocol_events.json()[0]["spec_run_id"] == spec_run.id

        assert run_detail.status_code == 200
        assert run_detail.json()["spec_run_id"] == spec_run.id

        assert run_list.status_code == 200
        assert run_list.json()[0]["spec_run_id"] == spec_run.id

        assert protocol_runs.status_code == 200
        assert protocol_runs.json()[0]["spec_run_id"] == spec_run.id

        assert quality.status_code == 200
        assert quality.json()["recent_findings"][0]["spec_run_id"] == spec_run.id
    finally:
        app.dependency_overrides.clear()
