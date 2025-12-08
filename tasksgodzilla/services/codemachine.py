from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tasksgodzilla.logging import get_logger
from tasksgodzilla.storage import BaseDatabase
from tasksgodzilla.workers import codemachine_worker

log = get_logger(__name__)


@dataclass
class CodeMachineService:
    """Facade for CodeMachine workspace import and management.
    
    This wraps the existing codemachine_worker implementation to provide a
    stable service API for CodeMachine operations.
    """
    
    db: BaseDatabase
    
    def import_workspace(
        self,
        project_id: int,
        protocol_run_id: int,
        workspace_path: str,
        *,
        job_id: Optional[str] = None
    ) -> None:
        """Import a CodeMachine workspace and create protocol spec.
        
        Delegates to the existing worker implementation while providing a
        service-level API for callers.
        """
        log.info(
            "codemachine_import_workspace",
            extra={
                "project_id": project_id,
                "protocol_run_id": protocol_run_id,
                "workspace_path": workspace_path,
                "job_id": job_id,
            }
        )
        codemachine_worker.import_codemachine_workspace(
            project_id,
            protocol_run_id,
            workspace_path,
            self.db,
            job_id=job_id
        )
