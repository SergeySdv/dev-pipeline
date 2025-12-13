"""
Codex worker: resolves protocol context, runs engine-backed planning/exec/QA, and updates DB.
"""

import json
import os
import shutil
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import tasksgodzilla.engines_codex  # noqa: F401 - ensure Codex engine is registered

from tasksgodzilla.codex import run_process

from tasksgodzilla.config import load_config
from tasksgodzilla.logging import get_logger, log_extra
from tasksgodzilla.domain import ProtocolRun, ProtocolStatus, StepRun, StepStatus
from tasksgodzilla.prompt_utils import prompt_version
from tasksgodzilla.errors import CodexCommandError
from tasksgodzilla.codemachine.runtime_adapter import (
    build_prompt_text,
    find_agent_for_step,
    is_codemachine_run,
    output_paths,
)
from tasksgodzilla.pipeline import (
    execute_step_prompt,
    planning_prompt,
    decompose_step_prompt,
    is_simple_step,
    step_markdown_files,
    write_protocol_files,
)
from tasksgodzilla.storage import BaseDatabase

from tasksgodzilla.metrics import metrics
from tasksgodzilla.engines import EngineRequest, registry
from tasksgodzilla.engine_resolver import resolve_prompt_and_outputs
from tasksgodzilla.workers.unified_runner import execute_step_unified, run_qa_unified
from tasksgodzilla.jobs import BaseQueue
from tasksgodzilla.project_setup import auto_clone_enabled
from tasksgodzilla.spec import (
    PROTOCOL_SPEC_KEY,
    build_spec_from_protocol_files,
    create_steps_from_spec,
    get_step_spec,
    protocol_spec_hash,
    resolve_spec_path,
    update_spec_meta,
    validate_step_spec_paths,
    validate_protocol_spec,
)
from tasksgodzilla.services.git import GitService
from tasksgodzilla.services.budget import BudgetService
from tasksgodzilla.services.orchestrator import OrchestratorService
from tasksgodzilla.services.spec import SpecService
from tasksgodzilla.services.prompts import PromptService
from tasksgodzilla.services.policy import PolicyService
from tasksgodzilla.services.clarifications import ClarificationsService

log = get_logger(__name__)
# MAX_INLINE_TRIGGER_DEPTH moved to OrchestratorService
SINGLE_WORKTREE = os.environ.get("TASKSGODZILLA_SINGLE_WORKTREE", "true").lower() in ("1", "true", "yes", "on")
DEFAULT_WORKTREE_BRANCH = os.environ.get("TASKSGODZILLA_WORKTREE_BRANCH", "tasksgodzilla-worktree")


def _ensure_required_step_sections(protocol_root: Path, required_sections: list[str]) -> list[str]:
    """
    Best-effort normalization: ensure each step markdown file contains headings for required sections.
    Returns a list of step filenames modified.
    """
    if not required_sections:
        return []
    modified: list[str] = []
    for step_file in step_markdown_files(protocol_root, include_setup=True):
        try:
            content = step_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lower = content.lower()
        missing: list[str] = []
        for section in required_sections:
            sec = (section or "").strip()
            if not sec:
                continue
            pattern = r"(?m)^#{1,6}\\s+" + re.escape(sec.lower()) + r"\\s*$"
            if re.search(pattern, lower):
                continue
            missing.append(sec)
        if not missing:
            continue
        blocks = []
        for sec in missing:
            blocks.append(f"\\n\\n## {sec}\\n\\n- TBD\\n")
        new_content = content.rstrip() + "".join(blocks) + "\\n"
        try:
            step_file.write_text(new_content, encoding="utf-8")
            modified.append(step_file.name)
        except Exception:
            continue
    return modified


def load_project(repo_root: Path, protocol_name: str, base_branch: str) -> Path:
    """
    Backward-compatible helper kept for tests and older integrations.

    Historically this function prepared a project worktree for a protocol run.
    The worker now delegates repo/worktree setup to GitService, so this is a
    no-op that returns the given repo_root.
    """
    return repo_root


def _load_project_with_context(repo_root: Path, *args, **kwargs) -> Path:
    """
    Legacy helper kept for unit tests.

    Previous versions enriched the repo with protocol context before execution.
    Context resolution is now handled by ExecutionService/QualityService.
    """
    return repo_root


