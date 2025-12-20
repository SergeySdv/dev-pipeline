"""
DevGodzilla Discovery Agent Service

Runs repository discovery via an AI engine (typically `opencode`) using prompt files
that instruct the agent to write durable artifacts into the repo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from devgodzilla.engines import EngineNotFoundError, EngineRequest, SandboxMode, get_registry
from devgodzilla.logging import get_logger
from devgodzilla.services.base import Service, ServiceContext
from devgodzilla.services.agent_config import AgentConfigService
from devgodzilla.spec import resolve_spec_path

logger = get_logger(__name__)


@dataclass
class DiscoveryStageResult:
    stage: str
    prompt_path: Path
    success: bool
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None


@dataclass
class DiscoveryResult:
    success: bool
    engine_id: str
    model: Optional[str]
    repo_root: Path
    log_path: Path
    stages: list[DiscoveryStageResult] = field(default_factory=list)
    expected_outputs: list[Path] = field(default_factory=list)
    missing_outputs: list[Path] = field(default_factory=list)
    error: Optional[str] = None


def _resolve_prompt(repo_root: Path, *, prompt_name: str) -> Path:
    repo_local = repo_root / "prompts" / prompt_name
    if repo_local.is_file():
        return repo_local
    fallback = Path(__file__).resolve().parents[2] / "prompts" / prompt_name
    return fallback


class DiscoveryAgentService(Service):
    def __init__(self, context: ServiceContext) -> None:
        super().__init__(context)

    def run_discovery(
        self,
        *,
        repo_root: Path,
        engine_id: str = "opencode",
        model: Optional[str] = None,
        pipeline: bool = True,
        stages: Optional[list[str]] = None,
        timeout_seconds: int = 900,
        strict_outputs: bool = True,
        project_id: Optional[int] = None,
    ) -> DiscoveryResult:
        repo_root = repo_root.expanduser().resolve()
        log_path = repo_root / "opencode-discovery.log"

        stage_map = (
            {
                "inventory": "discovery-inventory.prompt.md",
                "architecture": "discovery-architecture.prompt.md",
                "api_reference": "discovery-api-reference.prompt.md",
                "ci_notes": "discovery-ci-notes.prompt.md",
            }
            if pipeline
            else {"repo_discovery": "repo-discovery.prompt.md"}
        )

        selected = list(stage_map.keys()) if stages is None else stages

        registry = get_registry()
        try:
            engine = registry.get(engine_id)
        except EngineNotFoundError as e:
            return DiscoveryResult(
                success=False,
                engine_id=engine_id,
                model=model,
                repo_root=repo_root,
                log_path=log_path,
                error=f"Engine not registered: {e}",
            )

        if not engine.check_availability():
            return DiscoveryResult(
                success=False,
                engine_id=engine_id,
                model=model,
                repo_root=repo_root,
                log_path=log_path,
                error=f"Engine unavailable: {engine_id}",
            )

        run_model = model or engine.metadata.default_model

        self.logger.info(
            "discovery_agent_start",
            extra=self.log_extra(repo_root=str(repo_root), engine_id=engine_id, model=run_model, pipeline=pipeline),
        )

        results: list[DiscoveryStageResult] = []
        for stage in selected:
            prompt_name = stage_map.get(stage)
            if not prompt_name:
                results.append(
                    DiscoveryStageResult(
                        stage=stage,
                        prompt_path=Path("<unknown>"),
                        success=False,
                        error=f"Unknown stage: {stage}",
                    )
                )
                continue

            prompt_path = _resolve_prompt(repo_root, prompt_name=prompt_name)
            try:
                cfg = AgentConfigService(self.context)
                assignment = cfg.resolve_prompt_assignment(f"discovery.{stage}", project_id=project_id)
                if not assignment:
                    assignment = cfg.resolve_prompt_assignment("discovery", project_id=project_id)
                if assignment and assignment.get("path"):
                    candidate = resolve_spec_path(str(assignment["path"]), repo_root, repo_root)
                    if candidate.exists():
                        prompt_path = candidate
                    else:
                        self.logger.warning(
                            "discovery_prompt_assignment_missing",
                            extra=self.log_extra(
                                project_id=project_id,
                                prompt_path=str(candidate),
                                stage=stage,
                            ),
                        )
            except Exception:
                prompt_path = prompt_path
            if not prompt_path.is_file():
                results.append(
                    DiscoveryStageResult(
                        stage=stage,
                        prompt_path=prompt_path,
                        success=False,
                        error=f"Prompt missing: {prompt_name}",
                    )
                )
                continue

            prompt_text = prompt_path.read_text(encoding="utf-8")
            req = EngineRequest(
                project_id=None,
                protocol_run_id=None,
                step_run_id=None,
                model=run_model,
                prompt_text=prompt_text,
                prompt_files=[str(prompt_path)],
                working_dir=str(repo_root),
                sandbox=SandboxMode.WORKSPACE_WRITE,
                timeout=timeout_seconds,
                extra={"output_format": "text", "job_id": "discovery"},
            )
            engine_result = engine.execute(req)

            # Best-effort aggregated log for debugging.
            try:
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(f"\n\n===== discovery stage: {stage} ({prompt_name}) =====\n")
                    if engine_result.stdout:
                        f.write(engine_result.stdout)
                    if engine_result.stderr:
                        f.write("\n[stderr]\n")
                        f.write(engine_result.stderr)
            except Exception:
                pass

            results.append(
                DiscoveryStageResult(
                    stage=stage,
                    prompt_path=prompt_path,
                    success=engine_result.success,
                    stdout=engine_result.stdout,
                    stderr=engine_result.stderr,
                    error=engine_result.error,
                )
            )

        expected = self._expected_outputs(pipeline=pipeline)
        missing = [p for p in expected if not (repo_root / p).exists()]

        success = all(r.success for r in results) and (not missing if strict_outputs else True)
        error = None
        if not success:
            error = "Discovery failed"
            if missing and strict_outputs:
                error = f"Missing discovery outputs: {', '.join(str(p) for p in missing)}"

        return DiscoveryResult(
            success=success,
            engine_id=engine_id,
            model=run_model,
            repo_root=repo_root,
            log_path=log_path,
            stages=results,
            expected_outputs=[repo_root / p for p in expected],
            missing_outputs=[repo_root / p for p in missing],
            error=error,
        )

    def _expected_outputs(self, *, pipeline: bool) -> list[Path]:
        base = Path("tasksgodzilla")
        if pipeline:
            return [
                base / "DISCOVERY.md",
                base / "DISCOVERY_SUMMARY.json",
                base / "ARCHITECTURE.md",
                base / "API_REFERENCE.md",
                base / "CI_NOTES.md",
            ]
        return [
            base / "DISCOVERY.md",
            base / "ARCHITECTURE.md",
            base / "API_REFERENCE.md",
            base / "CI_NOTES.md",
        ]


def parse_discovery_summary(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("DISCOVERY_SUMMARY.json must be a JSON object")
    return data
