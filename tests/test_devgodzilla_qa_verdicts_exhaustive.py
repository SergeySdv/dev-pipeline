import pytest
from unittest.mock import Mock

from devgodzilla.services.quality import QualityService, QAResult, QAVerdict
from devgodzilla.qa.gates.interface import (
    Gate,
    GateContext,
    GateResult,
    GateVerdict,
    Finding,
)
from devgodzilla.services.base import ServiceContext
from devgodzilla.models.domain import ProtocolStatus, StepStatus


class _StubGate(Gate):
    def __init__(self, gate_id: str, verdict: GateVerdict, findings=None):
        self._gate_id = gate_id
        self._verdict = verdict
        self._findings = findings or []

    @property
    def gate_id(self):
        return self._gate_id

    @property
    def gate_name(self):
        return f"Stub {self._gate_id}"

    def run(self, context: GateContext) -> GateResult:
        return GateResult(
            gate_id=self._gate_id,
            gate_name=self.gate_name,
            verdict=self._verdict,
            findings=self._findings,
        )


@pytest.fixture
def service_context():
    config = Mock()
    config.engine_defaults = {}
    config.qa_max_auto_fix_attempts = 0
    return ServiceContext(config=config)


@pytest.fixture
def mock_db():
    db = Mock()
    mock_project = Mock()
    mock_project.id = 1
    mock_project.local_path = "/tmp/repo"
    mock_run = Mock()
    mock_run.id = 100
    mock_run.project_id = 1
    mock_run.worktree_path = None
    mock_run.protocol_root = None
    mock_step = Mock()
    mock_step.id = 1000
    mock_step.protocol_run_id = 100
    mock_step.step_name = "step-1"
    mock_step.status = "running"
    mock_step.runtime_state = None
    db.get_step_run.return_value = mock_step
    db.get_protocol_run.return_value = mock_run
    db.get_project.return_value = mock_project
    return db


