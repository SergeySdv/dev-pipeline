"""
Shared protocol/step specification helpers to unify Codex and CodeMachine paths.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from deksdenflow.codemachine.config_loader import AgentSpec, CodeMachineConfig
from deksdenflow.domain import StepStatus
from deksdenflow.storage import BaseDatabase

# Key used inside protocol_run.template_config to persist the normalized spec.
PROTOCOL_SPEC_KEY = "protocol_spec"


def infer_step_type_from_name(name: str) -> str:
    lower = name.lower()
    if lower.startswith("00-") or "setup" in lower:
        return "setup"
    if "qa" in lower:
        return "qa"
    return "work"


def build_spec_from_protocol_files(
    protocol_root: Path,
    default_engine_id: str = "codex",
    default_qa_policy: str = "full",
    default_qa_prompt: str = "prompts/quality-validator.prompt.md",
) -> Dict[str, Any]:
    """
    Create a ProtocolSpec from Codex-generated step files.
    """
    steps: List[Dict[str, Any]] = []
    step_files = sorted([p for p in protocol_root.glob("*.md") if p.name[0:2].isdigit()])
    for idx, path in enumerate(step_files):
        steps.append(
            {
                "id": path.stem,
                "name": path.name,
                "engine_id": default_engine_id,
                "model": None,
                "prompt_ref": str(path),
                "outputs": {"protocol": str(path)},
                "step_type": infer_step_type_from_name(path.name),
                "policies": [],
                "qa": {"policy": default_qa_policy, "prompt": default_qa_prompt},
                "order": idx,
            }
        )
    return {"steps": steps}


def _policies_for_agent(agent: AgentSpec, modules: List[Any]) -> List[dict]:
    """
    Attach module policies to a CodeMachine agent when explicitly referenced.
    Mirrors the previous worker logic but centralized for spec generation.
    """
    from deksdenflow.codemachine.config_loader import policy_to_dict  # local import to avoid cycles

    policies: List[dict] = []
    agent_modules = agent.raw.get("moduleId") or agent.raw.get("module_id") or agent.raw.get("module")
    agent_module_ids = set()
    if isinstance(agent_modules, str):
        agent_module_ids.add(agent_modules)
    elif isinstance(agent_modules, list):
        agent_module_ids.update(str(m) for m in agent_modules)

    for mod in modules:
        target_agent = (mod.target_agent_id or mod.raw.get("targetAgentId") or mod.raw.get("target_agent_id") or "").strip()
        should_attach = False
        if mod.module_id in agent_module_ids:
            should_attach = True
        if target_agent and target_agent == agent.id:
            should_attach = True
        if getattr(mod, "behavior", None) == "trigger" and mod.trigger_agent_id == agent.id:
            should_attach = True
        if should_attach:
            policies.append(policy_to_dict(mod))
    return policies


def build_spec_from_codemachine_config(
    cfg: CodeMachineConfig,
    qa_policy: str = "skip",
    qa_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a ProtocolSpec from a CodeMachine config (main agents only).
    Defaults to skipping QA to mirror current behavior until QA is normalized.
    """
    steps: List[Dict[str, Any]] = []
    for idx, agent in enumerate(cfg.main_agents):
        step_name = f"{idx:02d}-{agent.id}"
        steps.append(
            {
                "id": agent.id,
                "name": step_name,
                "engine_id": agent.engine_id,
                "model": agent.model,
                "prompt_ref": agent.prompt_path,
                "outputs": {"aux": {"codemachine": f"outputs/{agent.id}.md"}},
                "step_type": infer_step_type_from_name(step_name),
                "policies": _policies_for_agent(agent, cfg.modules),
                "qa": {"policy": qa_policy, "prompt": qa_prompt},
                "order": idx,
                "description": agent.description,
            }
        )
    return {"steps": steps, "placeholders": cfg.placeholders, "template": cfg.template}


def create_steps_from_spec(
    protocol_run_id: int,
    spec: Dict[str, Any],
    db: BaseDatabase,
    existing_names: Optional[set] = None,
) -> int:
    """
    Materialize StepRun rows from a ProtocolSpec; skips already-present steps.
    """
    created = 0
    existing = existing_names or set()
    steps = spec.get("steps") or []
    for idx, step in enumerate(steps):
        step_name = str(step.get("name") or step.get("id") or f"{idx:02d}-step")
        if step_name in existing:
            continue
        db.create_step_run(
            protocol_run_id=protocol_run_id,
            step_index=idx,
            step_name=step_name,
            step_type=str(step.get("step_type") or infer_step_type_from_name(step_name)),
            status=StepStatus.PENDING,
            model=step.get("model"),
            engine_id=step.get("engine_id"),
            policy=step.get("policies"),
            summary=step.get("description"),
        )
        created += 1
    return created


def get_step_spec(template_config: Optional[dict], step_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the spec entry for a given step name from a protocol template_config.
    """
    if not template_config:
        return None
    spec = template_config.get(PROTOCOL_SPEC_KEY) if isinstance(template_config, dict) else None
    if not spec:
        return None
    steps = spec.get("steps") or []
    for step in steps:
        name = str(step.get("name") or step.get("id") or "")
        if name == step_name:
            return step
    return None


def validate_step_spec_paths(base: Path, step_spec: Dict[str, Any]) -> List[str]:
    """
    Validate prompt_ref and output paths exist (if relative, resolved from base).
    Returns a list of errors; empty list if valid.
    """
    errors: List[str] = []
    prompt_ref = step_spec.get("prompt_ref")
    if prompt_ref:
        pr_path = Path(prompt_ref)
        if not pr_path.is_absolute():
            pr_path = (base / pr_path).resolve()
        if not pr_path.exists():
            errors.append(f"prompt_ref missing: {pr_path}")
    return errors


def validate_protocol_spec(base: Path, spec: Dict[str, Any]) -> List[str]:
    """
    Validate all steps in a protocol spec relative to a base path.
    """
    if not spec or not isinstance(spec, dict):
        return ["protocol spec missing or malformed"]
    steps = spec.get("steps")
    if not isinstance(steps, list):
        return ["protocol spec steps must be a list"]
    errors: List[str] = []
    for step in steps:
        step_name = str(step.get("name") or step.get("id") or "(unknown)")
        errs = validate_step_spec_paths(base, step)
        errors.extend([f"{step_name}: {e}" for e in errs])
    return errors
