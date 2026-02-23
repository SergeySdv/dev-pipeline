"""
Tests for GeminiEngine.

NOTE: The gemini.py module currently has import errors (references
EngineInterface and EngineCapability which don't exist in interface.py).
These tests use sys.modules mocking to test the implementation logic.
"""

import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# Mock the missing classes from interface.py
class EngineCapability(str, Enum):
    """Mock EngineCapability for testing."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    MULTIMODAL = "multimodal"
    LONG_CONTEXT = "long_context"


@dataclass
class MockEngineMetadata:
    """Mock EngineMetadata with the structure used by GeminiEngine."""
    engine_id: str
    name: str
    version: str
    capabilities: List[EngineCapability]
    default_model: str
    supported_models: List[str] = field(default_factory=list)


@dataclass
class MockEngineRequest:
    """Mock EngineRequest matching GeminiEngine's expected interface."""
    prompt: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    context: Optional[str] = None
    constraints: Optional[List[str]] = None
    workspace_path: Optional[str] = None


@dataclass
class MockEngineResult:
    """Mock EngineResult matching GeminiEngine's expected interface."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    files_modified: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MockEngineInterface:
    """Mock EngineInterface base class."""
    @property
    def metadata(self) -> MockEngineMetadata:
        raise NotImplementedError
    
    def execute(self, request: MockEngineRequest) -> MockEngineResult:
        raise NotImplementedError
    
    def check_availability(self) -> bool:
        raise NotImplementedError


def _create_mock_interface_module():
    """Create a mock interface module with the missing classes."""
    mock_module = MagicMock()
    mock_module.EngineInterface = MockEngineInterface
    mock_module.EngineMetadata = MockEngineMetadata
    mock_module.EngineRequest = MockEngineRequest
    mock_module.EngineResult = MockEngineResult
    mock_module.EngineCapability = EngineCapability
    return mock_module


@pytest.fixture
def mock_interface_module():
    """Mock the missing interface classes."""
    mock_module = _create_mock_interface_module()
    
    # Clear any cached import
    if 'devgodzilla.engines.gemini' in sys.modules:
        del sys.modules['devgodzilla.engines.gemini']
    
    with patch.dict(sys.modules, {'devgodzilla.engines.interface': mock_module}):
        yield mock_module


def _get_gemini_engine_class():
    """Import and return GeminiEngine class with mocked interface."""
    # Clear cached imports
    for mod in ['devgodzilla.engines.gemini']:
        if mod in sys.modules:
            del sys.modules[mod]
    
    mock_module = _create_mock_interface_module()
    with patch.dict(sys.modules, {'devgodzilla.engines.interface': mock_module}):
        from devgodzilla.engines.gemini import GeminiEngine
        return GeminiEngine


class TestGeminiEngineMetadata:
    """Tests for GeminiEngine metadata and initialization."""

    def test_default_initialization(self, mock_interface_module):
        """Test engine with default settings."""
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        assert engine._model == "gemini-2.5-pro"
        assert engine._timeout == 300
        assert engine._command == "gemini"

    def test_custom_initialization(self, mock_interface_module):
        """Test engine with custom settings."""
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine(
            model="gemini-2.5-flash",
            timeout=600,
            command="gemini-custom",
        )
        assert engine._model == "gemini-2.5-flash"
        assert engine._timeout == 600
        assert engine._command == "gemini-custom"

    def test_metadata_engine_id(self, mock_interface_module):
        """Test metadata has correct engine_id."""
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        metadata = engine.metadata
        assert metadata.engine_id == "gemini-cli"

    def test_metadata_name(self, mock_interface_module):
        """Test metadata has correct name."""
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        metadata = engine.metadata
        assert metadata.name == "Gemini CLI"

    def test_metadata_version(self, mock_interface_module):
        """Test metadata has version."""
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        metadata = engine.metadata
        assert metadata.version == "1.0.0"

    def test_metadata_capabilities(self, mock_interface_module):
        """Test metadata has expected capabilities."""
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        metadata = engine.metadata
        
        capabilities = [c.value if hasattr(c, 'value') else str(c) for c in metadata.capabilities]
        assert "code_generation" in capabilities
        assert "code_review" in capabilities
        assert "multimodal" in capabilities
        assert "long_context" in capabilities

    def test_metadata_default_model(self, mock_interface_module):
        """Test metadata has default model."""
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine(model="gemini-2.5-flash")
        metadata = engine.metadata
        assert metadata.default_model == "gemini-2.5-flash"

    def test_metadata_supported_models(self, mock_interface_module):
        """Test metadata lists supported models."""
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        metadata = engine.metadata
        
        assert "gemini-2.5-pro" in metadata.supported_models
        assert "gemini-2.5-flash" in metadata.supported_models
        assert "gemini-2.0-flash" in metadata.supported_models


class TestGeminiEngineAvailability:
    """Tests for check_availability method."""

    @patch("subprocess.run")
    def test_available_when_installed(self, mock_run, mock_interface_module):
        """Test availability returns True when gemini CLI is installed."""
        mock_run.return_value = MagicMock(returncode=0)
        
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        assert engine.check_availability() is True
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gemini" in call_args
        assert "--version" in call_args

    @patch("subprocess.run")
    def test_unavailable_when_not_installed(self, mock_run, mock_interface_module):
        """Test availability returns False when gemini CLI is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        assert engine.check_availability() is False

    @patch("subprocess.run")
    def test_unavailable_on_nonzero_exit(self, mock_run, mock_interface_module):
        """Test availability returns False on non-zero exit code."""
        mock_run.return_value = MagicMock(returncode=1)
        
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        assert engine.check_availability() is False

    @patch("subprocess.run")
    def test_unavailable_on_timeout(self, mock_run, mock_interface_module):
        """Test availability returns False on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gemini", timeout=10)
        
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        assert engine.check_availability() is False

    @patch("subprocess.run")
    def test_availability_timeout_value(self, mock_run, mock_interface_module):
        """Test availability check uses short timeout."""
        mock_run.return_value = MagicMock(returncode=0)
        
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine()
        engine.check_availability()
        
        timeout = mock_run.call_args[1].get("timeout")
        assert timeout == 10


class TestGeminiEngineExecute:
    """Tests for execute method."""

    @pytest.fixture
    def engine(self, mock_interface_module):
        GeminiEngine = _get_gemini_engine_class()
        return GeminiEngine()

    @pytest.fixture
    def basic_request(self, tmp_path):
        return MockEngineRequest(
            prompt="Write a hello world function",
            workspace_path=str(tmp_path),
        )

    @patch("subprocess.run")
    def test_execute_success(self, mock_run, engine, basic_request):
        """Test successful execution returns success result."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Function created successfully",
            stderr="",
        )
        
        result = engine.execute(basic_request)
        
        assert result.success is True
        assert result.output == "Function created successfully"
        assert result.error is None

    @patch("subprocess.run")
    def test_execute_with_custom_model(self, mock_run, engine, tmp_path):
        """Test execution uses custom model when provided."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        
        request = MockEngineRequest(
            prompt="test",
            model="gemini-2.5-flash",
            workspace_path=str(tmp_path),
        )
        result = engine.execute(request)
        
        call_args = mock_run.call_args[0][0]
        assert "--model" in call_args
        model_idx = call_args.index("--model")
        assert call_args[model_idx + 1] == "gemini-2.5-flash"
        assert result.success is True

    @patch("subprocess.run")
    def test_execute_failure_nonzero_exit(self, mock_run, engine, basic_request):
        """Test execution failure on non-zero exit code."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="",  # Empty stderr forces the default message
        )
        
        result = engine.execute(basic_request)
        
        assert result.success is False
        assert "non-zero exit code" in result.error

    @patch("subprocess.run")
    def test_execute_failure_with_stderr(self, mock_run, engine, basic_request):
        """Test execution failure returns stderr when available."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: something went wrong",
        )
        
        result = engine.execute(basic_request)
        
        assert result.success is False
        assert "Error: something went wrong" in result.error

    @patch("subprocess.run")
    def test_execute_timeout(self, mock_run, engine, basic_request):
        """Test execution handles timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="gemini", timeout=300
        )
        
        result = engine.execute(basic_request)
        
        assert result.success is False
        assert "timed out" in result.error.lower()

    @patch("subprocess.run")
    def test_execute_not_installed(self, mock_run, engine, basic_request):
        """Test execution when gemini CLI is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        result = engine.execute(basic_request)
        
        assert result.success is False
        assert "not found" in result.error.lower()

    @patch("subprocess.run")
    def test_execute_sets_working_directory(self, mock_run, engine, basic_request, tmp_path):
        """Test execution uses workspace as working directory."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        
        engine.execute(basic_request)
        
        cwd = mock_run.call_args[1].get("cwd")
        assert cwd == str(tmp_path)

    @patch("subprocess.run")
    def test_execute_default_workspace(self, mock_run, engine):
        """Test execution uses current directory when no workspace."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        
        request = MockEngineRequest(prompt="test", workspace_path=None)
        engine.execute(request)
        
        cwd = mock_run.call_args[1].get("cwd")
        assert cwd == "."

    @patch("subprocess.run")
    def test_execute_includes_metadata(self, mock_run, engine, basic_request):
        """Test result includes metadata."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        
        result = engine.execute(basic_request)
        
        assert "model" in result.metadata
        assert "engine" in result.metadata
        assert result.metadata["engine"] == "gemini-cli"

    @patch("subprocess.run")
    def test_execute_exception_handling(self, mock_run, engine, basic_request):
        """Test execution handles unexpected exceptions."""
        mock_run.side_effect = RuntimeError("Unexpected error")
        
        result = engine.execute(basic_request)
        
        assert result.success is False
        assert "error" in result.error.lower()


