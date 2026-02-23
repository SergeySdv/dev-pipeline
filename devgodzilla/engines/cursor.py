"""
DevGodzilla Cursor IDE Engine

Adapter for Cursor IDE integration.
Generates command files for Cursor's AI-assisted coding features.
"""

import os
from pathlib import Path
from typing import List, Optional

from devgodzilla.engines.interface import (
    EngineKind,
    EngineMetadata,
    EngineRequest,
    EngineResult,
    SandboxMode,
)
from devgodzilla.engines.ide import (
    IDECommand,
    IDEEngine,
)
from devgodzilla.engines.registry import register_engine
from devgodzilla.logging import get_logger

logger = get_logger(__name__)


class CursorEngine(IDEEngine):
    """
    Engine adapter for Cursor IDE.
    
    Cursor is an AI-powered code editor built on VS Code.
    This adapter generates command files that can be consumed
    by the DevGodzilla Cursor extension.
    
    Features:
    - Generates .cursorrules for project-specific AI behavior
    - Creates command files for automated editing
    - Supports Composer and Chat modes
    
    Example:
        engine = CursorEngine()
        result = engine.execute(request)
    """

    def __init__(
        self,
        *,
        command_dir: Optional[Path] = None,
        result_timeout: int = 300,
        default_model: Optional[str] = None,
        use_composer: bool = True,
    ) -> None:
        """
        Initialize Cursor engine.
        
        Args:
            command_dir: Directory for command files
            result_timeout: Seconds to wait for Cursor result
            default_model: Default model (cursor-small, claude-3.5-sonnet, etc.)
            use_composer: Whether to use Composer mode (multi-file editing)
        """
        super().__init__(
            command_dir=command_dir,
            result_timeout=result_timeout,
        )
        self._default_model = default_model or os.environ.get(
            "DEVGODZILLA_CURSOR_MODEL", "claude-3.5-sonnet"
        )
        self._use_composer = use_composer

    @property
    def metadata(self) -> EngineMetadata:
        return EngineMetadata(
            id="cursor",
            display_name="Cursor IDE",
            kind=EngineKind.IDE,
            default_model=self._default_model,
            description="Cursor IDE AI assistant for code generation and editing",
            capabilities=[
                "plan",
                "execute",
                "qa",
                "multi-file-edit",
                "codebase-indexing",
            ],
        )

    def _get_command_dir(self, req: EngineRequest) -> Path:
        """Get command directory, preferring workspace .devgodzilla dir."""
        if self._command_dir:
            return self._command_dir
        
        workspace_dir = Path(req.working_dir)
        command_dir = workspace_dir / ".devgodzilla" / "cursor"
        command_dir.mkdir(parents=True, exist_ok=True)
        return command_dir

    def _get_command_file_path(self, req: EngineRequest) -> Path:
        """Get command file path in workspace .devgodzilla directory."""
        command_dir = self._get_command_dir(req)
        filename = f"cmd-{req.step_run_id}.json"
        return command_dir / filename

    def _infer_command_type(self, sandbox: SandboxMode) -> str:
        """Infer command type from sandbox mode."""
        if sandbox == SandboxMode.FULL_ACCESS:
            return "plan"
        elif sandbox == SandboxMode.READ_ONLY:
            return "review"
        else:
            return "edit"

    def _generate_commands(
        self,
        req: EngineRequest,
        sandbox: SandboxMode,
    ) -> List[IDECommand]:
        """
        Generate Cursor commands from the request.
        
        Creates commands based on sandbox mode:
        - FULL_ACCESS: Planning/analysis commands
        - WORKSPACE_WRITE: Edit/create commands
        - READ_ONLY: Review/audit commands
        """
        commands: List[IDECommand] = []
        prompt_text = self.get_prompt_text(req)
        command_type = self._infer_command_type(sandbox)
        
        # Primary command with the full prompt
        primary_command = IDECommand(
            command_type=command_type,
            target=req.working_dir,
            instruction=prompt_text,
            context={
                "mode": "composer" if self._use_composer else "chat",
                "project_id": req.project_id,
                "protocol_run_id": req.protocol_run_id,
            },
            metadata={
                "model": req.model or self._default_model,
                "files": req.prompt_files,
                "extra": req.extra,
            },
        )
        commands.append(primary_command)
        
        # Add follow-up commands based on extra parameters
        follow_ups = req.extra.get("follow_up_commands", [])
        for follow_up in follow_ups:
            if isinstance(follow_up, dict):
                commands.append(IDECommand(
                    command_type=follow_up.get("type", "edit"),
                    target=follow_up.get("target", req.working_dir),
                    instruction=follow_up.get("instruction", ""),
                    context=follow_up.get("context", {}),
                    metadata=follow_up.get("metadata", {}),
                ))
        
        return commands

    def _parse_response(self, result_data) -> EngineResult:
        """
        Parse Cursor extension result.
        
        Expected format:
        {
            "success": bool,
            "changes": [{"file": str, "action": str, "content": str}],
            "output": str,
            "error": str | null
        }
        """
        if result_data is None:
            return EngineResult(
                success=False,
                error="Timeout waiting for Cursor response",
                metadata={"timeout": True},
            )
        
        success = result_data.get("success", False)
        changes = result_data.get("changes", [])
        output = result_data.get("output", "")
        error = result_data.get("error")
        
        # Build stdout from changes summary
        if changes:
            change_summary = "\n".join(
                f"- {c.get('action', 'change')}: {c.get('file', 'unknown')}"
                for c in changes
            )
            stdout = f"Changes made:\n{change_summary}\n\n{output}"
        else:
            stdout = output
        
        return EngineResult(
            success=success,
            stdout=stdout,
            stderr="",
            error=error,
            metadata={
                "changes": changes,
                "change_count": len(changes),
            },
        )

    def sync_config(self, additional_agents: Optional[List[dict]] = None) -> None:
        """
        Generate .cursorrules file for the project.
        
        Creates or updates the .cursorrules file with DevGodzilla
        configuration and coding guidelines.
        """
        # This would typically be called with project-specific rules
        # For now, we just log that sync was requested
        logger.info(
            "cursor_sync_config",
            extra={"additional_agents": len(additional_agents) if additional_agents else 0},
        )

    def check_availability(self) -> bool:
        """
        Check if Cursor integration is available.
        
        Checks for Cursor installation or .cursor directory.
        """
        try:
            # Check for common Cursor indicators
            home = Path.home()
            cursor_config = home / ".cursor"
            
            if cursor_config.exists():
                return True
            
            # Check for Cursor in common install locations
            common_paths = [
                "/Applications/Cursor.app",  # macOS
                Path(home) / ".local" / "share" / "cursor",  # Linux
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "cursor",  # Windows
            ]
            
            for path in common_paths:
                if Path(path).exists():
                    return True
            
            # If command dir is writable, we can still generate commands
            return super().check_availability()
            
        except Exception:
            return False


def register_cursor_engine(*, default: bool = False) -> CursorEngine:
    """
    Register CursorEngine in the global registry.
    
    Returns the registered engine instance.
    """
    engine = CursorEngine()
    register_engine(engine, default=default)
    return engine
