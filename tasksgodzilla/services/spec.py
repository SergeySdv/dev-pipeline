from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from tasksgodzilla.logging import get_logger
from tasksgodzilla.spec import (
    PROTOCOL_SPEC_KEY,
    build_spec_from_codemachine_config,
    build_spec_from_protocol_files,
    create_steps_from_spec,
    get_step_spec,
    update_spec_meta,
    validate_protocol_spec,
)
from tasksgodzilla.storage import BaseDatabase

log = get_logger(__name__)


@dataclass
class SpecService:
    """Facade for building and validating ProtocolSpec / StepSpec.

    This centralizes how specs are attached to `ProtocolRun.template_config`
    while delegating to the existing helpers in `tasksgodzilla.spec`.
    """

    db: BaseDatabase

    def build_from_protocol_files(self, protocol_run_id: int, protocol_root: Path) -> Dict[str, Any]:
        """Create a spec from protocol step files and persist it on the run."""
        run = self.db.get_protocol_run(protocol_run_id)
        spec = build_spec_from_protocol_files(protocol_root)
        template_config = dict(run.template_config or {})
        template_config[PROTOCOL_SPEC_KEY] = spec
        self.db.update_protocol_template(protocol_run_id, template_config, run.template_source)
        log.info(
            "spec_built_from_protocol_files",
            extra={"protocol_run_id": protocol_run_id, "protocol_root": str(protocol_root)},
        )
        return spec

    def build_from_codemachine_config(self, protocol_run_id: int, cfg: Any) -> Dict[str, Any]:
        """Create a spec from a CodeMachine config and persist it on the run."""
        run = self.db.get_protocol_run(protocol_run_id)
        spec = build_spec_from_codemachine_config(cfg)
        template_config = dict(run.template_config or {})
        template_config[PROTOCOL_SPEC_KEY] = spec
        self.db.update_protocol_template(protocol_run_id, template_config, run.template_source)
        log.info(
            "spec_built_from_codemachine",
            extra={"protocol_run_id": protocol_run_id, "has_placeholders": bool(getattr(cfg, "placeholders", None))},
        )
        return spec

    def validate_and_update_meta(
        self,
        protocol_run_id: int,
        protocol_root: Path,
        workspace_root: Optional[Path] = None,
    ) -> List[str]:
        """Validate the spec associated with a protocol run and update meta fields."""
        run = self.db.get_protocol_run(protocol_run_id)
        template_config = dict(run.template_config or {})
        spec = template_config.get(PROTOCOL_SPEC_KEY) or {}

        if workspace_root is None:
            if protocol_root.parent.name == ".protocols":
                workspace_root = protocol_root.parent.parent
            else:
                workspace_root = protocol_root.parent

        errors = validate_protocol_spec(protocol_root, spec, workspace=workspace_root)
        status = "valid" if not errors else "invalid"
        update_spec_meta(self.db, protocol_run_id, template_config, run.template_source, status=status, errors=errors or None)
        log.info(
            "spec_validated",
            extra={"protocol_run_id": protocol_run_id, "status": status, "error_count": len(errors)},
        )
        return errors

    def ensure_step_runs(self, protocol_run_id: int) -> int:
        """Create StepRun rows from the current spec, skipping already-present steps."""
        run = self.db.get_protocol_run(protocol_run_id)
        template_config = dict(run.template_config or {})
        spec = template_config.get(PROTOCOL_SPEC_KEY)
        if not spec:
            return 0
        existing = {s.step_name for s in self.db.list_step_runs(protocol_run_id)}
        created = create_steps_from_spec(protocol_run_id, spec, self.db, existing_names=existing)
        log.info("spec_step_runs_synced", extra={"protocol_run_id": protocol_run_id, "created": created})
        return created

    def get_step_spec(self, protocol_run_id: int, step_name: str) -> Optional[Dict[str, Any]]:
        """Look up a single step spec entry by name."""
        run = self.db.get_protocol_run(protocol_run_id)
        return get_step_spec(run.template_config, step_name)