class TestGeminiEngineBuildPrompt:
    """Tests for _build_prompt method."""

    @pytest.fixture
    def engine(self, mock_interface_module):
        GeminiEngine = _get_gemini_engine_class()
        return GeminiEngine()

    def test_build_prompt_basic(self, engine):
        """Test building prompt from basic request."""
        request = MockEngineRequest(prompt="Write a function")
        prompt = engine._build_prompt(request)
        
        assert "Write a function" in prompt
        assert "## Task" in prompt

    def test_build_prompt_with_system_prompt(self, engine):
        """Test building prompt includes system instructions."""
        request = MockEngineRequest(
            prompt="Write code",
            system_prompt="You are a helpful coding assistant.",
        )
        prompt = engine._build_prompt(request)
        
        assert "System Instructions" in prompt
        assert "helpful coding assistant" in prompt

    def test_build_prompt_with_context(self, engine):
        """Test building prompt includes context."""
        request = MockEngineRequest(
            prompt="Fix the bug",
            context="The function returns wrong values for negative inputs.",
        )
        prompt = engine._build_prompt(request)
        
        assert "Context" in prompt
        assert "negative inputs" in prompt

    def test_build_prompt_with_constraints(self, engine):
        """Test building prompt includes constraints."""
        request = MockEngineRequest(
            prompt="Refactor the code",
            constraints=[
                "Keep backward compatibility",
                "Add type hints",
            ],
        )
        prompt = engine._build_prompt(request)
        
        assert "Constraints" in prompt
        assert "backward compatibility" in prompt
        assert "type hints" in prompt

    def test_build_prompt_all_sections(self, engine):
        """Test building prompt with all sections."""
        request = MockEngineRequest(
            prompt="Implement feature X",
            system_prompt="Be concise",
            context="This is for a web app",
            constraints=["Use Python 3.12"],
        )
        prompt = engine._build_prompt(request)
        
        assert "System Instructions" in prompt
        assert "Task" in prompt
        assert "Context" in prompt
        assert "Constraints" in prompt


