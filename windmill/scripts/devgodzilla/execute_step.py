"""
Execute Step Script

Executes a single task step using the specified AI agent via ExecutionService.

Args:
    step_id: Task identifier (DB ID string or int)
    agent_id: Agent to use (e.g., opencode, claude-code)
    protocol_run_id: Parent protocol run ID
    context: Additional context

Returns:
    status: Execution status
    output: Agent output
"""

import os
from datetime import datetime

try:
    from devgodzilla.config import Config
    from devgodzilla.services.base import ServiceContext
    from devgodzilla.db import get_database
    from devgodzilla.services import ExecutionService
    DEVGODZILLA_AVAILABLE = True
except ImportError:
    DEVGODZILLA_AVAILABLE = False


def main(
    step_id: str | int,
    agent_id: str = "opencode",
    protocol_run_id: int = 0,
    context: dict = None,
) -> dict:
    """Execute a single step using specified AI agent."""
    
    if not DEVGODZILLA_AVAILABLE:
        return {"error": "DevGodzilla services not available"}
    
    start_time = datetime.now()
    context = context or {}
    
    db = get_database()
    config = Config()
    service_context = ServiceContext(config=config)
    execution_service = ExecutionService(service_context, db=db)
    
    try:
        # Step ID comes as string from Windmill sometimes
        sid = int(step_id)
        
        result = execution_service.execute_step(
            step_run_id=sid,
            agent_id=agent_id,
            job_id=context.get("job_id"),
        )
        
        return {
            "status": "success" if result.success else "failed",
            "executed_by": result.engine_id,
            "output": result.stdout,
            "error": result.error,
            "duration_seconds": result.duration_seconds,
            "artifacts": [str(p) for p in result.outputs_written.values()],
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
        }
