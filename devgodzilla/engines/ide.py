"""
DevGodzilla IDE Engine Adapter

Base class for IDE-integrated AI coding agents.
Generates command files for IDE-based execution.
"""

import json
import tempfile
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from devgodzilla.engines.interface import (
    Engine,
    EngineKind,
    EngineMetadata,
    EngineRequest,
    EngineResult,
    SandboxMode,
)
from devgodzilla.logging import get_logger

logger = get_logger(__name__)


@dataclass
class IDECommand:
    """
    A command to be executed by an IDE agent.
    
    IDE agents typically read commands from a file and execute
    them within the IDE context.
    """
    command_type: str  # e.g., "edit", "create", "refactor", "review"
    target: str  # File path or scope
    instruction: str  # The main instruction
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IDECommandFile:
    """
    A command file for IDE agent execution.
    
    Contains a list of commands and metadata about the execution request.
    """
    commands: List[IDECommand]
    project_id: int
    protocol_run_id: int
    step_run_id: int
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    sandbox: str = "workspace-write"
    model: Optional[str] = None
    timeout_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "commands": [
                {
                    "command_type": cmd.command_type,
                    "target": cmd.target,
                    "instruction": cmd.instruction,
                    "context": cmd.context,
                    "metadata": cmd.metadata,
                }
                for cmd in self.commands
            ],
            "project_id": self.project_id,
            "protocol_run_id": self.protocol_run_id,
            "step_run_id": self.step_run_id,
            "created_at": self.created_at,
            "sandbox": self.sandbox,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class IDEEngine(Engine):
    """
    Base class for IDE-integrated AI coding agents.
    
    IDE engines generate command files that are picked up and executed
    by IDE extensions or integrations. This is useful for agents like
    Cursor, GitHub Copilot, and other IDE-native tools.
    
    Subclasses should implement:
    - metadata property
    - _generate_commands() to create IDECommand objects
    - _get_command_file_path() to specify where commands are written
    - _wait_for_result() to wait for IDE execution completion
    
    Example:
        class CursorEngine(IDEEngine):
            @property
            def metadata(self) -> EngineMetadata:
                return EngineMetadata(
                    id="cursor",
                    display_name="Cursor IDE",
                    kind=EngineKind.IDE,
                )
            
            def _generate_commands(self, req: EngineRequest, sandbox: SandboxMode) -> List[IDECommand]:
                return [IDECommand(
                    command_type="edit",
                    target="src/main.py",
                    instruction=self.get_prompt_text(req),
                )]
    """

    def __init__(
        self,
        *,
        command_dir: Optional[Path] = None,
        result_timeout: int = 300,
    ) -> None:
        """
        Initialize IDE engine.
        
        Args:
            command_dir: Directory for command files (default: temp dir)
            result_timeout: Seconds to wait for IDE result
        """
        self._command_dir = command_dir
        self._result_timeout = result_timeout

    @property
    def metadata(self) -> EngineMetadata:
        """Override in subclass."""
        raise NotImplementedError

    @abstractmethod
    def _generate_commands(
        self,
        req: EngineRequest,
        sandbox: SandboxMode,
    ) -> List[IDECommand]:
        """
        Generate IDE commands from the request.
        
        Override in subclass to define IDE-specific command structure.
        """
        ...

    def _get_command_file_path(self, req: EngineRequest) -> Path:
        """
        Get the path where the command file should be written.
        
        Override in subclass for IDE-specific paths.
        """
        if self._command_dir:
            base_dir = self._command_dir
        else:
            base_dir = Path(tempfile.gettempdir()) / "devgodzilla-ide-commands"
        
        base_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"cmd-{req.project_id}-{req.protocol_run_id}-{req.step_run_id}.json"
        return base_dir / filename

    def _get_result_file_path(self, command_file: Path) -> Path:
        """
        Get the path where the IDE will write results.
        
        Default: same as command file with .result extension.
        """
        return command_file.with_suffix(".result.json")

    def _write_command_file(self, command_file: IDECommandFile, path: Path) -> None:
        """Write command file to disk."""
        path.write_text(command_file.to_json(), encoding="utf-8")
        logger.info(
            "ide_command_file_written",
            extra={
                "path": str(path),
                "command_count": len(command_file.commands),
            },
        )

    def _wait_for_result(
        self,
        result_path: Path,
        timeout: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for IDE to write result file.
        
        Override in subclass for IDE-specific result handling.
        """
        import time
        
        start = time.time()
        while time.time() - start < timeout:
            if result_path.exists():
                try:
                    content = result_path.read_text(encoding="utf-8")
                    return json.loads(content)
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(
                        "ide_result_parse_error",
                        extra={"path": str(result_path), "error": str(e)},
                    )
            time.sleep(1)
        
        return None

    def _parse_result(self, result_data: Optional[Dict[str, Any]]) -> EngineResult:
        """
        Parse IDE result data into EngineResult.
        
        Override in subclass for IDE-specific result formats.
        """
        if result_data is None:
            return EngineResult(
                success=False,
                error="Timeout waiting for IDE result",
                metadata={"timeout": True},
            )
        
        return EngineResult(
            success=result_data.get("success", False),
            stdout=result_data.get("stdout", ""),
            stderr=result_data.get("stderr", ""),
            error=result_data.get("error"),
            metadata=result_data.get("metadata", {}),
        )

    def _cleanup_files(self, command_path: Path, result_path: Path) -> None:
        """Clean up command and result files."""
        for path in [command_path, result_path]:
            try:
                if path.exists():
                    path.unlink()
            except OSError as e:
                logger.debug(
                    "ide_cleanup_failed",
                    extra={"path": str(path), "error": str(e)},
                )

    def _execute_via_ide(
        self,
        req: EngineRequest,
        sandbox: SandboxMode,
    ) -> EngineResult:
        """
        Execute request by generating command file and waiting for IDE.
        """
        # Generate commands
        commands = self._generate_commands(req, sandbox)
        
        if not commands:
            return EngineResult(
                success=False,
                error="No commands generated for IDE execution",
            )
        
        # Create command file
        command_file = IDECommandFile(
            commands=commands,
            project_id=req.project_id,
            protocol_run_id=req.protocol_run_id,
            step_run_id=req.step_run_id,
            sandbox=sandbox.value,
            model=req.model or self.metadata.default_model,
            timeout_seconds=req.timeout or self._result_timeout,
        )
        
        # Write command file
        command_path = self._get_command_file_path(req)
        self._write_command_file(command_file, command_path)
        
        # Wait for result
        result_path = self._get_result_file_path(command_path)
        timeout = req.timeout or self._result_timeout
        
        logger.info(
            "ide_waiting_for_result",
            extra={
                "engine_id": self.metadata.id,
                "command_path": str(command_path),
                "result_path": str(result_path),
                "timeout": timeout,
            },
        )
        
        result_data = self._wait_for_result(result_path, timeout)
        result = self._parse_result(result_data)
        
        # Add engine metadata
        result.metadata["engine_id"] = self.metadata.id
        result.metadata["sandbox"] = sandbox.value
        result.metadata["command_file"] = str(command_path)
        
        # Cleanup
        self._cleanup_files(command_path, result_path)
        
        return result

    def plan(self, req: EngineRequest) -> EngineResult:
        """Execute planning with full access."""
        return self._execute_via_ide(req, SandboxMode.FULL_ACCESS)

    def execute(self, req: EngineRequest) -> EngineResult:
        """Execute coding with workspace-write sandbox."""
        return self._execute_via_ide(req, SandboxMode.WORKSPACE_WRITE)

    def qa(self, req: EngineRequest) -> EngineResult:
        """Execute QA in read-only mode."""
        return self._execute_via_ide(req, SandboxMode.READ_ONLY)

    def check_availability(self) -> bool:
        """
        Check if the IDE integration is available.
        
        Default implementation checks if command directory is writable.
        Override in subclass for specific checks.
        """
        try:
            if self._command_dir:
                test_file = self._command_dir / ".devgodzilla_test"
                test_file.touch()
                test_file.unlink()
            return True
        except OSError:
            return False