class TestQAVerdictStepStatusMapping:

    def test_pass_sets_step_completed(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        result = QAResult(step_run_id=1000, verdict=QAVerdict.PASS)
        step = mock_db.get_step_run(1000)
        run = mock_db.get_protocol_run(step.protocol_run_id)
        service._update_step_status(step, run, result)

        mock_db.update_step_status.assert_called_once_with(
            step.id, StepStatus.COMPLETED, summary="QA passed"
        )

    def test_warn_sets_step_completed(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        result = QAResult(
            step_run_id=1000,
            verdict=QAVerdict.WARN,
            gate_results=[
                GateResult(
                    gate_id="test", gate_name="Test", verdict=GateVerdict.WARN,
                    findings=[Finding(gate_id="test", severity="warning", message="minor issue")],
                )
            ],
        )
        step = mock_db.get_step_run(1000)
        run = mock_db.get_protocol_run(step.protocol_run_id)
        service._update_step_status(step, run, result)

        args = mock_db.update_step_status.call_args
        assert args[0][1] == StepStatus.COMPLETED

    def test_fail_sets_step_failed_and_protocol_blocked(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        result = QAResult(
            step_run_id=1000,
            verdict=QAVerdict.FAIL,
            gate_results=[
                GateResult(
                    gate_id="test", gate_name="Test", verdict=GateVerdict.FAIL,
                    findings=[Finding(gate_id="test", severity="error", message="critical issue")],
                )
            ],
        )
        step = mock_db.get_step_run(1000)
        run = mock_db.get_protocol_run(step.protocol_run_id)
        service._update_step_status(step, run, result)

        step_call = mock_db.update_step_status.call_args
        assert step_call[0][1] == StepStatus.FAILED
        mock_db.update_protocol_status.assert_called_with(run.id, ProtocolStatus.BLOCKED)

    def test_skip_sets_step_completed(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        result = QAResult(step_run_id=1000, verdict=QAVerdict.SKIP)
        step = mock_db.get_step_run(1000)
        run = mock_db.get_protocol_run(step.protocol_run_id)
        service._update_step_status(step, run, result)

        mock_db.update_step_status.assert_called_once_with(
            step.id, StepStatus.COMPLETED, summary="QA skipped"
        )

    def test_error_sets_step_failed_and_protocol_blocked(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        result = QAResult(step_run_id=1000, verdict=QAVerdict.ERROR, error="gate crashed")
        step = mock_db.get_step_run(1000)
        run = mock_db.get_protocol_run(step.protocol_run_id)
        service._update_step_status(step, run, result)

        step_call = mock_db.update_step_status.call_args
        assert step_call[0][1] == StepStatus.FAILED
        mock_db.update_protocol_status.assert_called_with(run.id, ProtocolStatus.BLOCKED)


class TestQAVerdictAggregation:

    def test_error_gate_gives_overall_fail(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        gate_results = [
            GateResult(gate_id="a", gate_name="A", verdict=GateVerdict.PASS),
            GateResult(gate_id="b", gate_name="B", verdict=GateVerdict.ERROR, error="crash"),
        ]
        assert service._aggregate_verdict(gate_results) == QAVerdict.FAIL

    def test_all_skip_gives_pass(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        gate_results = [
            GateResult(gate_id="a", gate_name="A", verdict=GateVerdict.SKIP),
            GateResult(gate_id="b", gate_name="B", verdict=GateVerdict.SKIP),
        ]
        assert service._aggregate_verdict(gate_results) == QAVerdict.PASS

    def test_pass_and_skip_gives_pass(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        gate_results = [
            GateResult(gate_id="a", gate_name="A", verdict=GateVerdict.PASS),
            GateResult(gate_id="b", gate_name="B", verdict=GateVerdict.SKIP),
        ]
        assert service._aggregate_verdict(gate_results) == QAVerdict.PASS

    def test_warn_and_fail_gives_fail(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        gate_results = [
            GateResult(gate_id="a", gate_name="A", verdict=GateVerdict.WARN),
            GateResult(gate_id="b", gate_name="B", verdict=GateVerdict.FAIL),
        ]
        assert service._aggregate_verdict(gate_results) == QAVerdict.FAIL

    def test_empty_gates_gives_skip(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        assert service._aggregate_verdict([]) == QAVerdict.SKIP

    def test_only_warn_gives_warn(self, service_context, mock_db):
        service = QualityService(service_context, mock_db)
        gate_results = [
            GateResult(gate_id="a", gate_name="A", verdict=GateVerdict.WARN),
        ]
        assert service._aggregate_verdict(gate_results) == QAVerdict.WARN


class TestQAResultProperties:

    def test_passed_for_pass(self):
        result = QAResult(step_run_id=1, verdict=QAVerdict.PASS)
        assert result.passed is True

    def test_passed_for_warn(self):
        result = QAResult(step_run_id=1, verdict=QAVerdict.WARN)
        assert result.passed is True

    def test_passed_for_skip(self):
        result = QAResult(step_run_id=1, verdict=QAVerdict.SKIP)
        assert result.passed is True

    def test_not_passed_for_fail(self):
        result = QAResult(step_run_id=1, verdict=QAVerdict.FAIL)
        assert result.passed is False

    def test_not_passed_for_error(self):
        result = QAResult(step_run_id=1, verdict=QAVerdict.ERROR)
        assert result.passed is False


class TestGateVerdictValues:

    ALL_VERDICTS = [
        GateVerdict.PASS,
        GateVerdict.WARN,
        GateVerdict.FAIL,
        GateVerdict.SKIP,
        GateVerdict.ERROR,
    ]

    def test_all_5_values_exist(self):
        assert len(self.ALL_VERDICTS) == 5

    def test_all_values_are_unique(self):
        assert len(set(self.ALL_VERDICTS)) == 5

    def test_values_serialize_correctly(self):
        assert GateVerdict.PASS.value == "pass"
        assert GateVerdict.WARN.value == "warn"
        assert GateVerdict.FAIL.value == "fail"
        assert GateVerdict.SKIP.value == "skip"
        assert GateVerdict.ERROR.value == "error"

    def test_passed_property(self):
        pass_result = GateResult(gate_id="t", gate_name="T", verdict=GateVerdict.PASS)
        warn_result = GateResult(gate_id="t", gate_name="T", verdict=GateVerdict.WARN)
        skip_result = GateResult(gate_id="t", gate_name="T", verdict=GateVerdict.SKIP)
        fail_result = GateResult(gate_id="t", gate_name="T", verdict=GateVerdict.FAIL)
        error_result = GateResult(gate_id="t", gate_name="T", verdict=GateVerdict.ERROR)

        assert pass_result.passed is True
        assert warn_result.passed is True
        assert skip_result.passed is True
        assert fail_result.passed is False
        assert error_result.passed is False

    def test_blocking_property(self):
        pass_result = GateResult(gate_id="t", gate_name="T", verdict=GateVerdict.PASS)
        warn_result = GateResult(gate_id="t", gate_name="T", verdict=GateVerdict.WARN)
        skip_result = GateResult(gate_id="t", gate_name="T", verdict=GateVerdict.SKIP)
        fail_result = GateResult(gate_id="t", gate_name="T", verdict=GateVerdict.FAIL)
        error_result = GateResult(gate_id="t", gate_name="T", verdict=GateVerdict.ERROR)

        assert pass_result.blocking is False
        assert warn_result.blocking is False
        assert skip_result.blocking is False
        assert fail_result.blocking is True
        assert error_result.blocking is True
