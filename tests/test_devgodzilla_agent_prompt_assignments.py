"""
Tests for agent prompt assignments used by execution and QA flows.
"""

from types import SimpleNamespace
from unittest.mock import Mock

from devgodzilla.engines.dummy import DummyEngine
from devgodzilla.engines.registry import EngineRegistry
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.execution import ExecutionService
from devgodzilla.services.policy import EffectivePolicy
from devgodzilla.services.quality import QualityService


def test_execution_prompt_assignment_used(tmp_path):
    repo_root = tmp_path / "repo"
    protocol_root = repo_root / ".protocols" / "demo"
    prompt_path = repo_root / "prompts" / "exec.prompt.md"
    step_path = protocol_root / "step-01.md"

    step_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    step_path.write_text("Step content", encoding="utf-8")
    prompt_path.write_text("EXEC TEMPLATE", encoding="utf-8")

    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        """
defaults:
  prompts:
    exec: exec-template
prompts:
  exec-template:
    path: prompts/exec.prompt.md
""".strip(),
        encoding="utf-8",
    )

    config = SimpleNamespace(
        agent_config_path=config_path,
        engine_defaults={},
        qa_model=None,
    )
    context = ServiceContext(config=config)
    service = ExecutionService(context=context, db=Mock())

    step = Mock()
    step.step_name = "step-01"
    step.summary = None
    step.model = None
    step.assigned_agent = None

    run = Mock()
    run.protocol_name = "demo"
    run.worktree_path = None
    run.protocol_root = None
    run.template_config = None

    project = Mock()
    project.id = 1
    project.local_path = str(repo_root)

    resolution = service._resolve_step(step, run, project, engine_id=None, model=None)

    assert "EXEC TEMPLATE" in resolution.prompt_text


def test_qa_prompt_assignment_used(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    protocol_root = repo_root / ".protocols" / "demo"
    prompt_path = repo_root / "prompts" / "qa.prompt.md"
    protocol_root.mkdir(parents=True, exist_ok=True)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("QA TEMPLATE", encoding="utf-8")

    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        """
defaults:
  qa: dummy
  prompts:
    qa: qa-template
prompts:
  qa-template:
    path: prompts/qa.prompt.md
""".strip(),
        encoding="utf-8",
    )

    config = SimpleNamespace(
        agent_config_path=config_path,
        engine_defaults={},
        qa_model=None,
    )
    context = ServiceContext(config=config)

    registry = EngineRegistry()
    registry.register(DummyEngine(), default=True)
    monkeypatch.setattr("devgodzilla.engines.registry._registry", registry)

    db = Mock()
    step = Mock()
    step.id = 11
    step.step_name = "step-01"
    step.protocol_run_id = 21
    run = Mock()
    run.id = 21
    run.project_id = 31
    run.protocol_name = "demo"
    run.protocol_root = None
    run.worktree_path = None
    project = Mock()
    project.id = 31
    project.local_path = str(repo_root)

    db.get_step_run.return_value = step
    db.get_protocol_run.return_value = run
    db.get_project.return_value = project

    effective = EffectivePolicy(
        policy={},
        effective_hash="hash",
        pack_key="default",
        pack_version="1.0",
    )
    monkeypatch.setattr(
        "devgodzilla.services.quality.PolicyService.resolve_effective_policy",
        lambda *args, **kwargs: effective,
    )

    service = QualityService(context=context, db=db)
    qa_result = service.run_qa(step.id)

    prompt_gate = next((gate for gate in qa_result.gate_results if gate.gate_id == "prompt_qa"), None)
    assert prompt_gate is not None
    assert prompt_gate.metadata["prompt_path"] == str(prompt_path)
