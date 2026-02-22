from __future__ import annotations

import json
from pathlib import Path

from devgodzilla.engines.interface import Engine, EngineKind, EngineMetadata, EngineRequest, EngineResult
from devgodzilla.engines.registry import EngineRegistry
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.discovery_agent import DiscoveryAgentService


class UnavailableEngine(Engine):
    @property
    def metadata(self) -> EngineMetadata:
        return EngineMetadata(
            id="opencode",
            display_name="Unavailable engine (test)",
            kind=EngineKind.CLI,
            default_model=None,
            description="Test engine that is always unavailable.",
            capabilities=["execute"],
        )

    def check_availability(self) -> bool:
        return False

    def plan(self, req: EngineRequest) -> EngineResult:
        raise RuntimeError("plan should not be called when engine is unavailable")

    def execute(self, req: EngineRequest) -> EngineResult:
        raise RuntimeError("execute should not be called when engine is unavailable")

    def qa(self, req: EngineRequest) -> EngineResult:
        raise RuntimeError("qa should not be called when engine is unavailable")


def test_discovery_fallback_writes_expected_outputs(tmp_path, monkeypatch) -> None:
    from devgodzilla.engines.dummy import DummyEngine

    registry = EngineRegistry()
    registry.register(UnavailableEngine())
    registry.register(DummyEngine(), default=True)
    monkeypatch.setattr("devgodzilla.engines.registry._registry", registry)

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)

    context = ServiceContext(config=None)
    service = DiscoveryAgentService(context)
    result = service.run_discovery(
        repo_root=repo_root,
        engine_id="opencode",
        pipeline=True,
        strict_outputs=True,
    )

    assert result.success is True

    runtime_dir = repo_root / "specs" / "discovery" / "_runtime"
    assert (runtime_dir / "DISCOVERY.md").exists()
    assert (runtime_dir / "DISCOVERY_SUMMARY.json").exists()

    summary = json.loads((runtime_dir / "DISCOVERY_SUMMARY.json").read_text(encoding="utf-8"))
    assert isinstance(summary, dict)
    assert "languages" in summary
