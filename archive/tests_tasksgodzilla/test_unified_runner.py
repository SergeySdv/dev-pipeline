from pathlib import Path

from tasksgodzilla.engines import EngineMetadata, EngineRequest, EngineResult, registry
from tasksgodzilla.engine_resolver import resolve_prompt_and_outputs
from tasksgodzilla.prompt_utils import fingerprint_file
from tasksgodzilla.workers.unified_runner import execute_step_unified, run_qa_unified


class EchoEngine:
    metadata = EngineMetadata(id="runner-echo", display_name="Echo", kind="cli", default_model="echo-model")

    def execute(self, req: EngineRequest) -> EngineResult:
        prompt_text = (req.extra or {}).get("prompt_text", "")
        return EngineResult(success=True, stdout=prompt_text, stderr="", metadata={"engine": self.metadata.id})

    def qa(self, req: EngineRequest) -> EngineResult:
        prompt_text = (req.extra or {}).get("prompt_text", "")
        return EngineResult(success=True, stdout=prompt_text, stderr="", metadata={"engine": self.metadata.id})

    def plan(self, req: EngineRequest) -> EngineResult:  # pragma: no cover - unused
        return EngineResult(success=True, stdout="", stderr="")


def _register_echo_engine() -> None:
    try:
        registry.register(EchoEngine())
    except ValueError:
        # Already registered in another test run
        pass


def test_execute_step_unified_writes_outputs(tmp_path: Path) -> None:
    _register_echo_engine()
    workspace = tmp_path / "repo"
    protocol_root = workspace / ".protocols" / "1234-demo"
    protocol_root.mkdir(parents=True, exist_ok=True)
    prompt_path = protocol_root / "01-step.md"
    prompt_path.write_text("Hello from prompt", encoding="utf-8")

    step_spec = {
        "name": "01-step.md",
        "engine_id": "runner-echo",
        "model": "echo-model",
        "prompt_ref": str(prompt_path),
        "outputs": {"protocol": "outputs/protocol.md", "aux": {"extra": "outputs/aux.md"}},
        "qa": {"policy": "skip"},
    }
    resolution = resolve_prompt_and_outputs(
        step_spec,
        protocol_root=protocol_root,
        workspace_root=workspace,
        protocol_spec={"steps": [step_spec]},
        default_engine_id="runner-echo",
    )

    result = execute_step_unified(resolution, project_id=1, protocol_run_id=2, step_run_id=3)

    protocol_out = protocol_root / "outputs" / "protocol.md"
    aux_out = protocol_root / "outputs" / "aux.md"
    assert protocol_out.read_text(encoding="utf-8") == "Hello from prompt"
    assert aux_out.read_text(encoding="utf-8") == "Hello from prompt"
    outputs_meta = result.metadata["outputs"]
    assert outputs_meta["protocol"].endswith("protocol.md")
    assert outputs_meta["aux"]["extra"].endswith("aux.md")
    assert result.metadata["prompt_versions"]["exec"] == fingerprint_file(prompt_path)


def test_run_qa_unified_returns_metadata(tmp_path: Path) -> None:
    _register_echo_engine()
    workspace = tmp_path / "repo"
    protocol_root = workspace / ".protocols" / "5678-demo"
    protocol_root.mkdir(parents=True, exist_ok=True)
    prompt_path = protocol_root / "01-step.md"
    prompt_path.write_text("Prompt", encoding="utf-8")
    qa_prompt = protocol_root / "qa.prompt.md"
    qa_prompt.write_text("qa prompt", encoding="utf-8")

    step_spec = {
        "name": "01-step.md",
        "engine_id": "runner-echo",
        "model": "echo-model",
        "prompt_ref": str(prompt_path),
        "outputs": {"protocol": str(prompt_path)},
        "qa": {"policy": "full"},
    }
    resolution = resolve_prompt_and_outputs(
        step_spec,
        protocol_root=protocol_root,
        workspace_root=workspace,
        protocol_spec={"steps": [step_spec]},
        default_engine_id="runner-echo",
    )

    qa_result = run_qa_unified(
        resolution,
        project_id=1,
        protocol_run_id=2,
        step_run_id=3,
        qa_prompt_path=qa_prompt,
        qa_prompt_text="REPORT\nVERDICT: PASS",
        qa_engine_id="runner-echo",
        qa_model="echo-model",
        sandbox="read-only",
    )

    assert qa_result.result.stdout.strip().endswith("PASS")
    assert qa_result.metadata["engine_id"] == "runner-echo"
    assert qa_result.metadata["prompt_versions"]["qa"] == fingerprint_file(qa_prompt)
