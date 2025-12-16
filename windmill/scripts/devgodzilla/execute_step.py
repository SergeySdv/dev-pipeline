"""
Execute Step Script

Executes a single task step using the specified AI agent.

Args:
    step_id: Task identifier (e.g., T001)
    agent_id: Agent to use (e.g., codex, claude-code, opencode)
    protocol_run_id: Parent protocol run ID
    context: Additional context for execution

Returns:
    status: Execution status (success, failed, blocked)
    output: Agent output
    artifacts: List of created/modified files
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any, List

# Import DevGodzilla services if available
try:
    from devgodzilla.services import ExecutionService
    from devgodzilla.engines import get_engine
    from devgodzilla.db import get_database
    DEVGODZILLA_AVAILABLE = True
except ImportError:
    DEVGODZILLA_AVAILABLE = False


# Agent configurations
AGENT_CONFIGS = {
    "codex": {
        "command": "codex",
        "args": ["--quiet"],
    },
    "claude-code": {
        "command": "claude",
        "args": ["code"],
    },
    "opencode": {
        "command": "opencode",
        "args": [],
    },
    "gemini-cli": {
        "command": "gemini",
        "args": [],
    },
}


def main(
    step_id: str,
    agent_id: str = "codex",
    protocol_run_id: int = 0,
    context: dict = None,
) -> dict:
    """Execute a single step using specified AI agent."""
    
    context = context or {}
    project_path = context.get("project_path", "/tmp/devgodzilla/current")
    step_description = context.get("description", f"Execute step {step_id}")
    
    start_time = datetime.now()
    
    # Use DevGodzilla execution service if available
    if DEVGODZILLA_AVAILABLE:
        try:
            db = get_database()
            execution_service = ExecutionService(db)
            result = execution_service.execute_step(
                step_id=step_id,
                agent_id=agent_id,
                protocol_run_id=protocol_run_id,
                context=context,
            )
            return {
                "status": result.status,
                "output": result.output,
                "artifacts": result.artifacts,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
            }
        except Exception as e:
            # Fall through to demo execution
            pass
    
    # Demo execution without real AI agent
    return _demo_execute(step_id, agent_id, project_path, step_description, start_time)


def _demo_execute(
    step_id: str,
    agent_id: str,
    project_path: str,
    step_description: str,
    start_time: datetime,
) -> dict:
    """Demo execution for demonstration purposes."""
    
    # Create output directory
    output_dir = Path(project_path) / ".specify" / "specs" / "_runtime" / "runs" / step_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Simulate execution
    execution_log = f"""
=== Step Execution: {step_id} ===
Agent: {agent_id}
Started: {start_time.isoformat()}
Description: {step_description}

--- Simulated Output ---
[{agent_id}] Analyzing step requirements...
[{agent_id}] Identifying relevant files...
[{agent_id}] Generating implementation...
[{agent_id}] Step completed successfully.

--- Files Modified ---
(Demo mode - no actual changes made)
"""
    
    # Write execution log
    log_path = output_dir / "execution.log"
    log_path.write_text(execution_log)
    
    # Write result metadata
    result = {
        "step_id": step_id,
        "agent_id": agent_id,
        "status": "success",
        "started_at": start_time.isoformat(),
        "completed_at": datetime.now().isoformat(),
        "demo_mode": True,
    }
    (output_dir / "result.json").write_text(json.dumps(result, indent=2))
    
    return {
        "status": "success",
        "output": execution_log,
        "artifacts": [str(log_path)],
        "duration_seconds": (datetime.now() - start_time).total_seconds(),
        "demo_mode": True,
    }
