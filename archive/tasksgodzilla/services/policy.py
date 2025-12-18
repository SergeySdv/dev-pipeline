from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Optional

from tasksgodzilla.logging import get_logger
from tasksgodzilla.storage import BaseDatabase, DEFAULT_POLICY_PACK_KEY, DEFAULT_POLICY_PACK_VERSION

log = get_logger(__name__)

_DEFAULT_BLOCK_CODES = {
    "policy.ci.required_check_missing",
    "policy.ci.required_check_not_executable",
    "policy.protocol.missing_file",
    "policy.step.missing_section",
    "policy.step.file_missing",
}


def _sanitize_policy_override(override: dict[str, Any]) -> dict[str, Any]:
    """
    Allow only a conservative subset of keys from overrides (central/user/repo-local).
    Prevents unexpected keys from influencing execution behavior.
    """
    allowed_top = {"defaults", "requirements", "clarifications", "enforcement", "constraints"}
    sanitized: dict[str, Any] = {}
    for k, v in override.items():
        if k in allowed_top:
            sanitized[k] = v
    return sanitized


def validate_policy_pack_definition(
    *,
    pack_key: str,
    pack_version: str,
    pack: Any,
) -> list[str]:
    """
    Validate a policy pack payload for basic shape and safety.
    Returns a list of human-readable error strings; empty means valid.
    """
    errors: list[str] = []
    if not isinstance(pack, dict):
        return ["pack must be a JSON object"]

    # Prevent extremely large policy packs from being stored/merged.
    try:
        raw = json.dumps(pack, ensure_ascii=False)
        if len(raw.encode("utf-8")) > 256_000:
            errors.append("pack too large (max 256KB)")
    except Exception:
        errors.append("pack must be JSON-serializable")
        return errors

    allowed_top = {"meta", "defaults", "requirements", "clarifications", "enforcement", "constraints"}
    extra_top = [k for k in pack.keys() if k not in allowed_top]
    if extra_top:
        errors.append(f"pack has unsupported top-level keys: {', '.join(sorted(map(str, extra_top)))}")

    meta = pack.get("meta")
    if not isinstance(meta, dict):
        errors.append("pack.meta must be an object")
    else:
        mk = meta.get("key")
        mv = meta.get("version")
        mn = meta.get("name")
        if not isinstance(mk, str) or not mk.strip():
            errors.append("pack.meta.key must be a non-empty string")
        if not isinstance(mv, str) or not mv.strip():
            errors.append("pack.meta.version must be a non-empty string")
        if mn is not None and not isinstance(mn, str):
            errors.append("pack.meta.name must be a string")
        if isinstance(mk, str) and mk != pack_key:
            errors.append("pack.meta.key must match payload.key")
        if isinstance(mv, str) and mv != pack_version:
            errors.append("pack.meta.version must match payload.version")

    enforcement = pack.get("enforcement")
    if enforcement is not None and not isinstance(enforcement, dict):
        errors.append("pack.enforcement must be an object")
    elif isinstance(enforcement, dict):
        mode = enforcement.get("mode")
        if mode is not None and mode not in ("warn", "block"):
            errors.append("pack.enforcement.mode must be 'warn' or 'block'")
        block_codes = enforcement.get("block_codes")
        if block_codes is not None:
            if not isinstance(block_codes, list):
                errors.append("pack.enforcement.block_codes must be a list")
            else:
                if len(block_codes) > 200:
                    errors.append("pack.enforcement.block_codes too long (max 200)")
                bad = [c for c in block_codes if not isinstance(c, (str, int, float))]
                if bad:
                    errors.append("pack.enforcement.block_codes must contain strings/numbers only")

    requirements = pack.get("requirements")
    if requirements is not None and not isinstance(requirements, dict):
        errors.append("pack.requirements must be an object")
    elif isinstance(requirements, dict):
        step_sections = requirements.get("step_sections")
        if step_sections is not None:
            if not isinstance(step_sections, list) or not all(isinstance(s, str) and s.strip() for s in step_sections):
                errors.append("pack.requirements.step_sections must be a list of non-empty strings")
            elif len(step_sections) > 30:
                errors.append("pack.requirements.step_sections too long (max 30)")
        protocol_files = requirements.get("protocol_files")
        if protocol_files is not None:
            if not isinstance(protocol_files, list) or not all(isinstance(s, str) and s.strip() for s in protocol_files):
                errors.append("pack.requirements.protocol_files must be a list of non-empty strings")
            elif len(protocol_files) > 50:
                errors.append("pack.requirements.protocol_files too long (max 50)")

    defaults = pack.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        errors.append("pack.defaults must be an object")
    elif isinstance(defaults, dict):
        ci = defaults.get("ci")
        if ci is not None and not isinstance(ci, dict):
            errors.append("pack.defaults.ci must be an object")
        elif isinstance(ci, dict):
            checks = ci.get("required_checks")
            if checks is not None:
                if not isinstance(checks, list) or not all(isinstance(s, str) and s.strip() for s in checks):
                    errors.append("pack.defaults.ci.required_checks must be a list of non-empty strings")
                elif len(checks) > 50:
                    errors.append("pack.defaults.ci.required_checks too long (max 50)")

    clarifications = pack.get("clarifications")
    if clarifications is not None and not isinstance(clarifications, list):
        errors.append("pack.clarifications must be a list")
    elif isinstance(clarifications, list) and len(clarifications) > 200:
        errors.append("pack.clarifications too long (max 200)")

    return errors


