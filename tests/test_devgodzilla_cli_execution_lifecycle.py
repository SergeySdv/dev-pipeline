import pytest

from devgodzilla.services.cli_execution_tracker import (
    CLIExecutionTracker,
    CLIExecution,
    ExecutionStatus,
)


@pytest.fixture(autouse=True)
def fresh_tracker():
    CLIExecutionTracker._instance = None
    yield
    CLIExecutionTracker._instance = None


@pytest.fixture
def tracker():
    return CLIExecutionTracker()


class TestExecutionStatusValues:

    ALL_VALUES = [
        ExecutionStatus.PENDING,
        ExecutionStatus.RUNNING,
        ExecutionStatus.SUCCEEDED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    ]

    def test_all_5_values_exist(self):
        assert len(self.ALL_VALUES) == 5

    def test_all_values_are_unique(self):
        assert len(set(self.ALL_VALUES)) == 5

    def test_values_serialize_correctly(self):
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.SUCCEEDED.value == "succeeded"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.CANCELLED.value == "cancelled"

    def test_enum_from_string(self):
        assert ExecutionStatus("pending") == ExecutionStatus.PENDING
        assert ExecutionStatus("running") == ExecutionStatus.RUNNING
        assert ExecutionStatus("succeeded") == ExecutionStatus.SUCCEEDED
        assert ExecutionStatus("failed") == ExecutionStatus.FAILED
        assert ExecutionStatus("cancelled") == ExecutionStatus.CANCELLED


class TestExecutionStatusLifecycle:

    def test_start_sets_running(self, tracker):
        execution = tracker.start_execution(
            execution_type="discovery",
            engine_id="opencode",
            project_id=1,
        )
        assert execution.status == ExecutionStatus.RUNNING
        assert execution.started_at is not None

    def test_complete_success_sets_succeeded(self, tracker):
        execution = tracker.start_execution(
            execution_type="discovery",
            engine_id="opencode",
        )
        tracker.complete(execution.execution_id, success=True, exit_code=0)

        updated = tracker.get_execution(execution.execution_id)
        assert updated.status == ExecutionStatus.SUCCEEDED
        assert updated.exit_code == 0
        assert updated.finished_at is not None

    def test_complete_failure_sets_failed(self, tracker):
        execution = tracker.start_execution(
            execution_type="code_gen",
            engine_id="opencode",
        )
        tracker.complete(execution.execution_id, success=False, error="timeout")

        updated = tracker.get_execution(execution.execution_id)
        assert updated.status == ExecutionStatus.FAILED
        assert updated.error == "timeout"

    def test_cancel_sets_cancelled(self, tracker):
        execution = tracker.start_execution(
            execution_type="discovery",
            engine_id="opencode",
        )
        tracker.cancel(execution.execution_id)

        updated = tracker.get_execution(execution.execution_id)
        assert updated.status == ExecutionStatus.CANCELLED
        assert updated.finished_at is not None

    def test_cancel_then_complete_success_preserves_cancelled(self, tracker):
        execution = tracker.start_execution(
            execution_type="discovery",
            engine_id="opencode",
        )
        tracker.cancel(execution.execution_id)
        tracker.complete(execution.execution_id, success=True, exit_code=0)

        updated = tracker.get_execution(execution.execution_id)
        assert updated.status == ExecutionStatus.CANCELLED
        assert updated.exit_code == 0

    def test_cancel_then_complete_failure_preserves_cancelled_with_error(self, tracker):
        execution = tracker.start_execution(
            execution_type="discovery",
            engine_id="opencode",
        )
        tracker.cancel(execution.execution_id)
        tracker.complete(
            execution.execution_id, success=False, exit_code=1, error="process died"
        )

        updated = tracker.get_execution(execution.execution_id)
        assert updated.status == ExecutionStatus.CANCELLED
        assert updated.error == "process died"
        assert updated.exit_code == 1


class TestExecutionTrackerFiltering:

    def test_list_by_type(self, tracker):
        tracker.start_execution(execution_type="discovery", engine_id="opencode")
        tracker.start_execution(execution_type="code_gen", engine_id="opencode")
        tracker.start_execution(execution_type="discovery", engine_id="opencode")

        results = tracker.list_executions(execution_type="discovery")
        assert len(results) == 2

    def test_list_by_project_id(self, tracker):
        tracker.start_execution(execution_type="discovery", engine_id="opencode", project_id=1)
        tracker.start_execution(execution_type="discovery", engine_id="opencode", project_id=2)
        tracker.start_execution(execution_type="discovery", engine_id="opencode", project_id=1)

        results = tracker.list_executions(project_id=1)
        assert len(results) == 2

    def test_list_by_status(self, tracker):
        e1 = tracker.start_execution(execution_type="discovery", engine_id="opencode")
        e2 = tracker.start_execution(execution_type="discovery", engine_id="opencode")
        tracker.complete(e1.execution_id, success=True)

        running = tracker.list_executions(status=ExecutionStatus.RUNNING)
        assert len(running) == 1
        assert running[0].execution_id == e2.execution_id

    def test_list_active_returns_only_running(self, tracker):
        e1 = tracker.start_execution(execution_type="discovery", engine_id="opencode")
        e2 = tracker.start_execution(execution_type="code_gen", engine_id="opencode")
        tracker.complete(e1.execution_id, success=True)
        tracker.cancel(e2.execution_id)
        e3 = tracker.start_execution(execution_type="qa", engine_id="opencode")

        active = tracker.list_active()
        assert len(active) == 1
        assert active[0].execution_id == e3.execution_id

    def test_to_dict_includes_status(self, tracker):
        execution = tracker.start_execution(
            execution_type="discovery",
            engine_id="opencode",
            project_id=42,
        )
        d = execution.to_dict()
        assert d["status"] == "running"
        assert d["execution_type"] == "discovery"
        assert d["project_id"] == 42

    def test_to_dict_with_logs(self, tracker):
        execution = tracker.start_execution(
            execution_type="discovery",
            engine_id="opencode",
        )
        tracker.log(execution.execution_id, "info", "test message", source="test")

        d = execution.to_dict(include_logs=True)
        assert d["log_count"] >= 2
        assert len(d["logs"]) >= 2
