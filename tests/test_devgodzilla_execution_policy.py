"""
Tests for policy gating in ExecutionService.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from devgodzilla.engines.interface import EngineMetadata, EngineResult, EngineKind, SandboxMode
from devgodzilla.models.domain import ProtocolStatus, StepStatus
from devgodzilla.qa.gates.interface import GateResult, GateVerdict
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.execution import ExecutionService, StepResolution
from devgodzilla.services.policy import EffectivePolicy, Finding
from devgodzilla.services.quality import QAVerdict, QualityService


@pytest.fixture
def service_context():
    config = Mock()
    config.engine_defaults = {}
    return ServiceContext(config=config)


def _build_execution_db():
    db = Mock()

    step = Mock()
    step.id = 10
    step.protocol_run_id = 20
    step.step_name = "step-1"
    step.engine_id = None
    step.model = None
    step.assigned_agent = None

    run = Mock()
    run.id = 20
    run.project_id = 30
    run.protocol_name = "demo"
    run.worktree_path = None
    run.protocol_root = None

    project = Mock()
    project.id = 30
    project.local_path = "/tmp/repo"
    project.policy_enforcement_mode = "block"

    db.get_step_run.return_value = step
    db.get_protocol_run.return_value = run
    db.get_project.return_value = project

    return db, step, run, project


def test_execute_step_blocks_on_clarifications(service_context, monkeypatch):
    db, step, run, _project = _build_execution_db()

    monkeypatch.setattr(
        "devgodzilla.services.execution.ClarifierService.has_blocking_open",
        lambda *args, **kwargs: True,
    )

    service = ExecutionService(context=service_context, db=db)
    result = service.execute_step(step.id)

    assert result.success is False
    assert result.error == "Blocked on clarifications"
    db.update_step_status.assert_called_with(
        step.id,
        StepStatus.BLOCKED,
        summary="Blocked on clarifications",
    )
    db.update_protocol_status.assert_called_with(run.id, ProtocolStatus.BLOCKED)


def test_execute_step_blocks_on_policy_findings(service_context, monkeypatch, tmp_path):
    db, step, run, project = _build_execution_db()
    project.local_path = str(tmp_path)

    monkeypatch.setattr(
        "devgodzilla.services.execution.ClarifierService.has_blocking_open",
        lambda *args, **kwargs: False,
    )

    effective = EffectivePolicy(
        policy={},
        effective_hash="hash",
        pack_key="default",
        pack_version="1.0",
    )
    monkeypatch.setattr(
        "devgodzilla.services.execution.PolicyService.resolve_effective_policy",
        lambda *args, **kwargs: effective,
    )
    finding = Finding(
        code="policy.step.file_missing",
        severity="warning",
        message="Missing step file",
        scope="step",
    )
    monkeypatch.setattr(
        "devgodzilla.services.execution.PolicyService.evaluate_step",
        lambda *args, **kwargs: [finding],
    )
    monkeypatch.setattr(
        "devgodzilla.services.execution.resolve_workspace_root",
        lambda _run, _project: Path("/tmp/repo"),
    )

    service = ExecutionService(context=service_context, db=db)
    result = service.execute_step(step.id)

    assert result.success is False
    assert result.error == "Blocked by policy findings"
    db.update_step_status.assert_called_with(
        step.id,
        StepStatus.BLOCKED,
        summary="Blocked by policy findings",
    )
    db.update_protocol_status.assert_called_with(run.id, ProtocolStatus.BLOCKED)

    assert db.append_event.called
    event_calls = [call.kwargs for call in db.append_event.call_args_list]
    assert any(call.get("event_type") == "policy_finding" for call in event_calls)


def test_handle_result_auto_enqueues_next_step_after_passing_qa(service_context, monkeypatch):
    db, step, run, _project = _build_execution_db()
    step.status = StepStatus.NEEDS_QA
    run.status = ProtocolStatus.RUNNING

    def update_step_status(_step_id, status, **_kwargs):
        step.status = status

    def update_protocol_status(_run_id, status, **_kwargs):
        run.status = status

    db.update_step_status.side_effect = update_step_status
    db.update_protocol_status.side_effect = update_protocol_status
    db.get_step_run.side_effect = lambda _step_id: step
    db.get_protocol_run.side_effect = lambda _run_id: run

    qa_result = Mock(verdict=QAVerdict.PASS)
    qa_service = Mock()
    qa_service.run_qa.return_value = qa_result
    qa_service.generate_quality_report.return_value = None

    def persist_verdict(_qa_result, _step_id, report_path=None):
        step.status = StepStatus.COMPLETED

    qa_service.persist_verdict.side_effect = persist_verdict

    orchestrator = Mock()
    orchestrator.check_and_complete_protocol.return_value = False
    monkeypatch.setattr("devgodzilla.services.execution._build_orchestrator", lambda context, db_obj: orchestrator)

    service = ExecutionService(context=service_context, db=db, quality_service=qa_service)
    monkeypatch.setattr(service, "_write_execution_artifacts", lambda **kwargs: {})

    engine = Mock()
    engine.metadata = EngineMetadata(id="opencode", display_name="OpenCode", kind=EngineKind.CLI)
    engine_result = EngineResult(success=True, stdout="ok", metadata={})
    resolution = StepResolution(
        engine_id="opencode",
        model="demo-model",
        prompt_text="prompt",
        prompt_path=None,
        prompt_version=None,
        workdir=Path("/tmp/repo"),
        protocol_root=Path("/tmp/repo/.protocols/demo"),
        workspace_root=Path("/tmp/repo"),
        sandbox=SandboxMode.WORKSPACE_WRITE,
    )

    result = service._handle_result(step, run, engine, engine_result, resolution)

    assert result.success is True
    orchestrator.check_and_complete_protocol.assert_called_once_with(step.protocol_run_id)
    orchestrator.enqueue_next_step.assert_called_once_with(step.protocol_run_id)


def test_handle_result_does_not_auto_enqueue_after_failing_qa(service_context, monkeypatch):
    db, step, run, _project = _build_execution_db()
    step.status = StepStatus.NEEDS_QA
    run.status = ProtocolStatus.RUNNING

    def update_step_status(_step_id, status, **_kwargs):
        step.status = status

    def update_protocol_status(_run_id, status, **_kwargs):
        run.status = status

    db.update_step_status.side_effect = update_step_status
    db.update_protocol_status.side_effect = update_protocol_status
    db.get_step_run.side_effect = lambda _step_id: step
    db.get_protocol_run.side_effect = lambda _run_id: run

    qa_result = Mock(verdict=QAVerdict.FAIL)
    qa_service = Mock()
    qa_service.run_qa.return_value = qa_result
    qa_service.generate_quality_report.return_value = None

    def persist_verdict(_qa_result, _step_id, report_path=None):
        step.status = StepStatus.FAILED
        run.status = ProtocolStatus.BLOCKED

    qa_service.persist_verdict.side_effect = persist_verdict

    orchestrator = Mock()
    orchestrator.check_and_complete_protocol.return_value = False
    monkeypatch.setattr("devgodzilla.services.execution._build_orchestrator", lambda context, db_obj: orchestrator)

    service = ExecutionService(context=service_context, db=db, quality_service=qa_service)
    monkeypatch.setattr(service, "_write_execution_artifacts", lambda **kwargs: {})

    engine = Mock()
    engine.metadata = EngineMetadata(id="opencode", display_name="OpenCode", kind=EngineKind.CLI)
    engine_result = EngineResult(success=True, stdout="ok", metadata={})
    resolution = StepResolution(
        engine_id="opencode",
        model="demo-model",
        prompt_text="prompt",
        prompt_path=None,
        prompt_version=None,
        workdir=Path("/tmp/repo"),
        protocol_root=Path("/tmp/repo/.protocols/demo"),
        workspace_root=Path("/tmp/repo"),
        sandbox=SandboxMode.WORKSPACE_WRITE,
    )

    result = service._handle_result(step, run, engine, engine_result, resolution)

    assert result.success is True
    orchestrator.check_and_complete_protocol.assert_called_once_with(step.protocol_run_id)
    orchestrator.enqueue_next_step.assert_not_called()


def test_resolve_step_maps_dev_alias_to_default_exec_engine(service_context, monkeypatch):
    db, step, run, project = _build_execution_db()
    step.assigned_agent = "dev"
    project.policy_enforcement_mode = "warn"
    service_context.config.engine_defaults = {"exec": "opencode"}

    workspace_root = Path("/tmp/repo")
    protocol_root = workspace_root / ".protocols" / "demo"

    monkeypatch.setattr("devgodzilla.services.execution.resolve_workspace_root", lambda _run, _project: workspace_root)
    monkeypatch.setattr("devgodzilla.services.execution.resolve_protocol_root", lambda _run, _workspace: protocol_root)
    monkeypatch.setattr("devgodzilla.services.execution.get_step_spec_from_template", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ExecutionService, "_build_prompt", lambda *args, **kwargs: "prompt")

    service = ExecutionService(context=service_context, db=db)
    resolution = service._resolve_step(step, run, project, engine_id=None, model=None)

    assert resolution.engine_id == "opencode"


def test_verify_steps_require_real_test_gate(service_context):
    db, step, _run, _project = _build_execution_db()
    step.step_type = "verify"
    step.step_name = "step-03-phase-3-testing"

    service = QualityService(context=service_context, db=db)

    enforced = service._enforce_required_verify_gates(
        step,
        [GateResult(gate_id="prompt_qa", gate_name="Prompt QA", verdict=GateVerdict.SKIP)],
    )

    test_gate = next(result for result in enforced if result.gate_id == "test")
    assert test_gate.verdict == GateVerdict.FAIL
    assert any("requires automated tests" in finding.message for finding in test_gate.findings)