def validate_policy_override_definition(override: Any) -> list[str]:
    """
    Validate a project/repo-local policy override payload (partial policy).
    Returns a list of human-readable error strings; empty means valid.
    """
    errors: list[str] = []
    if override is None:
        return errors
    if not isinstance(override, dict):
        return ["policy_overrides must be a JSON object"]

    # Size + serializability guard.
    try:
        raw = json.dumps(override, ensure_ascii=False)
        if len(raw.encode("utf-8")) > 256_000:
            errors.append("policy_overrides too large (max 256KB)")
    except Exception:
        errors.append("policy_overrides must be JSON-serializable")
        return errors

    allowed_top = {"defaults", "requirements", "clarifications", "enforcement", "constraints"}
    extra_top = [k for k in override.keys() if k not in allowed_top]
    if extra_top:
        errors.append(f"policy_overrides has unsupported top-level keys: {', '.join(sorted(map(str, extra_top)))}")

    enforcement = override.get("enforcement")
    if enforcement is not None and not isinstance(enforcement, dict):
        errors.append("policy_overrides.enforcement must be an object")
    elif isinstance(enforcement, dict):
        mode = enforcement.get("mode")
        if mode is not None and mode not in ("warn", "block"):
            errors.append("policy_overrides.enforcement.mode must be 'warn' or 'block'")
        block_codes = enforcement.get("block_codes")
        if block_codes is not None:
            if not isinstance(block_codes, list):
                errors.append("policy_overrides.enforcement.block_codes must be a list")
            else:
                if len(block_codes) > 200:
                    errors.append("policy_overrides.enforcement.block_codes too long (max 200)")
                bad = [c for c in block_codes if not isinstance(c, (str, int, float))]
                if bad:
                    errors.append("policy_overrides.enforcement.block_codes must contain strings/numbers only")

    requirements = override.get("requirements")
    if requirements is not None and not isinstance(requirements, dict):
        errors.append("policy_overrides.requirements must be an object")
    elif isinstance(requirements, dict):
        step_sections = requirements.get("step_sections")
        if step_sections is not None:
            if not isinstance(step_sections, list) or not all(isinstance(s, str) and s.strip() for s in step_sections):
                errors.append("policy_overrides.requirements.step_sections must be a list of non-empty strings")
            elif len(step_sections) > 30:
                errors.append("policy_overrides.requirements.step_sections too long (max 30)")
        protocol_files = requirements.get("protocol_files")
        if protocol_files is not None:
            if not isinstance(protocol_files, list) or not all(isinstance(s, str) and s.strip() for s in protocol_files):
                errors.append("policy_overrides.requirements.protocol_files must be a list of non-empty strings")
            elif len(protocol_files) > 50:
                errors.append("policy_overrides.requirements.protocol_files too long (max 50)")

    defaults = override.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        errors.append("policy_overrides.defaults must be an object")
    elif isinstance(defaults, dict):
        ci = defaults.get("ci")
        if ci is not None and not isinstance(ci, dict):
            errors.append("policy_overrides.defaults.ci must be an object")
        elif isinstance(ci, dict):
            checks = ci.get("required_checks")
            if checks is not None:
                if not isinstance(checks, list) or not all(isinstance(s, str) and s.strip() for s in checks):
                    errors.append("policy_overrides.defaults.ci.required_checks must be a list of non-empty strings")
                elif len(checks) > 50:
                    errors.append("policy_overrides.defaults.ci.required_checks too long (max 50)")

    clarifications = override.get("clarifications")
    if clarifications is not None and not isinstance(clarifications, list):
        errors.append("policy_overrides.clarifications must be a list")
    elif isinstance(clarifications, list) and len(clarifications) > 200:
        errors.append("policy_overrides.clarifications too long (max 200)")

    return errors


