"""Tests for IDEEngine base class and adapters."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from devgodzilla.engines.ide import (
    IDECommand,
    IDECommandFile,
    IDEEngine,
)
from devgodzilla.engines.interface import (
    EngineKind,
    EngineMetadata,
    EngineRequest,
    EngineResult,
    SandboxMode,
)


class ConcreteIDEEngine(IDEEngine):
    """Concrete implementation of IDEEngine for testing."""

    @property
    def metadata(self) -> EngineMetadata:
        return EngineMetadata(
            id="test-ide",
            display_name="Test IDE",
            kind=EngineKind.IDE,
            default_model="test-model",
            description="Test IDE engine for unit tests",
            capabilities=["plan", "execute", "qa"],
        )

    def _generate_commands(self, req: EngineRequest, sandbox: SandboxMode):
        return [
            IDECommand(
                command_type="edit",
                target=req.working_dir,
                instruction=self.get_prompt_text(req),
            )
        ]


class TestIDECommand:
    """Tests for IDECommand dataclass."""

    def test_create_ide_command(self):
        """Test IDE command creation."""
        cmd = IDECommand(
            command_type="edit",
            target="src/main.py",
            instruction="Add type hints",
        )
        assert cmd.command_type == "edit"
        assert cmd.target == "src/main.py"
        assert cmd.instruction == "Add type hints"
        assert cmd.context == {}
        assert cmd.metadata == {}

    def test_ide_command_with_context(self):
        """Test IDE command with context and metadata."""
        cmd = IDECommand(
            command_type="refactor",
            target="src/",
            instruction="Refactor module",
            context={"mode": "composer", "project_id": 1},
            metadata={"priority": "high"},
        )
        assert cmd.context["mode"] == "composer"
        assert cmd.metadata["priority"] == "high"


class TestIDECommandFile:
    """Tests for IDECommandFile."""

    def test_create_command_file(self):
        """Test command file creation."""
        commands = [
            IDECommand(
                command_type="create",
                target="test.py",
                instruction="Create test file",
            )
        ]
        cmd_file = IDECommandFile(
            commands=commands,
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
        )
        assert cmd_file.project_id == 1
        assert cmd_file.protocol_run_id == 2
        assert cmd_file.step_run_id == 3
        assert len(cmd_file.commands) == 1
        assert cmd_file.sandbox == "workspace-write"

    def test_command_file_to_dict(self):
        """Test command file serialization."""
        commands = [
            IDECommand(
                command_type="edit",
                target="main.py",
                instruction="Fix bug",
                context={"key": "value"},
                metadata={"meta": "data"},
            )
        ]
        cmd_file = IDECommandFile(
            commands=commands,
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            sandbox="read-only",
            model="test-model",
            timeout_seconds=60,
            metadata={"extra": "info"},
        )
        data = cmd_file.to_dict()

        assert data["project_id"] == 1
        assert data["protocol_run_id"] == 2
        assert data["step_run_id"] == 3
        assert data["sandbox"] == "read-only"
        assert data["model"] == "test-model"
        assert data["timeout_seconds"] == 60
        assert len(data["commands"]) == 1
        assert data["commands"][0]["command_type"] == "edit"
        assert data["commands"][0]["target"] == "main.py"
        assert data["commands"][0]["context"] == {"key": "value"}
        assert data["metadata"] == {"extra": "info"}

    def test_command_file_to_json(self):
        """Test command file JSON serialization."""
        commands = [
            IDECommand(
                command_type="review",
                target=".",
                instruction="Review code",
            )
        ]
        cmd_file = IDECommandFile(
            commands=commands,
            project_id=0,
            protocol_run_id=0,
            step_run_id=1,
        )
        json_str = cmd_file.to_json()
        data = json.loads(json_str)

        assert data["project_id"] == 0
        assert data["step_run_id"] == 1
        assert len(data["commands"]) == 1


class TestIDEEngine:
    """Tests for IDEEngine base class."""

    def test_ide_engine_metadata(self):
        """Test IDE engine metadata."""
        engine = ConcreteIDEEngine()
        assert engine.metadata.id == "test-ide"
        assert engine.metadata.kind == EngineKind.IDE
        assert engine.metadata.display_name == "Test IDE"

    def test_ide_engine_check_availability_default(self, tmp_path: Path):
        """Test IDE engine availability check with default command dir."""
        engine = ConcreteIDEEngine()
        # Default uses temp dir which should be writable
        assert engine.check_availability() is True

    def test_ide_engine_check_availability_with_dir(self, tmp_path: Path):
        """Test IDE engine availability check with specified command dir."""
        engine = ConcreteIDEEngine(command_dir=tmp_path)
        assert engine.check_availability() is True

    def test_ide_engine_write_command_file(self, tmp_path: Path):
        """Test command file generation."""
        engine = ConcreteIDEEngine(command_dir=tmp_path)

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Test instruction",
            working_dir=str(tmp_path),
            sandbox=SandboxMode.WORKSPACE_WRITE,
        )

        # Get command file path
        command_path = engine._get_command_file_path(req)
        assert "cmd-1-2-3" in str(command_path)

    def test_ide_engine_get_result_file_path(self, tmp_path: Path):
        """Test result file path derivation."""
        engine = ConcreteIDEEngine(command_dir=tmp_path)

        command_path = tmp_path / "cmd-1-2-3.json"
        result_path = engine._get_result_file_path(command_path)

        assert result_path == tmp_path / "cmd-1-2-3.result.json"

    def test_ide_engine_execute_timeout(self, tmp_path: Path):
        """Test IDE engine returns timeout error when no result file."""
        engine = ConcreteIDEEngine(
            command_dir=tmp_path,
            result_timeout=1,  # 1 second timeout
        )

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Test",
            working_dir=str(tmp_path),
            sandbox=SandboxMode.WORKSPACE_WRITE,
            timeout=1,
        )

        # Execute should timeout since no result file will be written
        result = engine.execute(req)

        assert result.success is False
        assert "timeout" in result.error.lower() or result.metadata.get("timeout") is True

    def test_ide_engine_parse_result_success(self, tmp_path: Path):
        """Test parsing successful IDE result."""
        engine = ConcreteIDEEngine(command_dir=tmp_path)

        result_data = {
            "success": True,
            "stdout": "File created successfully",
            "stderr": "",
            "changes": [
                {"file": "main.py", "action": "create", "content": "# new file"}
            ],
        }

        result = engine._parse_result(result_data)
        assert result.success is True
        assert "successfully" in result.stdout.lower()

    def test_ide_engine_parse_result_failure(self, tmp_path: Path):
        """Test parsing failed IDE result."""
        engine = ConcreteIDEEngine(command_dir=tmp_path)

        result_data = {
            "success": False,
            "error": "Permission denied",
        }

        result = engine._parse_result(result_data)
        assert result.success is False

    def test_ide_engine_generate_commands(self, tmp_path: Path):
        """Test command generation from request."""
        engine = ConcreteIDEEngine(command_dir=tmp_path)

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Create a new file",
            working_dir=str(tmp_path),
            sandbox=SandboxMode.WORKSPACE_WRITE,
        )

        commands = engine._generate_commands(req, SandboxMode.WORKSPACE_WRITE)

        assert len(commands) == 1
        assert commands[0].command_type == "edit"
        assert commands[0].target == str(tmp_path)
        assert "Create a new file" in commands[0].instruction

    def test_ide_engine_plan(self, tmp_path: Path):
        """Test plan method uses full access sandbox."""
        engine = ConcreteIDEEngine(command_dir=tmp_path, result_timeout=1)

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Plan the architecture",
            working_dir=str(tmp_path),
        )

        result = engine.plan(req)
        assert result.metadata.get("sandbox") == SandboxMode.FULL_ACCESS.value

    def test_ide_engine_qa(self, tmp_path: Path):
        """Test qa method uses read-only sandbox."""
        engine = ConcreteIDEEngine(command_dir=tmp_path, result_timeout=1)

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Review the code",
            working_dir=str(tmp_path),
        )

        result = engine.qa(req)
        assert result.metadata.get("sandbox") == SandboxMode.READ_ONLY.value


class TestCursorEngine:
    """Tests for Cursor engine adapter."""

    def test_cursor_engine_metadata(self):
        """Test Cursor engine creation and metadata."""
        from devgodzilla.engines.cursor import CursorEngine

        engine = CursorEngine()
        assert engine.metadata.id == "cursor"
        assert engine.metadata.kind == EngineKind.IDE
        assert "multi-file-edit" in engine.metadata.capabilities

    def test_cursor_engine_command_generation(self, tmp_path: Path):
        """Test Cursor command generation."""
        from devgodzilla.engines.cursor import CursorEngine

        engine = CursorEngine(command_dir=tmp_path)

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Fix the bug in main.py",
            working_dir=str(tmp_path),
            sandbox=SandboxMode.WORKSPACE_WRITE,
        )

        commands = engine._generate_commands(req, SandboxMode.WORKSPACE_WRITE)
        assert len(commands) >= 1
        assert commands[0].command_type == "edit"

    def test_cursor_engine_infer_command_type(self):
        """Test Cursor command type inference from sandbox mode."""
        from devgodzilla.engines.cursor import CursorEngine

        engine = CursorEngine()

        assert engine._infer_command_type(SandboxMode.FULL_ACCESS) == "plan"
        assert engine._infer_command_type(SandboxMode.READ_ONLY) == "review"
        assert engine._infer_command_type(SandboxMode.WORKSPACE_WRITE) == "edit"

    def test_register_cursor_engine(self):
        """Test Cursor engine registration function."""
        from devgodzilla.engines.cursor import register_cursor_engine

        engine = register_cursor_engine()
        assert engine.metadata.id == "cursor"


class TestCopilotEngine:
    """Tests for GitHub Copilot engine adapter."""

    def test_copilot_engine_metadata(self):
        """Test Copilot engine creation and metadata."""
        from devgodzilla.engines.copilot import CopilotEngine

        engine = CopilotEngine()
        assert engine.metadata.id == "copilot"
        assert engine.metadata.kind == EngineKind.IDE
        assert "chat" in engine.metadata.capabilities

    def test_copilot_engine_modes(self):
        """Test Copilot engine modes."""
        from devgodzilla.engines.copilot import CopilotEngine

        ide_engine = CopilotEngine(mode="ide")
        assert ide_engine._mode == "ide"

        chat_engine = CopilotEngine(mode="chat")
        assert chat_engine._mode == "chat"

    def test_copilot_engine_command_generation(self, tmp_path: Path):
        """Test Copilot command generation."""
        from devgodzilla.engines.copilot import CopilotEngine

        engine = CopilotEngine(command_dir=tmp_path)

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Suggest improvements",
            working_dir=str(tmp_path),
            sandbox=SandboxMode.WORKSPACE_WRITE,
            prompt_files=["main.py", "utils.py"],
        )

        commands = engine._generate_commands(req, SandboxMode.WORKSPACE_WRITE)
        # Should have context command for multi-file + primary command
        assert len(commands) >= 1

    def test_copilot_parse_response(self, tmp_path: Path):
        """Test Copilot response parsing."""
        from devgodzilla.engines.copilot import CopilotEngine

        engine = CopilotEngine(command_dir=tmp_path)

        result_data = {
            "success": True,
            "suggestions": [
                {"file": "main.py", "line": 10, "code": "improved code"}
            ],
            "chat_response": "I suggest the following changes...",
        }

        result = engine._parse_response(result_data)
        assert result.success is True
        assert "main.py" in result.stdout
        assert result.metadata["suggestion_count"] == 1

    def test_register_copilot_engine(self):
        """Test Copilot engine registration function."""
        from devgodzilla.engines.copilot import register_copilot_engine

        engine = register_copilot_engine()
        assert engine.metadata.id == "copilot"


class TestCopilotAPIEngine:
    """Tests for GitHub Copilot API engine."""

    def test_copilot_api_engine_metadata(self):
        """Test Copilot API engine metadata."""
        from devgodzilla.engines.copilot import CopilotAPIEngine

        engine = CopilotAPIEngine()
        assert engine.metadata.id == "copilot-api"
        assert engine.metadata.kind == EngineKind.API

    def test_copilot_api_build_request_config(self):
        """Test Copilot API request config building."""
        from devgodzilla.engines.copilot import CopilotAPIEngine

        engine = CopilotAPIEngine(api_key="test-key")

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Test",
            working_dir=".",
        )

        config = engine._build_request_config(req, SandboxMode.WORKSPACE_WRITE)
        assert "copilot" in config.endpoint.lower()
        assert config.method == "POST"
