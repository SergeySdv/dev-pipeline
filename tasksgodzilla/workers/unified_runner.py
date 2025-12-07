"""
Skeleton runner that uses the unified resolver + engine registry for both execute and QA.

This is not wired into the workers yet. It exists to make the refactor mechanical:
- Resolve prompt/outputs via `tasksgodzilla.engines.resolver`.
- Build an EngineRequest with consistent sandbox/prompt handling.
- Dispatch through the registry (Codex, CodeMachine, future engines).
- Hand back event-ready metadata for the caller to persist.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from tasksgodzilla.engines import EngineRequest, EngineResult, registry
from tasksgodzilla.engine_resolver import StepResolution
from tasksgodzilla.prompt_utils import prompt_version


@dataclass
class ExecutionSkeleton:
    resolution: StepResolution
    request: EngineRequest
    result: Optional[EngineResult]
    outputs_written: Dict[str, str]
    metadata: Dict[str, Any]


@dataclass
class QASkeleton:
    request: EngineRequest
    result: Optional[EngineResult]
    metadata: Dict[str, Any]


def build_engine_request(
    resolution: StepResolution,
    *,
    project_id: int,
    protocol_run_id: int,
    step_run_id: int,
    sandbox: str,
    prompt_text: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> EngineRequest:
    """
    Construct an EngineRequest from the resolved step data. Callers fill in IDs.
    """
    payload: Dict[str, Any] = {"prompt_text": prompt_text or resolution.prompt_text, "sandbox": sandbox}
    if extra:
        payload.update(extra)
    return EngineRequest(
        project_id=project_id,
        protocol_run_id=protocol_run_id,
        step_run_id=step_run_id,
        model=resolution.model,
        prompt_files=[str(resolution.prompt_path)],
        working_dir=str(resolution.workdir),
        extra=payload,
    )


def execute_step_unified(
    resolution: StepResolution,
    *,
    project_id: int,
    protocol_run_id: int,
    step_run_id: int,
    sandbox: str = "workspace-write",
    write_outputs: bool = True,
    extra: Optional[Dict[str, Any]] = None,
) -> ExecutionSkeleton:
    """
    Run execution through the registry. Returns the raw EngineResult plus
    minimal metadata the worker can attach to events.
    """
    engine = registry.get(resolution.engine_id)
    request = build_engine_request(
        resolution,
        project_id=project_id,
        protocol_run_id=protocol_run_id,
        step_run_id=step_run_id,
        sandbox=sandbox,
        extra=extra,
    )
    result: Optional[EngineResult] = None
    outputs_written: Dict[str, str] = {}
    try:
        result = engine.execute(request)
    finally:
        if write_outputs and result and result.stdout:
            if resolution.outputs.protocol:
                resolution.outputs.protocol.parent.mkdir(parents=True, exist_ok=True)
                resolution.outputs.protocol.write_text(result.stdout, encoding="utf-8")
                outputs_written["protocol"] = str(resolution.outputs.protocol)
            for name, path in resolution.outputs.aux.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(result.stdout, encoding="utf-8")
                outputs_written[f"aux.{name}"] = str(path)

    aux_meta: Dict[str, str] = {}
    for key, val in outputs_written.items():
        if key.startswith("aux."):
            aux_meta[key.split("aux.", 1)[1]] = val

    metadata = {
        "engine_id": resolution.engine_id,
        "model": resolution.model,
        "prompt_versions": {"exec": resolution.prompt_version},
        "spec_hash": resolution.spec_hash,
        "outputs": {"protocol": outputs_written.get("protocol"), "aux": aux_meta},
        "agent_id": resolution.agent_id,
        "step_name": resolution.step_name,
    }
    return ExecutionSkeleton(
        resolution=resolution,
        request=request,
        result=result,
        outputs_written=outputs_written,
        metadata=metadata,
    )


def run_qa_unified(
    resolution: StepResolution,
    *,
    project_id: int,
    protocol_run_id: int,
    step_run_id: int,
    qa_prompt_path: Path,
    qa_prompt_text: str,
    qa_engine_id: Optional[str] = None,
    qa_model: Optional[str] = None,
    sandbox: str = "read-only",
    extra: Optional[Dict[str, Any]] = None,
) -> QASkeleton:
    """
    Run QA through the registry using the resolved step defaults unless overrides are provided.
    """
    engine_id = qa_engine_id or resolution.engine_id
    engine = registry.get(engine_id)
    payload: Dict[str, Any] = {"prompt_text": qa_prompt_text, "sandbox": sandbox}
    if extra:
        payload.update(extra)
    request = EngineRequest(
        project_id=project_id,
        protocol_run_id=protocol_run_id,
        step_run_id=step_run_id,
        model=qa_model or resolution.qa.get("model") or resolution.model,
        prompt_files=[str(qa_prompt_path)],
        working_dir=str(resolution.workdir),
        extra=payload,
    )
    result: Optional[EngineResult] = None
    try:
        result = engine.qa(request)
    except Exception:
        result = None
    metadata = {
        "engine_id": engine_id,
        "model": request.model,
        "prompt_versions": {"qa": prompt_version(qa_prompt_path)},
        "spec_hash": resolution.spec_hash,
        "agent_id": resolution.agent_id,
        "step_name": resolution.step_name,
    }
    return QASkeleton(request=request, result=result, metadata=metadata)