def git_push_and_open_pr(*_args, **_kwargs) -> bool:
    """Legacy stub for tests; GitService handles push/PR now."""
    return False


def trigger_ci_pipeline(*_args, **_kwargs) -> bool:
    """Legacy stub for tests; GitService handles CI triggers now."""
    return False


def _log_context(
    run: Optional[ProtocolRun] = None,
    step: Optional[StepRun] = None,
    job_id: Optional[str] = None,
    project_id: Optional[int] = None,
    protocol_run_id: Optional[int] = None,
) -> dict:
    """
    Build a standard extra payload so job/protocol/step IDs are always populated.
    """
    return log_extra(
        job_id=job_id,
        project_id=project_id or (run.project_id if run else None),
        protocol_run_id=protocol_run_id or (run.id if run else None),
        step_run_id=step.id if step else None,
    )








def handle_plan_protocol(protocol_run_id: int, db: BaseDatabase, job_id: Optional[str] = None) -> None:
    run = db.get_protocol_run(protocol_run_id)
    project = db.get_project(run.project_id)
    config = load_config()
    planning_prompt_path = None
    workspace_hint: Optional[Path] = None
    protocol_hint: Optional[Path] = None
    git_service = GitService(db)
    budget_service = BudgetService()
    spec_service = SpecService(db)
    policy_service = PolicyService(db)
    clarifications_service = ClarificationsService(db)
    branch_name = git_service.get_branch_name(run.protocol_name)
    required_step_sections: list[str] = []
    policy_guidelines: Optional[str] = None

    # Resolve effective policy early so stub planning can also benefit.
    try:
        effective_policy = policy_service.resolve_effective_policy(project.id)
        policy_service.update_project_policy_effective_hash(project.id, effective_policy.effective_hash)
        policy_service.update_protocol_policy_audit(
            run.id,
            pack_key=effective_policy.pack_key,
            pack_version=effective_policy.pack_version,
            effective_hash=effective_policy.effective_hash,
            policy=effective_policy.policy if isinstance(effective_policy.policy, dict) else None,
        )
        # Materialize + gate on blocking clarifications before doing any planning work.
        try:
            clarifications_service.ensure_from_policy(
                project_id=project.id,
                policy=effective_policy.policy if isinstance(effective_policy.policy, dict) else {},
                applies_to="planning",
                protocol_run_id=run.id,
            )
        except Exception:
            pass
        blocking_project = clarifications_service.list_blocking_open(project_id=project.id, applies_to="onboarding")
        blocking_protocol = clarifications_service.list_blocking_open(protocol_run_id=run.id, applies_to="planning")
        if blocking_project or blocking_protocol:
            db.update_protocol_status(run.id, ProtocolStatus.BLOCKED)
            db.append_event(
                run.id,
                "planning_blocked_clarifications",
                "Planning blocked pending required clarifications.",
                metadata={
                    "project_id": project.id,
                    "protocol_run_id": run.id,
                    "blocking": {
                        "project": [c.__dict__ for c in blocking_project][:25],
                        "protocol": [c.__dict__ for c in blocking_protocol][:25],
                    },
                    "truncated": (len(blocking_project) > 25) or (len(blocking_protocol) > 25),
                },
            )
            return
        req = (effective_policy.policy.get("requirements") if isinstance(effective_policy.policy, dict) else {}) or {}
        defaults = (effective_policy.policy.get("defaults") if isinstance(effective_policy.policy, dict) else {}) or {}
        step_sections = req.get("step_sections") if isinstance(req, dict) else None
        if isinstance(step_sections, list):
            required_step_sections = [str(x) for x in step_sections if isinstance(x, (str, int, float))]
        protocol_files = req.get("protocol_files") if isinstance(req, dict) else None
        required_checks = []
        if isinstance(defaults, dict):
            ci = defaults.get("ci")
            if isinstance(ci, dict) and isinstance(ci.get("required_checks"), list):
                required_checks = [str(x) for x in ci.get("required_checks") if isinstance(x, (str, int, float))]
        step_template = None
        if required_step_sections:
            template_lines = []
            for sec in required_step_sections:
                template_lines.append(f"## {sec}")
                if sec.strip().lower() == "verification" and required_checks:
                    for check in required_checks:
                        template_lines.append(f"- Run `{check}`")
                else:
                    template_lines.append("- TBD")
                template_lines.append("")
            step_template = "\n".join(template_lines).strip()
        verification_snippet = None
        if required_checks:
            verification_snippet = "\n".join([f"- Run `{c}`" for c in required_checks])
        lines = [
            f"policy_pack: {effective_policy.pack_key}@{effective_policy.pack_version}",
            f"required_protocol_files: {protocol_files or []}",
            f"required_step_sections: {required_step_sections or []}",
            f"required_checks: {required_checks or []}",
            f"step_file_template:\n{step_template}" if step_template else "step_file_template: (none)",
            f"verification_snippet:\n{verification_snippet}" if verification_snippet else "verification_snippet: (none)",
            "note: warnings-only mode; prefer compliance.",
        ]
        policy_guidelines = "\n".join(lines)
    except Exception:
        policy_guidelines = None

    def _stub_plan(reason: str, *, error: Optional[str] = None) -> None:
        workspace_root, protocol_root = spec_service.resolve_protocol_paths(run, project)
        if workspace_hint:
            workspace_root = workspace_hint
        if protocol_hint:
            protocol_root = protocol_hint
        db.update_protocol_paths(protocol_run_id, str(workspace_root), str(protocol_root))
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "plan.md").write_text(f"# Plan for {run.protocol_name}\n\n- [ ] Execute demo step\n", encoding="utf-8")
        (protocol_root / "context.md").write_text(run.description or "Auto-generated stub context.", encoding="utf-8")
        (protocol_root / "log.md").write_text("", encoding="utf-8")
        setup_file = protocol_root / "00-setup.md"
        work_file = protocol_root / "01-demo.md"
        if not setup_file.exists():
            setup_file.write_text("Prepare workspace and dependencies.", encoding="utf-8")
        if not work_file.exists():
            work_file.write_text("Implement the demo task.", encoding="utf-8")

        modified = _ensure_required_step_sections(protocol_root, required_step_sections)
        if modified:
            db.append_event(
                protocol_run_id,
                "policy_autofix",
                f"Inserted missing required step sections into {len(modified)} file(s).",
                metadata={"files": modified, "mode": "warnings"},
                job_id=job_id,
            )

        template_cfg = dict(run.template_config or {})
        spec = template_cfg.get(PROTOCOL_SPEC_KEY)
        if not spec:
            spec = build_spec_from_protocol_files(protocol_root, default_qa_policy="skip")
            template_cfg[PROTOCOL_SPEC_KEY] = spec
            db.update_protocol_template(protocol_run_id, template_cfg, run.template_source)
        spec_hash_val = protocol_spec_hash(spec) if spec else None
        create_steps_from_spec(
            protocol_run_id,
            spec,
            db,
            existing_names={s.step_name for s in db.list_step_runs(protocol_run_id)},
        )
        update_spec_meta(db, protocol_run_id, template_cfg, run.template_source, status="valid", errors=[])
        db.update_protocol_status(protocol_run_id, ProtocolStatus.PLANNED)
        db.append_event(
            protocol_run_id,
            "planned",
            f"Protocol planned (stub; {reason}).",
            step_run_id=None,
            metadata={"spec_hash": spec_hash_val, "spec_validated": True, "fallback_reason": reason, "error": error},
        )
        try:
            project_findings = policy_service.evaluate_project(project.id)
            protocol_findings = policy_service.evaluate_protocol(run.id)
            findings = [*project_findings, *protocol_findings]
            if findings:
                db.append_event(
                    protocol_run_id,
                    "policy_findings",
                    f"Policy findings detected ({len(findings)}).",
                    metadata={"findings": [f.asdict() for f in findings[:25]], "truncated": len(findings) > 25},
                    job_id=job_id,
                )
        except Exception:
            pass
        log.warning(
            "planning_stubbed",
            extra={
                **_log_context(run=run, job_id=job_id),
                "reason": reason,
                "error": error,
                "protocol_root": str(protocol_root),
            },
        )
        return

    log.info(
        "Planning protocol",
        extra={
            **_log_context(run=run, job_id=job_id),
            "protocol_name": run.protocol_name,
            "branch": run.protocol_name,
        },
    )
    if shutil.which("codex") is None:
        _stub_plan("codex unavailable")
        return

    repo_root = git_service.ensure_repo_or_block(project, run, job_id=job_id)
    if repo_root is None:
        return

    worktree = git_service.ensure_worktree(
        repo_root,
        run.protocol_name,
        run.base_branch,
        protocol_run_id=run.id,
        project_id=project.id,
        job_id=job_id,
    )

    budget_limit = config.max_tokens_per_step or config.max_tokens_per_protocol
    planning_model = (
        (project.default_models or {}).get("planning")
        or config.planning_model
        or "gpt-5.1-codex-max"
    )
    protocol_root = worktree / ".protocols" / run.protocol_name
    workspace_hint = worktree
    protocol_hint = protocol_root
    db.update_protocol_paths(protocol_run_id, str(worktree), str(protocol_root))
    schema_path = repo_root / "schemas" / "protocol-planning.schema.json"
    planning_prompt_path = repo_root / "prompts" / "protocol-new.prompt.md"
    templates = planning_prompt_path.read_text(encoding="utf-8")
    planning_text = planning_prompt(
        protocol_name=run.protocol_name,
        protocol_number=run.protocol_name.split("-")[0],
        task_short_name=run.protocol_name.split("-", 1)[1],
        description=run.description or "",
        repo_root=repo_root,
        worktree_root=worktree,
        templates_section=templates,
        policy_guidelines=policy_guidelines,
    )
    planning_tokens = budget_service.check_and_track(
        planning_text, planning_model, "planning", config.token_budget_mode, budget_limit
    )
    engine = registry.get_default()
    planning_request = EngineRequest(
        project_id=project.id,
        protocol_run_id=run.id,
        step_run_id=0,
        model=planning_model,
        prompt_files=[],
        working_dir=str(worktree),
        extra={
            "prompt_text": planning_text,
            "sandbox": "read-only",
            "output_schema": str(schema_path),
        },
    )
    try:
        planning_result = engine.plan(planning_request)
        planning_json = (planning_result.stdout or "").strip()
        if not planning_json:
            raise ValueError("Empty planning result from Codex")
        data = json.loads(planning_json)
    except CodexCommandError as exc:
        db.update_protocol_status(run.id, ProtocolStatus.BLOCKED)
        db.append_event(
            protocol_run_id,
            "planning_failed",
            f"Codex planning failed: {exc}",
            metadata={
                "error": str(exc),
                "error_type": exc.__class__.__name__,
                "returncode": (exc.metadata or {}).get("returncode"),
            },
            job_id=job_id,
        )
        log.warning(
            "planning_codex_failed",
            extra={
                **_log_context(run=run, job_id=job_id),
                "error": str(exc),
                "error_type": exc.__class__.__name__,
                "returncode": (exc.metadata or {}).get("returncode"),
            },
        )
        raise
    except TimeoutError as exc:
        db.update_protocol_status(run.id, ProtocolStatus.BLOCKED)
        db.append_event(
            protocol_run_id,
            "planning_failed",
            "Codex planning timed out.",
            metadata={"error": str(exc), "error_type": "TimeoutError"},
            job_id=job_id,
        )
        log.warning(
            "planning_timeout",
            extra={**_log_context(run=run, job_id=job_id), "error": str(exc), "error_type": "TimeoutError"},
        )
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        db.update_protocol_status(run.id, ProtocolStatus.BLOCKED)
        db.append_event(
            protocol_run_id,
            "planning_failed",
            f"Invalid Codex planning output: {exc}",
            metadata={
                "error": str(exc),
                "error_type": exc.__class__.__name__,
                "stdout": (planning_result.stdout if 'planning_result' in locals() else None),
                "stderr": (planning_result.stderr if 'planning_result' in locals() else None),
            },
            job_id=job_id,
        )
        log.warning(
            "planning_output_invalid",
            extra={**_log_context(run=run, job_id=job_id), "error": str(exc), "error_type": exc.__class__.__name__},
        )
        raise
    write_protocol_files(protocol_root, data)
    created_steps = spec_service.sync_step_runs_from_protocol(protocol_root, protocol_run_id)

    # Decompose steps
    plan_md = (protocol_root / "plan.md").read_text(encoding="utf-8")
    decompose_tokens = 0
    decompose_model = (
        (project.default_models.get("decompose") if project.default_models else None)
        or config.decompose_model
        or "gpt-5.1-codex-max"
    )
    step_files = step_markdown_files(protocol_root)
    skip_simple = config.skip_simple_decompose
    decomposed_steps: List[str] = []
    skipped_steps: List[str] = []
    if step_files:
        db.append_event(
            protocol_run_id,
            "decompose_started",
            f"Decomposing {len(step_files)} step file(s).",
            metadata={"steps": [p.name for p in step_files], "model": decompose_model},
            job_id=job_id,
        )
    for step_file in step_files:
        step_content = step_file.read_text(encoding="utf-8")
        if skip_simple and is_simple_step(step_content):
            skipped_steps.append(step_file.name)
            log.info(
                "decompose_step_skipped",
                extra={**_log_context(run=run, job_id=job_id), "step_file": step_file.name, "reason": "simple_step"},
            )
            continue
        dec_text = decompose_step_prompt(
            run.protocol_name,
            run.protocol_name.split("-")[0],
            plan_md,
            step_file.name,
            step_content,
            policy_guidelines=policy_guidelines,
        )
        decompose_tokens += budget_service.check_and_track(
            dec_text, decompose_model, "decompose", config.token_budget_mode, budget_limit
        )
        decompose_request = EngineRequest(
            project_id=project.id,
            protocol_run_id=run.id,
            step_run_id=0,
            model=decompose_model,
            prompt_files=[],
            working_dir=str(worktree),
            extra={
                "prompt_text": dec_text,
                "sandbox": "read-only",
            },
        )
        decompose_result = engine.plan(decompose_request)
        new_content = decompose_result.stdout
        step_file.write_text(new_content, encoding="utf-8")
        decomposed_steps.append(step_file.name)
    modified = _ensure_required_step_sections(protocol_root, required_step_sections)
    if modified:
        db.append_event(
            protocol_run_id,
            "policy_autofix",
            f"Inserted missing required step sections into {len(modified)} file(s).",
            metadata={"files": modified, "mode": "warnings"},
            job_id=job_id,
        )
    if step_files:
        db.append_event(
            protocol_run_id,
            "decompose_completed",
            "Step decomposition finished.",
            metadata={
                "model": decompose_model,
                "steps_decomposed": decomposed_steps,
                "steps_skipped": skipped_steps,
                "estimated_tokens": {"decompose": decompose_tokens},
            },
            job_id=job_id,
        )

    # Emit warnings-only findings after planning/decomposition so UI can show them early.
    try:
        project_findings = policy_service.evaluate_project(project.id)
        protocol_findings = policy_service.evaluate_protocol(run.id)
        findings = [*project_findings, *protocol_findings]
        if findings:
            db.append_event(
                protocol_run_id,
                "policy_findings",
                f"Policy findings detected ({len(findings)}).",
                metadata={"findings": [f.asdict() for f in findings[:25]], "truncated": len(findings) > 25},
                job_id=job_id,
            )
        if policy_service.has_blocking_findings(findings):
            db.update_protocol_status(protocol_run_id, ProtocolStatus.BLOCKED)
            db.append_event(
                protocol_run_id,
                "policy_blocked",
                "Planning blocked by policy enforcement mode.",
                metadata={"blocking_findings": [f.asdict() for f in findings if f.severity == "block"][:25]},
                job_id=job_id,
            )
            return
    except Exception:
        pass

    db.update_protocol_status(protocol_run_id, ProtocolStatus.PLANNED)
    run = db.get_protocol_run(run.id)
    spec = (run.template_config or {}).get(PROTOCOL_SPEC_KEY)
    db.append_event(
        protocol_run_id,
        "planned",
        "Protocol planned via Codex.",
        step_run_id=None,
        metadata={
            "steps_created": created_steps,
            "protocol_root": str(protocol_root),
            "models": {"planning": planning_model, "decompose": decompose_model},
            "prompt_versions": {"planning": prompt_version(planning_prompt_path)},
            "estimated_tokens": {"planning": planning_tokens, "decompose": decompose_tokens},
            "spec_hash": protocol_spec_hash(spec) if spec else None,
            "spec_validated": True,
        },
    )

    # Best-effort push/PR to surface changes in CI
    pushed = git_service.push_and_open_pr(
        worktree,
        run.protocol_name,
        run.base_branch,
        protocol_run_id=run.id,
        project_id=project.id,
        job_id=job_id,
    )
    if pushed:
        triggered = git_service.trigger_ci(
            repo_root,
            run.protocol_name,
            project.ci_provider,
            protocol_run_id=run.id,
            project_id=project.id,
            job_id=job_id,
        )
        if triggered:
            db.append_event(protocol_run_id, "ci_triggered", "CI triggered after planning push.", metadata={"branch": run.protocol_name})