def _policy_block_codes(policy: dict[str, Any]) -> set[str]:
    """
    Determine which finding codes become blocking when project enforcement_mode=block.
    Default is a safe allowlist; can be overridden by policy.enforcement.block_codes.
    """
    enforcement = policy.get("enforcement") if isinstance(policy, dict) else None
    if isinstance(enforcement, dict):
        codes = enforcement.get("block_codes")
        if isinstance(codes, list):
            return {str(c) for c in codes if isinstance(c, (str, int, float))}
    return set(_DEFAULT_BLOCK_CODES)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Deep-merge override into base (dicts merge recursively, other values replace).
    Returns a new dict.
    """
    out: dict[str, Any] = dict(base)
    for key, value in override.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_repo_local_policy(repo_root: Path) -> Optional[dict[str, Any]]:
    """
    Best-effort loader for repo-local override policy.
    Supports JSON always; YAML only if PyYAML is available.
    """
    candidates = [
        repo_root / ".tasksgodzilla" / "policy.json",
        repo_root / ".tasksgodzilla" / "policy.yml",
        repo_root / ".tasksgodzilla" / "policy.yaml",
    ]
    path = next((p for p in candidates if p.exists() and p.is_file()), None)
    if not path:
        return None

    try:
        if path.stat().st_size > 256_000:
            log.warning("policy_repo_local_too_large", extra={"path": str(path), "bytes": path.stat().st_size})
            return None
    except Exception:
        pass

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - IO guard
        log.warning("policy_repo_local_read_failed", extra={"path": str(path), "error": str(exc)})
        return None

    if path.suffix.lower() == ".json":
        try:
            obj = json.loads(content)
        except Exception as exc:
            log.warning("policy_repo_local_json_invalid", extra={"path": str(path), "error": str(exc)})
            return None
        return obj if isinstance(obj, dict) else None

    # YAML optional
    try:
        import yaml  # type: ignore
    except Exception:
        log.info("policy_repo_local_yaml_unavailable", extra={"path": str(path)})
        return None
    try:
        obj = yaml.safe_load(content)
    except Exception as exc:
        log.warning("policy_repo_local_yaml_invalid", extra={"path": str(path), "error": str(exc)})
        return None
    return obj if isinstance(obj, dict) else None


def _policy_required_checks(policy: dict[str, Any]) -> list[str]:
    """
    Extract required CI checks from policy. Supports both `defaults.ci.required_checks`
    and `requirements.required_checks` for forward compatibility.
    """
    out: list[str] = []
    defaults = policy.get("defaults") if isinstance(policy, dict) else None
    if isinstance(defaults, dict):
        ci = defaults.get("ci")
        if isinstance(ci, dict):
            checks = ci.get("required_checks")
            if isinstance(checks, list):
                out.extend([str(c) for c in checks if isinstance(c, (str, int, float))])
    reqs = policy.get("requirements") if isinstance(policy, dict) else None
    if isinstance(reqs, dict):
        checks = reqs.get("required_checks")
        if isinstance(checks, list):
            out.extend([str(c) for c in checks if isinstance(c, (str, int, float))])
    # de-dupe while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for c in out:
        if c in seen:
            continue
        seen.add(c)
        deduped.append(c)
    return deduped


def _is_executable(path: Path) -> bool:
    try:
        return os.access(path, os.X_OK)
    except Exception:
        return False


@dataclass
class EffectivePolicy:
    policy: dict[str, Any]
    effective_hash: str
    pack_key: str
    pack_version: str
    sources: dict[str, Any]


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    scope: str
    suggested_fix: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def asdict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "scope": self.scope,
            "suggested_fix": self.suggested_fix,
            "metadata": self.metadata or {},
        }


class PolicyService:
    def __init__(self, db: BaseDatabase):
        self.db = db

    def resolve_effective_policy(
        self,
        project_id: int,
        *,
        repo_root: Optional[Path] = None,
        include_repo_local: bool = True,
    ) -> EffectivePolicy:
        project = self.db.get_project(project_id)
        pack_key = project.policy_pack_key or DEFAULT_POLICY_PACK_KEY
        if project.policy_pack_version:
            pack = self.db.get_policy_pack(key=pack_key, version=project.policy_pack_version)
        else:
            # When policy_pack_version is not set, treat it as "latest active".
            pack = self.db.get_policy_pack(key=pack_key, version=None)
        pack_version = pack.version
        merged = dict(pack.pack or {})
        sources: dict[str, Any] = {
            "central": {"key": pack.key, "version": pack.version, "id": pack.id},
            "project_overrides_applied": False,
            "repo_local_applied": False,
        }

        if project.policy_overrides and isinstance(project.policy_overrides, dict):
            merged = _deep_merge(merged, _sanitize_policy_override(project.policy_overrides))
            sources["project_overrides_applied"] = True

        repo_local_enabled = bool(project.policy_repo_local_enabled) if project.policy_repo_local_enabled is not None else False
        if include_repo_local and repo_local_enabled:
            resolved_repo_root = repo_root
            if resolved_repo_root is None and project.local_path:
                try:
                    resolved_repo_root = Path(project.local_path).expanduser()
                except Exception:
                    resolved_repo_root = None
            if resolved_repo_root and resolved_repo_root.exists():
                override = _load_repo_local_policy(resolved_repo_root)
                if override:
                    merged = _deep_merge(merged, _sanitize_policy_override(override))
                    sources["repo_local_applied"] = True

        eff_hash = _stable_hash(merged)
        return EffectivePolicy(
            policy=merged,
            effective_hash=eff_hash,
            pack_key=pack.key,
            pack_version=pack.version,
            sources=sources,
        )

    def evaluate_project(self, project_id: int) -> list[Finding]:
        """
        Warnings-first evaluation. This should not block execution.
        """
        project = self.db.get_project(project_id)
        findings: list[Finding] = []
        enforcement_mode = (project.policy_enforcement_mode or "warn").lower()

        effective_policy: Optional[EffectivePolicy] = None
        try:
            effective_policy = self.resolve_effective_policy(project.id)
            self.persist_project_effective_hash(project.id, effective_policy.effective_hash)
        except Exception:
            effective_policy = None

        if not project.policy_pack_key:
            findings.append(
                Finding(
                    code="policy.pack.defaulted",
                    severity="warning",
                    scope="project",
                    message=f"No policy pack selected; defaulting to {DEFAULT_POLICY_PACK_KEY}@{DEFAULT_POLICY_PACK_VERSION}.",
                    suggested_fix="Select a policy pack in the console Policy panel.",
                )
            )
        if project.policy_repo_local_enabled and not project.local_path:
            findings.append(
                Finding(
                    code="policy.repo_local.no_local_path",
                    severity="warning",
                    scope="project",
                    message="Repo-local policy override is enabled but the project has no local_path recorded.",
                    suggested_fix="Run onboarding/setup so the repo is cloned and local_path is recorded, or disable repo-local overrides.",
                )
            )
        # Ensure selected pack exists (best-effort: warn instead of failing hard).
        try:
            key = project.policy_pack_key or DEFAULT_POLICY_PACK_KEY
            ver = project.policy_pack_version or DEFAULT_POLICY_PACK_VERSION
            self.db.get_policy_pack(key=key, version=ver)
        except Exception as exc:
            findings.append(
                Finding(
                    code="policy.pack.missing",
                    severity="warning",
                    scope="project",
                    message=f"Selected policy pack could not be resolved: {exc}",
                    suggested_fix="Choose an existing pack key/version or create/seed the pack.",
                    metadata={"policy_pack_key": project.policy_pack_key, "policy_pack_version": project.policy_pack_version},
                )
            )

        # Validate required CI checks (best-effort, filesystem-only).
        if effective_policy and isinstance(effective_policy.policy, dict):
            required_checks = _policy_required_checks(effective_policy.policy)
            if required_checks:
                repo_root: Optional[Path] = None
                if project.local_path:
                    try:
                        repo_root = Path(project.local_path).expanduser()
                    except Exception:
                        repo_root = None
                if not repo_root or not repo_root.exists():
                    findings.append(
                        Finding(
                            code="policy.ci.required_checks.unverifiable",
                            severity="warning",
                            scope="project",
                            message="Policy defines required checks but the repo is not available locally to verify script paths.",
                            suggested_fix="Run onboarding/setup to clone the repo, or disable required checks in policy overrides.",
                            metadata={"required_checks": required_checks},
                        )
                    )
                else:
                    for check in required_checks:
                        check_path = (repo_root / check) if not Path(check).is_absolute() else Path(check)
                        if not check_path.exists():
                            findings.append(
                                Finding(
                                    code="policy.ci.required_check_missing",
                                    severity="warning",
                                    scope="project",
                                    message=f"Required check script missing: {check}",
                                    suggested_fix="Add the script to the repo or update policy required_checks.",
                                    metadata={"check": check, "repo_root": str(repo_root)},
                                )
                            )
        return self.apply_enforcement_mode(
            findings,
            enforcement_mode,
            policy=effective_policy.policy if effective_policy else None,
        )

    def evaluate_protocol(self, protocol_run_id: int) -> list[Finding]:
        run = self.db.get_protocol_run(protocol_run_id)
        project = self.db.get_project(run.project_id)
        findings: list[Finding] = []
        enforcement_mode = (project.policy_enforcement_mode or "warn").lower()

        # Audit coverage
        if not run.policy_effective_hash:
            findings.append(
                Finding(
                    code="policy.protocol.audit_missing",
                    severity="warning",
                    scope="protocol",
                    message="Protocol run has no recorded policy audit (policy_effective_hash).",
                    suggested_fix="Open the protocol after policy is configured; future runs will record policy hash.",
                )
            )

        # File requirements (best-effort)
        requirements = {}
        effective_policy: Optional[EffectivePolicy] = None
        try:
            effective_policy = self.resolve_effective_policy(project.id)
            requirements = (effective_policy.policy.get("requirements") if isinstance(effective_policy.policy, dict) else {}) or {}
        except Exception:
            requirements = {}

        req_files = requirements.get("protocol_files") if isinstance(requirements, dict) else None
        if req_files and isinstance(req_files, list):
            proto_root = None
            if run.protocol_root:
                try:
                    proto_root = Path(run.protocol_root).expanduser()
                except Exception:
                    proto_root = None
            for fname in req_files:
                if not proto_root:
                    break
                try:
                    if not (proto_root / str(fname)).exists():
                        findings.append(
                            Finding(
                                code="policy.protocol.missing_file",
                                severity="warning",
                                scope="protocol",
                                message=f"Missing required protocol file: {fname}",
                                suggested_fix="Regenerate protocol artifacts or add the missing file.",
                                metadata={"protocol_root": str(proto_root), "file": str(fname)},
                            )
                        )
                except Exception:
                    continue

        # Validate required checks at protocol scope (prefers worktree, falls back to project.local_path).
        if effective_policy and isinstance(effective_policy.policy, dict):
            required_checks = _policy_required_checks(effective_policy.policy)
            if required_checks:
                workspace_root: Optional[Path] = None
                for candidate in [run.worktree_path, project.local_path]:
                    if not candidate:
                        continue
                    try:
                        p = Path(candidate).expanduser()
                    except Exception:
                        continue
                    if p.exists():
                        workspace_root = p
                        break
                if workspace_root:
                    for check in required_checks:
                        check_path = (workspace_root / check) if not Path(check).is_absolute() else Path(check)
                        if not check_path.exists():
                            findings.append(
                                Finding(
                                    code="policy.ci.required_check_missing",
                                    severity="warning",
                                    scope="protocol",
                                    message=f"Required check script missing in workspace: {check}",
                                    suggested_fix="Add the script to the repo/worktree or update policy required_checks.",
                                    metadata={"check": check, "workspace_root": str(workspace_root), "protocol_run_id": run.id},
                                )
                            )
                else:
                    findings.append(
                        Finding(
                            code="policy.ci.required_checks.unverifiable",
                            severity="warning",
                            scope="protocol",
                            message="Policy defines required checks but no workspace path is available to verify script paths.",
                            suggested_fix="Ensure protocol worktree_path is recorded or project.local_path exists.",
                            metadata={"required_checks": required_checks, "protocol_run_id": run.id},
                        )
                    )

        return self.apply_enforcement_mode(findings, enforcement_mode, policy=effective_policy.policy if effective_policy else None)

    def evaluate_step(self, step_run_id: int) -> list[Finding]:
        step = self.db.get_step_run(step_run_id)
        run = self.db.get_protocol_run(step.protocol_run_id)
        project = self.db.get_project(run.project_id)
        findings: list[Finding] = []
        enforcement_mode = (project.policy_enforcement_mode or "warn").lower()

        requirements: dict[str, Any] = {}
        effective_policy: Optional[EffectivePolicy] = None
        try:
            effective_policy = self.resolve_effective_policy(project.id)
            requirements = (effective_policy.policy.get("requirements") if isinstance(effective_policy.policy, dict) else {}) or {}
        except Exception:
            requirements = {}

        required_sections = requirements.get("step_sections") if isinstance(requirements, dict) else None
        if required_sections and not isinstance(required_sections, list):
            required_sections = None

        # Best-effort locate step file.
        proto_root = None
        if run.protocol_root:
            try:
                proto_root = Path(run.protocol_root).expanduser()
            except Exception:
                proto_root = None
        if proto_root and required_sections:
            candidates = [
                proto_root / f"{step.step_name}.md",
                proto_root / step.step_name,
            ]
            step_path = next((p for p in candidates if p.exists() and p.is_file()), None)
            if not step_path:
                findings.append(
                    Finding(
                        code="policy.step.file_missing",
                        severity="warning",
                        scope="step",
                        message=f"Step file not found for step {step.step_name}.",
                        suggested_fix="Ensure the step markdown file exists under the protocol directory.",
                        metadata={"protocol_root": str(proto_root)},
                    )
                )
                # keep going; checks can still be evaluated without the step file
            try:
                content = step_path.read_text(encoding="utf-8", errors="replace") if step_path else ""
            except Exception:
                content = ""
            if content:
                lower = content.lower()
                for section in required_sections:
                    if not isinstance(section, str) or not section.strip():
                        continue
                    needle = section.strip().lower()
                    if f"# {needle}" in lower or f"## {needle}" in lower or f"### {needle}" in lower:
                        continue
                    findings.append(
                        Finding(
                            code="policy.step.missing_section",
                            severity="warning",
                            scope="step",
                            message=f"Missing required step section: {section}",
                            suggested_fix=f"Add a '{section}' heading to the step file.",
                            metadata={"step_file": str(step_path) if step_path else None, "section": section},
                        )
                    )

        # Step-level required checks (use worktree_path first for accuracy).
        if effective_policy and isinstance(effective_policy.policy, dict):
            required_checks = _policy_required_checks(effective_policy.policy)
            if required_checks:
                workspace_root: Optional[Path] = None
                for candidate in [run.worktree_path, project.local_path]:
                    if not candidate:
                        continue
                    try:
                        p = Path(candidate).expanduser()
                    except Exception:
                        continue
                    if p.exists():
                        workspace_root = p
                        break
                if not workspace_root:
                    findings.append(
                        Finding(
                            code="policy.ci.required_checks.unverifiable",
                            severity="warning",
                            scope="step",
                            message="Policy defines required checks but no workspace path is available to verify script paths.",
                            suggested_fix="Ensure protocol worktree_path is recorded or project.local_path exists.",
                            metadata={"required_checks": required_checks, "step_run_id": step.id},
                        )
                    )
                else:
                    for check in required_checks:
                        check_path = (workspace_root / check) if not Path(check).is_absolute() else Path(check)
                        if not check_path.exists():
                            findings.append(
                                Finding(
                                    code="policy.ci.required_check_missing",
                                    severity="warning",
                                    scope="step",
                                    message=f"Required check script missing in workspace: {check}",
                                    suggested_fix="Add the script to the repo/worktree or update policy required_checks.",
                                    metadata={"check": check, "workspace_root": str(workspace_root), "step_run_id": step.id},
                                )
                            )
                            continue
                        # If it looks like a script file, encourage executable bit (best-effort).
                        if check_path.is_file() and (str(check_path).endswith(".sh") or str(check_path).endswith(".py")):
                            if not _is_executable(check_path):
                                findings.append(
                                    Finding(
                                        code="policy.ci.required_check_not_executable",
                                        severity="warning",
                                        scope="step",
                                        message=f"Required check script is not executable: {check}",
                                        suggested_fix=f"Run `chmod +x {check}` (or invoke via an interpreter) and ensure CI can execute it.",
                                        metadata={"check": check, "path": str(check_path), "step_run_id": step.id},
                                    )
                                )

        return self.apply_enforcement_mode(findings, enforcement_mode, policy=effective_policy.policy if effective_policy else None)

    @staticmethod
    def apply_enforcement_mode(findings: list[Finding], enforcement_mode: str, *, policy: Optional[dict[str, Any]] = None) -> list[Finding]:
        """
        Translate finding severities based on project enforcement mode.
        This does not change workflow behavior yet; it only affects reporting.
        """
        mode = (enforcement_mode or "warn").lower()
        if mode != "block":
            return findings
        block_codes = _policy_block_codes(policy or {})
        escalated: list[Finding] = []
        for f in findings:
            if f.code in block_codes and f.severity in ("warning", "error"):
                escalated.append(
                    Finding(
                        code=f.code,
                        severity="block",
                        message=f.message,
                        scope=f.scope,
                        suggested_fix=f.suggested_fix,
                        metadata={**(f.metadata or {}), "enforcement_mode": "block"},
                    )
                )
            else:
                escalated.append(f)
        return escalated

    @staticmethod
    def has_blocking_findings(findings: list[Finding]) -> bool:
        return any(f.severity == "block" for f in findings)

    def update_project_policy_effective_hash(self, project_id: int, effective_hash: str) -> None:
        try:
            self.db.update_project_policy(project_id, policy_effective_hash=effective_hash)
        except Exception:
            return

    def update_protocol_policy_audit(
        self,
        protocol_run_id: int,
        *,
        pack_key: str,
        pack_version: str,
        effective_hash: str,
        policy: Optional[dict[str, Any]] = None,
    ) -> None:
        try:
            self.db.update_protocol_policy_audit(
                protocol_run_id,
                policy_pack_key=pack_key,
                policy_pack_version=pack_version,
                policy_effective_hash=effective_hash,
                policy_effective_json=policy,
            )
        except Exception:
            return

    # Backward-compatible aliases (kept as assignments so they don't violate
    # service method naming conventions enforced by tests).
    persist_project_effective_hash = update_project_policy_effective_hash
    audit_protocol_effective_policy = update_protocol_policy_audit