class TestGeminiEnginePromptFile:
    """Tests for long prompt file handling."""

    @pytest.fixture
    def engine(self, mock_interface_module):
        GeminiEngine = _get_gemini_engine_class()
        return GeminiEngine()

    @patch("subprocess.run")
    @patch("tempfile.NamedTemporaryFile")
    def test_uses_file_for_long_prompt(self, mock_tempfile, mock_run, engine, tmp_path):
        """Test that long prompts are written to a file."""
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/prompt.md"
        mock_tempfile.return_value = mock_file
        
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        
        # Create a long prompt (>1000 chars)
        long_prompt = "x" * 1500
        request = MockEngineRequest(
            prompt=long_prompt,
            workspace_path=str(tmp_path),
        )
        
        engine.execute(request)
        
        # Check that prompt file was written
        mock_file.write.assert_called_once()
        written_content = mock_file.write.call_args[0][0]
        assert long_prompt in written_content

    @patch("subprocess.run")
    def test_uses_inline_prompt_for_short_prompt(self, mock_run, engine, tmp_path):
        """Test that short prompts are passed inline."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        
        short_prompt = "Write a simple function"
        request = MockEngineRequest(
            prompt=short_prompt,
            workspace_path=str(tmp_path),
        )
        
        engine.execute(request)
        
        call_args = mock_run.call_args[0][0]
        assert "--prompt" in call_args
        prompt_idx = call_args.index("--prompt")
        assert short_prompt in call_args[prompt_idx + 1]


class TestGeminiEngineCustomCommand:
    """Tests for custom command configuration."""

    @patch("subprocess.run")
    def test_uses_custom_command(self, mock_run, mock_interface_module, tmp_path):
        """Test engine uses custom command when configured."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        
        GeminiEngine = _get_gemini_engine_class()
        engine = GeminiEngine(command="gemini-custom-cli")
        request = MockEngineRequest(
            prompt="test",
            workspace_path=str(tmp_path),
        )
        engine.execute(request)
        
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "gemini-custom-cli"