def handle_execute_step(step_run_id: int, db: BaseDatabase, job_id: Optional[str] = None) -> None:
    """Execute a protocol step (thin adapter to ExecutionService)."""
    from tasksgodzilla.services.execution import ExecutionService
    execution_service = ExecutionService(db)
    execution_service.execute_step(step_run_id, job_id=job_id)


def handle_quality(step_run_id: int, db: BaseDatabase, job_id: Optional[str] = None) -> None:
    """Run QA for a protocol step (thin adapter to QualityService)."""
    from tasksgodzilla.services.quality import QualityService
    quality_service = QualityService(db=db)
    quality_service.run_for_step_run(step_run_id, job_id=job_id)


def handle_open_pr(protocol_run_id: int, db: BaseDatabase, job_id: Optional[str] = None) -> None:
    run = db.get_protocol_run(protocol_run_id)
    project = db.get_project(run.project_id)
    git_service = GitService(db)
    
    repo_root = git_service.ensure_repo_or_block(project, run, job_id=job_id)
    if not repo_root:
        db.append_event(
            run.id,
            "open_pr_skipped",
            "Repo not available locally; cannot push or open PR/MR.",
            metadata={"git_url": project.git_url},
        )
        return
    try:
        worktree = git_service.ensure_worktree(
            repo_root,
            run.protocol_name,
            run.base_branch,
            protocol_run_id=run.id,
            project_id=project.id,
            job_id=job_id,
        )
        branch_name = git_service.get_branch_name(run.protocol_name)
        pushed = git_service.push_and_open_pr(
            worktree,
            run.protocol_name,
            run.base_branch,
            protocol_run_id=run.id,
            project_id=project.id,
            job_id=job_id,
        )
        if pushed:
            db.append_event(run.id, "open_pr", "Branch pushed and PR/MR requested.", metadata={"branch": branch_name})
            triggered = git_service.trigger_ci(
                repo_root,
                branch_name,
                project.ci_provider,
                protocol_run_id=run.id,
                project_id=project.id,
                job_id=job_id,
            )
            if triggered:
                db.append_event(
                    run.id,
                    "ci_triggered",
                    "CI triggered after PR/MR request.",
                    metadata={"branch": run.protocol_name},
                )
            db.update_protocol_status(run.id, ProtocolStatus.RUNNING)
        else:
            if git_service.remote_branch_exists(repo_root, run.protocol_name):
                db.append_event(
                    run.id,
                    "open_pr_branch_exists",
                    "Branch already exists remotely; skipping push/PR.",
                    metadata={"branch": run.protocol_name},
                )
                db.update_protocol_status(run.id, ProtocolStatus.RUNNING)
            else:
                db.append_event(
                    run.id,
                    "open_pr_failed",
                    "Failed to push branch or open PR/MR.",
                    metadata={"branch": run.protocol_name},
                )
                db.update_protocol_status(run.id, ProtocolStatus.BLOCKED)
    except Exception as exc:  # pragma: no cover - best effort
        log.warning(
            "Open PR job failed",
            extra={
                **_log_context(run=run, job_id=job_id),
                "protocol_name": run.protocol_name,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            },
        )
        db.append_event(
            run.id,
            "open_pr_failed",
            f"Open PR/MR failed: {exc}",
            metadata={"branch": run.protocol_name},
        )
        db.update_protocol_status(run.id, ProtocolStatus.BLOCKED)
