"""
DevGodzilla GitHub Copilot Engine

Adapter for GitHub Copilot integration.
Supports both IDE and API-based Copilot interactions.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from devgodzilla.engines.api_engine import (
    APIEngine,
    APIRequestConfig,
    APIResponse,
)
from devgodzilla.engines.registry import register_engine
from devgodzilla.logging import get_logger

logger = get_logger(__name__)


class CopilotEngine(IDEEngine):
    """
    Engine adapter for GitHub Copilot.
    
    GitHub Copilot is an AI pair programmer that provides code suggestions
    and can be accessed via IDE integration or the Copilot API.
    
    This adapter supports:
    - IDE mode: Generate command files for VS Code Copilot extension
    - Chat mode: Instructions for Copilot Chat conversations
    - API mode: Direct API calls (when available)
    
    Example:
        engine = CopilotEngine()
        result = engine.execute(request)
    """

    def __init__(
        self,
        *,
        command_dir: Optional[Path] = None,
        result_timeout: int = 300,
        default_model: Optional[str] = None,
        mode: str = "ide",  # "ide", "chat", "api"
        api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize Copilot engine.
        
        Args:
            command_dir: Directory for command files
            result_timeout: Seconds to wait for result
            default_model: Default model (copilot, gpt-4, etc.)
            mode: Execution mode ("ide", "chat", "api")
            api_key: GitHub token for API access
        """
        super().__init__(
            command_dir=command_dir,
            result_timeout=result_timeout,
        )
        self._default_model = default_model or os.environ.get(
            "DEVGODZILLA_COPILOT_MODEL", "copilot"
        )
        self._mode = mode
        self._api_key = api_key or os.environ.get("GITHUB_TOKEN")

    @property
    def metadata(self) -> EngineMetadata:
        return EngineMetadata(
            id="copilot",
            display_name="GitHub Copilot",
            kind=EngineKind.IDE,
            default_model=self._default_model,
            description="GitHub Copilot AI pair programmer",
            capabilities=[
                "plan",
                "execute",
                "qa",
                "code-completion",
                "chat",
                "multi-file-context",
            ],
        )

    def _get_command_dir(self, req: EngineRequest) -> Path:
        """Get command directory, preferring workspace .devgodzilla dir."""
        if self._command_dir:
            return self._command_dir
        
        workspace_dir = Path(req.working_dir)
        command_dir = workspace_dir / ".devgodzilla" / "copilot"
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
        Generate Copilot commands from the request.
        
        Creates commands for:
        - Code completion/editing suggestions
        - Copilot Chat conversations
        - Workspace-aware context building
        """
        commands: List[IDECommand] = []
        prompt_text = self.get_prompt_text(req)
        command_type = self._infer_command_type(sandbox)
        
        # Determine Copilot mode based on task type
        if self._mode == "chat" or command_type == "plan":
            copilot_mode = "chat"
        else:
            copilot_mode = "edit"
        
        # Primary command
        primary_command = IDECommand(
            command_type=command_type,
            target=req.working_dir,
            instruction=prompt_text,
            context={
                "copilot_mode": copilot_mode,
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
        
        # Add context-gathering commands for multi-file operations
        if len(req.prompt_files) > 1:
            context_command = IDECommand(
                command_type="context",
                target=req.working_dir,
                instruction="Analyze the following files for context",
                context={
                    "files": req.prompt_files,
                    "operation": "multi-file-analysis",
                },
            )
            commands.insert(0, context_command)
        
        return commands

    def _parse_response(self, result_data) -> EngineResult:
        """
        Parse Copilot extension result.
        
        Expected format:
        {
            "success": bool,
            "suggestions": [{"file": str, "line": int, "code": str}],
            "output": str,
            "chat_response": str,
            "error": str | null
        }
        """
        if result_data is None:
            return EngineResult(
                success=False,
                error="Timeout waiting for Copilot response",
                metadata={"timeout": True},
            )
        
        success = result_data.get("success", False)
        suggestions = result_data.get("suggestions", [])
        output = result_data.get("output", "")
        chat_response = result_data.get("chat_response", "")
        error = result_data.get("error")
        
        # Build stdout from suggestions and chat
        parts = []
        
        if chat_response:
            parts.append(f"Copilot Chat:\n{chat_response}")
        
        if suggestions:
            suggestion_summary = "\n".join(
                f"- {s.get('file', 'unknown')}:{s.get('line', '?')}"
                for s in suggestions
            )
            parts.append(f"Suggestions:\n{suggestion_summary}")
        
        if output:
            parts.append(output)
        
        stdout = "\n\n".join(parts) if parts else ""
        
        return EngineResult(
            success=success,
            stdout=stdout,
            stderr="",
            error=error,
            metadata={
                "suggestions": suggestions,
                "suggestion_count": len(suggestions),
                "chat_response": chat_response,
            },
        )

    def sync_config(self, additional_agents: Optional[List[dict]] = None) -> None:
        """
        Generate Copilot configuration files.
        
        Creates or updates:
        - .github/copilot-instructions.md for custom instructions
        """
        logger.info(
            "copilot_sync_config",
            extra={"additional_agents": len(additional_agents) if additional_agents else 0},
        )

    def check_availability(self) -> bool:
        """
        Check if Copilot integration is available.
        
        Checks for VS Code with Copilot extension or API access.
        """
        try:
            # Check for GitHub token (API mode)
            if self._api_key:
                return True
            
            # Check for VS Code with Copilot
            home = Path.home()
            vscode_extensions = home / ".vscode" / "extensions"
            
            if vscode_extensions.exists():
                # Look for Copilot extension
                for ext_dir in vscode_extensions.iterdir():
                    if "copilot" in ext_dir.name.lower() and "github" in ext_dir.name.lower():
                        return True
            
            # Check for command dir writability
            return super().check_availability()
            
        except Exception:
            return False


class CopilotAPIEngine(APIEngine):
    """
    API-based engine for GitHub Copilot.
    
    Uses the GitHub Copilot API for direct code generation.
    Requires a valid GitHub token with Copilot access.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        default_timeout: int = 300,
    ) -> None:
        env_key = api_key or os.environ.get("GITHUB_TOKEN")
        super().__init__(
            base_url="https://api.github.com",
            api_key=env_key,
            default_timeout=default_timeout,
        )
        self._default_model = default_model or os.environ.get(
            "DEVGODZILLA_COPILOT_MODEL", "gpt-4"
        )

    @property
    def metadata(self) -> EngineMetadata:
        return EngineMetadata(
            id="copilot-api",
            display_name="GitHub Copilot API",
            kind=EngineKind.API,
            default_model=self._default_model,
            description="GitHub Copilot API for code generation",
            capabilities=["plan", "execute", "qa", "chat"],
        )

    def _build_request_config(
        self,
        req: EngineRequest,
        sandbox: SandboxMode,
    ) -> APIRequestConfig:
        """Build API request configuration."""
        return APIRequestConfig(
            endpoint="https://api.github.com/copilot/chat/completions",
            method="POST",
            headers={
                "Accept": "application/vnd.github.copilot+json",
                "Editor-Version": "DevGodzilla/1.0",
            },
            timeout=req.timeout or self._default_timeout,
            retries=3,
        )

    def _build_request_body(
        self,
        req: EngineRequest,
        sandbox: SandboxMode,
    ) -> Dict[str, Any]:
        """Build request body for Copilot API."""
        prompt_text = self.get_prompt_text(req)
        
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt(sandbox),
            },
            {
                "role": "user",
                "content": prompt_text,
            },
        ]
        
        return {
            "model": req.model or self._default_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
        }

    def _get_system_prompt(self, sandbox: SandboxMode) -> str:
        """Get system prompt based on sandbox mode."""
        if sandbox == SandboxMode.FULL_ACCESS:
            return "You are an expert software architect planning code changes."
        elif sandbox == SandboxMode.READ_ONLY:
            return "You are a code reviewer analyzing code for quality and issues."
        else:
            return "You are an expert programmer implementing code changes."

    def _parse_response(
        self,
        response: APIResponse,
        req: EngineRequest,
    ) -> EngineResult:
        """Parse API response into EngineResult."""
        if not response.success:
            return EngineResult(
                success=False,
                error=response.error or "API request failed",
            )
        
        if not response.data:
            return EngineResult(
                success=False,
                error="Empty response from API",
            )
        
        try:
            choices = response.data.get("choices", [])
            if not choices:
                return EngineResult(
                    success=False,
                    error="No choices in API response",
                )
            
            content = choices[0].get("message", {}).get("content", "")
            usage = response.data.get("usage", {})
            
            return EngineResult(
                success=True,
                stdout=content,
                tokens_used=usage.get("total_tokens"),
                metadata={
                    "model": response.data.get("model"),
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                },
            )
            
        except Exception as e:
            return EngineResult(
                success=False,
                error=f"Failed to parse API response: {e}",
            )

    def check_availability(self) -> bool:
        """Check if Copilot API is available."""
        if not self._api_key:
            return False
        return super().check_availability()


def register_copilot_engine(*, default: bool = False, mode: str = "ide") -> CopilotEngine:
    """
    Register CopilotEngine in the global registry.
    
    Args:
        default: If True, set as default engine
        mode: Execution mode ("ide", "chat", "api")
    
    Returns the registered engine instance.
    """
    engine = CopilotEngine(mode=mode)
    register_engine(engine, default=default)
    return engine


def register_copilot_api_engine(*, default: bool = False) -> CopilotAPIEngine:
    """
    Register CopilotAPIEngine in the global registry.
    
    Returns the registered engine instance.
    """
    engine = CopilotAPIEngine()
    register_engine(engine, default=default)
    return engine
