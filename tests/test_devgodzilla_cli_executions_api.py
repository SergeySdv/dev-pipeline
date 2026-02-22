"""
Tests for CLI Executions API routes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient
except Exception:
    TestClient = None

from devgodzilla.api.app import app
from devgodzilla.db.database import SQLiteDatabase
from devgodzilla.services.cli_execution_tracker import (
    get_execution_tracker,
    ExecutionStatus,
)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
class TestCLIExecutionsAPI:
    """Tests for /cli-executions endpoints."""

    @pytest.fixture(autouse=True)
    def reset_tracker(self):
        """Reset tracker singleton between tests."""
        tracker = get_execution_tracker()
        # Clear existing executions
        with tracker._execution_lock:
            tracker._executions.clear()
            tracker._subscribers.clear()
        yield
        # Cleanup after test
        with tracker._execution_lock:
            tracker._executions.clear()
            tracker._subscribers.clear()

    @pytest.fixture
    def db(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(db_path)
        db.init_schema()
        return db

    @pytest.fixture
    def client(self, db: SQLiteDatabase):
        from devgodzilla.api.dependencies import get_db

        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def sample_execution(self):
        tracker = get_execution_tracker()
        return tracker.start_execution(
            execution_type="discovery",
            engine_id="opencode",
            project_id=1,
            command="discovery --full",
            working_dir="/tmp/test",
            metadata={"test": True},
        )

    @pytest.fixture
    def completed_execution(self):
        tracker = get_execution_tracker()
        execution = tracker.start_execution(
            execution_type="code_gen",
            engine_id="dummy",
            project_id=None,
        )
        tracker.complete(execution.execution_id, success=True, exit_code=0)
        return execution

    def test_list_cli_executions_empty(self, client):
        """Test listing executions when none exist."""
        resp = client.get("/cli-executions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["executions"] == []
        assert data["total"] == 0
        assert data["active_count"] == 0

    def test_list_cli_executions_with_data(self, client, sample_execution):
        """Test listing executions returns existing items."""
        resp = client.get("/cli-executions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["active_count"] == 1
        assert len(data["executions"]) == 1

        exec_data = data["executions"][0]
        assert exec_data["execution_id"] == sample_execution.execution_id
        assert exec_data["execution_type"] == "discovery"
        assert exec_data["engine_id"] == "opencode"
        assert exec_data["status"] == "running"

    def test_list_cli_executions_filter_by_type(self, client, sample_execution):
        """Test filtering by execution_type."""
        resp = client.get("/cli-executions?execution_type=discovery")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = client.get("/cli-executions?execution_type=code_gen")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_cli_executions_filter_by_status(self, client, sample_execution, completed_execution):
        """Test filtering by status."""
        resp = client.get("/cli-executions?status=running")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["executions"][0]["execution_id"] == sample_execution.execution_id

        resp = client.get("/cli-executions?status=succeeded")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_cli_executions_invalid_status(self, client):
        """Test invalid status parameter."""
        resp = client.get("/cli-executions?status=invalid_status")
        assert resp.status_code == 400
        assert "Invalid status" in resp.json()["detail"]

    def test_list_cli_executions_limit(self, client):
        """Test limit parameter."""
        tracker = get_execution_tracker()
        for i in range(5):
            tracker.start_execution(
                execution_type="test",
                engine_id="dummy",
            )

        resp = client.get("/cli-executions?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()["executions"]) == 2

    def test_list_active_executions(self, client, sample_execution, completed_execution):
        """Test listing only active executions."""
        resp = client.get("/cli-executions/active")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["active_count"] == 1
        assert data["executions"][0]["execution_id"] == sample_execution.execution_id

    def test_get_cli_execution(self, client, sample_execution):
        """Test getting a specific execution."""
        resp = client.get(f"/cli-executions/{sample_execution.execution_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["execution_id"] == sample_execution.execution_id
        assert data["execution_type"] == "discovery"
        assert "logs" in data  # include_logs defaults to True

    def test_get_cli_execution_without_logs(self, client, sample_execution):
        """Test getting execution without logs."""
        resp = client.get(f"/cli-executions/{sample_execution.execution_id}?include_logs=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data["logs"] is None
        assert data["log_count"] >= 1  # Should have startup log

    def test_get_cli_execution_not_found(self, client):
        """Test getting non-existent execution."""
        resp = client.get("/cli-executions/nonexistent-id")
        assert resp.status_code == 404

    def test_get_execution_logs(self, client, sample_execution):
        """Test getting logs for an execution."""
        tracker = get_execution_tracker()
        tracker.log(sample_execution.execution_id, "info", "Test log message")
        tracker.log(sample_execution.execution_id, "error", "Error message")

        resp = client.get(f"/cli-executions/{sample_execution.execution_id}/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["execution_id"] == sample_execution.execution_id
        assert data["status"] == "running"
        assert data["log_count"] >= 3  # Startup + 2 we added

    def test_get_execution_logs_filter_level(self, client, sample_execution):
        """Test filtering logs by level."""
        tracker = get_execution_tracker()
        tracker.log(sample_execution.execution_id, "info", "Info message")
        tracker.log(sample_execution.execution_id, "error", "Error message")
        tracker.log(sample_execution.execution_id, "debug", "Debug message")

        resp = client.get(f"/cli-executions/{sample_execution.execution_id}/logs?level=error")
        assert resp.status_code == 200
        logs = resp.json()["logs"]
        assert all(log_entry["level"] == "error" for log_entry in logs)

    def test_get_execution_logs_not_found(self, client):
        """Test getting logs for non-existent execution."""
        resp = client.get("/cli-executions/nonexistent-id/logs")
        assert resp.status_code == 404

    def test_cancel_execution(self, client, sample_execution):
        """Test cancelling a running execution."""
        resp = client.post(f"/cli-executions/{sample_execution.execution_id}/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"

        # Verify it's actually cancelled
        tracker = get_execution_tracker()
        exec_obj = tracker.get_execution(sample_execution.execution_id)
        assert exec_obj.status == ExecutionStatus.CANCELLED

    def test_cancel_execution_terminates_process_when_pid_present(
        self, client, sample_execution, monkeypatch: pytest.MonkeyPatch
    ):
        """Test cancel endpoint attempts to terminate the tracked process."""
        tracker = get_execution_tracker()
        tracker.set_pid(sample_execution.execution_id, 43210)

        kill_calls: list[tuple[int, int]] = []

        def _fake_kill(pid: int, sig: int) -> None:
            kill_calls.append((pid, sig))

        monkeypatch.setattr("devgodzilla.api.routes.cli_executions.os.kill", _fake_kill)

        resp = client.post(f"/cli-executions/{sample_execution.execution_id}/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["pid"] == 43210
        assert data["termination_attempted"] is True
        assert data["termination_result"] == "signal_sent"
        assert kill_calls == [(43210, 15)]

    def test_tracker_complete_preserves_cancelled_status(self):
        """Late completion callbacks should not overwrite cancelled status."""
        tracker = get_execution_tracker()
        execution = tracker.start_execution(execution_type="discovery", engine_id="opencode")
        tracker.cancel(execution.execution_id)

        tracker.complete(execution.execution_id, success=False, exit_code=-15, error="terminated")

        exec_obj = tracker.get_execution(execution.execution_id)
        assert exec_obj is not None
        assert exec_obj.status == ExecutionStatus.CANCELLED
        assert exec_obj.exit_code == -15

    def test_cancel_execution_not_found(self, client):
        """Test cancelling non-existent execution."""
        resp = client.post("/cli-executions/nonexistent-id/cancel")
        assert resp.status_code == 404

    def test_cancel_execution_not_running(self, client, completed_execution):
        """Test cancelling already completed execution."""
        resp = client.post(f"/cli-executions/{completed_execution.execution_id}/cancel")
        assert resp.status_code == 400
        assert "Cannot cancel" in resp.json()["detail"]

    def test_execution_duration_tracking(self, client):
        """Test that duration is tracked correctly."""
        tracker = get_execution_tracker()
        execution = tracker.start_execution(
            execution_type="test",
            engine_id="dummy",
        )
        tracker.complete(execution.execution_id, success=True)

        resp = client.get(f"/cli-executions/{execution.execution_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["duration_seconds"] is not None
        assert data["duration_seconds"] >= 0

    def test_execution_metadata_preserved(self, client):
        """Test that custom metadata is preserved."""
        tracker = get_execution_tracker()
        execution = tracker.start_execution(
            execution_type="custom",
            engine_id="test-engine",
            metadata={
                "custom_key": "custom_value",
                "nested": {"key": "value"},
            },
        )

        resp = client.get(f"/cli-executions/{execution.execution_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["custom_key"] == "custom_value"
        assert data["metadata"]["nested"]["key"] == "value"
