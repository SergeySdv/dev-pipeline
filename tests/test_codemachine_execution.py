from pathlib import Path
import copy

from deksdenflow.domain import ProtocolStatus, StepStatus
from deksdenflow.engines import EngineMetadata, EngineRequest, EngineResult, registry
from deksdenflow.spec import PROTOCOL_SPEC_KEY
from deksdenflow.storage import Database
from deksdenflow.workers import codemachine_worker, codex_worker


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class FakeEngine:
    metadata = EngineMetadata(id="fake-engine", display_name="Fake", kind="cli", default_model="fake-model")

    def plan(self, req: EngineRequest) -> EngineResult:  # pragma: no cover - not used here
        return EngineResult(success=True, stdout="plan", stderr="")

    def execute(self, req: EngineRequest) -> EngineResult:
        return EngineResult(success=True, stdout=f"output for {req.step_run_id}", stderr="", metadata={"engine": self.metadata.id})

    def qa(self, req: EngineRequest) -> EngineResult:  # pragma: no cover - not used here
        return EngineResult(success=True, stdout="qa", stderr="")


def _register_fake_engine() -> None:
    try:
        registry.register(FakeEngine())
    except ValueError:
        # Already registered in another test run
        pass


def _make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    config_dir = workspace / ".codemachine" / "config"
    (workspace / ".codemachine" / "outputs").mkdir(parents=True, exist_ok=True)
    (workspace / "outputs").mkdir(parents=True, exist_ok=True)
    _write(
        config_dir / "main.agents.js",
        """
        export default [
          { "id": "build", "promptPath": "prompts/build.md", "engineId": "fake-engine", "model": "fake-model" }
        ];
        """,
    )
    _write(workspace / ".codemachine" / "prompts" / "build.md", "Build prompt")
    _write(workspace / ".codemachine" / "inputs" / "specifications.md", "Spec text")
    _write(workspace / ".codemachine" / "template.json", '{"template":"demo","version":"0.0.1"}')
    return workspace


def test_codemachine_execute_writes_outputs_and_events(tmp_path) -> None:
    _register_fake_engine()
    db = Database(tmp_path / "db.sqlite")
    db.init_schema()

    workspace = _make_workspace(tmp_path)
    project = db.create_project("demo", str(workspace), "main", None, None)
    run = db.create_protocol_run(project.id, "1234-demo", ProtocolStatus.PLANNED, "main", str(workspace), str(workspace / ".codemachine"), "demo protocol")
    codemachine_worker.import_codemachine_workspace(project.id, run.id, str(workspace), db)
    step = db.list_step_runs(run.id)[0]

    codex_worker.handle_execute_step(step.id, db)

    step_after = db.get_step_run(step.id)
    assert step_after.status == StepStatus.NEEDS_QA

    protocol_output = workspace / ".protocols" / run.protocol_name / f"{step.step_name}.md"
    codemachine_output = workspace / "outputs" / "build.md"
    assert protocol_output.exists()
    assert codemachine_output.exists()
    assert "output for" in protocol_output.read_text(encoding="utf-8")
    assert "output for" in codemachine_output.read_text(encoding="utf-8")

    events = [e.event_type for e in db.list_events(run.id)]
    assert "codemachine_step_completed" in events


def test_codemachine_quality_is_skipped(tmp_path) -> None:
    _register_fake_engine()
    db = Database(tmp_path / "db.sqlite")
    db.init_schema()

    workspace = _make_workspace(tmp_path)
    project = db.create_project("demo", str(workspace), "main", None, None)
    run = db.create_protocol_run(project.id, "5678-demo", ProtocolStatus.PLANNED, "main", str(workspace), str(workspace / ".codemachine"), "demo protocol")
    codemachine_worker.import_codemachine_workspace(project.id, run.id, str(workspace), db)
    step = db.list_step_runs(run.id)[0]

    codex_worker.handle_execute_step(step.id, db)
    codex_worker.handle_quality(step.id, db)

    step_after = db.get_step_run(step.id)
    assert step_after.status == StepStatus.COMPLETED
    events = [e.event_type for e in db.list_events(run.id)]
    assert "qa_skipped_codemachine" in events


def test_codemachine_quality_runs_when_policy_full(tmp_path) -> None:
    _register_fake_engine()
    db = Database(tmp_path / "db.sqlite")
    db.init_schema()

    workspace = _make_workspace(tmp_path)
    project = db.create_project("demo", str(workspace), "main", None, None)
    run = db.create_protocol_run(project.id, "8888-demo", ProtocolStatus.PLANNED, "main", str(workspace), str(workspace / ".codemachine"), "demo protocol")
    codemachine_worker.import_codemachine_workspace(project.id, run.id, str(workspace), db)

    # Flip QA policy to full for the first step via the stored protocol spec.
    run = db.get_protocol_run(run.id)
    template_cfg = copy.deepcopy(run.template_config or {})
    spec = template_cfg.get(PROTOCOL_SPEC_KEY) or {}
    steps = spec.get("steps") or []
    if steps:
        steps[0]["qa"] = {"policy": "full", "model": "fake-model"}
    template_cfg[PROTOCOL_SPEC_KEY] = spec
    db.update_protocol_template(run.id, template_cfg, run.template_source)

    step = db.list_step_runs(run.id)[0]
    codex_worker.handle_execute_step(step.id, db)
    codex_worker.handle_quality(step.id, db)

    step_after = db.get_step_run(step.id)
    assert step_after.status == StepStatus.COMPLETED
    events = [e.event_type for e in db.list_events(run.id)]
    assert "qa_passed" in events
