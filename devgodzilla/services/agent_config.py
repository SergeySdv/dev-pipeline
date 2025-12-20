"""
DevGodzilla Agent Configuration Service

Loads and manages agent configurations from YAML files.
Provides runtime health checks and agent capability discovery.
"""

import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

from devgodzilla.services.base import Service, ServiceContext


@dataclass
class AgentConfig:
    """Configuration for a single AI agent."""
    id: str
    name: str
    kind: str  # cli, ide, api
    command: Optional[str] = None
    command_dir: Optional[str] = None
    endpoint: Optional[str] = None
    default_model: Optional[str] = None
    sandbox: str = "none"  # none, workspace-write, cloud
    capabilities: List[str] = field(default_factory=list)
    enabled: bool = True
    format: str = "default"
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    
    @property
    def is_cli(self) -> bool:
        return self.kind == "cli"
    
    @property
    def is_ide(self) -> bool:
        return self.kind == "ide"
    
    @property
    def is_api(self) -> bool:
        return self.kind == "api"


@dataclass
class HealthCheckResult:
    """Result of an agent health check."""
    agent_id: str
    available: bool
    version: Optional[str] = None
    error: Optional[str] = None
    response_time_ms: Optional[float] = None


class AgentConfigService(Service):
    """
    Manages agent configurations and health checks.
    
    Loads configuration from YAML and provides:
    - Agent discovery
    - Health checks
    - Capability matching
    - Default agent selection
    """
    
    DEFAULT_CONFIG_PATH = "config/agents.yaml"
    
    def __init__(
        self,
        context: ServiceContext,
        config_path: Optional[str] = None,
    ) -> None:
        super().__init__(context)
        self._config_path = config_path
        self._agents: Dict[str, AgentConfig] = {}
        self._defaults: Dict[str, str] = {}
        self._health_config: Dict[str, Any] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}
        self._projects: Dict[str, Dict[str, Any]] = {}
        self._loaded = False
    
    def load_config(self, force: bool = False) -> None:
        """Load agent configuration from YAML file."""
        if self._loaded and not force:
            return

        if yaml is None:
            # Minimal fallback when PyYAML isn't installed.
            self._agents = {
                "codex": AgentConfig(id="codex", name="OpenAI Codex", kind="cli", enabled=True),
                "opencode": AgentConfig(id="opencode", name="OpenCode", kind="cli", enabled=True),
            }
            self._defaults = {"code_gen": "opencode"}
            self._health_config = {}
            self._prompts = {}
            self._projects = {}
            self._loaded = True
            return
            
        config_path = self._resolve_config_path()
        if not config_path.exists():
            self.logger.warning("agent_config_not_found", extra={"path": str(config_path)})
            self._create_default_config(config_path)

        try:
            data = self._load_raw_config()
            self._agents = {}
            for agent_id, agent_data in (data.get("agents") or {}).items():
                if not isinstance(agent_data, dict):
                    continue
                self._agents[agent_id] = self._parse_agent(agent_id, agent_data)

            self._defaults = data.get("defaults", {}) or {}
            self._health_config = data.get("health_check", {}) or {}
            self._prompts = data.get("prompts", {}) or {}
            self._projects = data.get("projects", {}) or {}
            self._loaded = True

            self.logger.info(
                "agent_config_loaded",
                extra={"agent_count": len(self._agents), "path": str(config_path)},
            )

        except Exception as e:
            self.logger.error("agent_config_load_failed", extra={"error": str(e)})
            raise

    def _load_raw_config(self) -> Dict[str, Any]:
        config_path = self._resolve_config_path()
        if not config_path.exists():
            self._create_default_config(config_path)
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
        return data or {}

    def _write_raw_config(self, data: Dict[str, Any]) -> None:
        config_path = self._resolve_config_path()
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def _parse_agent(self, agent_id: str, agent_data: Dict[str, Any], base: Optional[AgentConfig] = None) -> AgentConfig:
        if base:
            values = {
                "id": base.id,
                "name": base.name,
                "kind": base.kind,
                "command": base.command,
                "command_dir": base.command_dir,
                "endpoint": base.endpoint,
                "default_model": base.default_model,
                "sandbox": base.sandbox,
                "capabilities": list(base.capabilities),
                "enabled": base.enabled,
                "format": base.format,
                "timeout_seconds": base.timeout_seconds,
                "max_retries": base.max_retries,
            }
        else:
            values = {
                "id": agent_id,
                "name": agent_id,
                "kind": "cli",
                "command": None,
                "command_dir": None,
                "endpoint": None,
                "default_model": None,
                "sandbox": "none",
                "capabilities": [],
                "enabled": True,
                "format": "default",
                "timeout_seconds": None,
                "max_retries": None,
            }

        if "name" in agent_data:
            values["name"] = agent_data.get("name") or agent_id
        if "kind" in agent_data:
            values["kind"] = agent_data.get("kind") or values["kind"]
        if "command" in agent_data or "cli_tool" in agent_data:
            values["command"] = agent_data.get("command") or agent_data.get("cli_tool")
        if "command_dir" in agent_data:
            values["command_dir"] = agent_data.get("command_dir")
        if "endpoint" in agent_data:
            values["endpoint"] = agent_data.get("endpoint")
        if "default_model" in agent_data:
            values["default_model"] = agent_data.get("default_model")
        if "sandbox" in agent_data:
            values["sandbox"] = agent_data.get("sandbox") or values["sandbox"]
        if "capabilities" in agent_data:
            values["capabilities"] = agent_data.get("capabilities") or []
        if "enabled" in agent_data:
            values["enabled"] = agent_data.get("enabled", True)
        elif "available" in agent_data:
            values["enabled"] = bool(agent_data.get("available"))
        if "format" in agent_data:
            values["format"] = agent_data.get("format") or values["format"]
        if "timeout_seconds" in agent_data:
            values["timeout_seconds"] = agent_data.get("timeout_seconds")
        if "max_retries" in agent_data:
            values["max_retries"] = agent_data.get("max_retries")

        raw_caps = values.get("capabilities") or []
        if isinstance(raw_caps, str):
            raw_caps = [c.strip() for c in raw_caps.split(",") if c.strip()]
        elif not isinstance(raw_caps, list):
            raw_caps = list(raw_caps)
        values["capabilities"] = list(raw_caps)
        return AgentConfig(**values)

    def _project_key(self, project_id: Optional[int | str]) -> Optional[str]:
        if project_id is None:
            return None
        return str(project_id)

    def _get_project_overrides(self, project_id: Optional[int | str]) -> Dict[str, Any]:
        key = self._project_key(project_id)
        if not key:
            return {}
        overrides = self._projects.get(key)
        if not isinstance(overrides, dict):
            return {}
        return overrides

    def _inherit_project(self, overrides: Dict[str, Any]) -> bool:
        inherit = overrides.get("inherit", True)
        return bool(inherit) if inherit is not None else True

    def _resolve_agents_map(self, project_id: Optional[int | str]) -> Dict[str, AgentConfig]:
        self.load_config()
        overrides = self._get_project_overrides(project_id)
        inherit = self._inherit_project(overrides)
        resolved: Dict[str, AgentConfig] = {}
        if inherit:
            for agent_id, agent in self._agents.items():
                resolved[agent_id] = replace(agent)

        project_agents = overrides.get("agents") or {}
        if isinstance(project_agents, dict):
            for agent_id, agent_data in project_agents.items():
                if not isinstance(agent_data, dict):
                    continue
                base = resolved.get(agent_id)
                resolved[agent_id] = self._parse_agent(agent_id, agent_data, base=base)

        return resolved

    def _resolve_prompts_map(self, project_id: Optional[int | str]) -> Dict[str, Dict[str, Any]]:
        self.load_config()
        overrides = self._get_project_overrides(project_id)
        inherit = self._inherit_project(overrides)
        resolved: Dict[str, Dict[str, Any]] = {}
        if inherit:
            resolved.update({pid: dict(meta) for pid, meta in self._prompts.items() if isinstance(meta, dict)})

        project_prompts = overrides.get("prompts") or {}
        if isinstance(project_prompts, dict):
            for prompt_id, prompt_data in project_prompts.items():
                if not isinstance(prompt_data, dict):
                    continue
                merged = dict(resolved.get(prompt_id, {}))
                merged.update(prompt_data)
                resolved[prompt_id] = merged

        return resolved

    def _resolve_defaults(self, project_id: Optional[int | str]) -> Dict[str, Any]:
        self.load_config()
        overrides = self._get_project_overrides(project_id)
        inherit = self._inherit_project(overrides)
        defaults = dict(self._defaults or {})
        project_defaults = overrides.get("defaults") or {}
        if not inherit:
            defaults = {}
        if isinstance(project_defaults, dict):
            defaults.update(project_defaults)
        return defaults
    
    def _resolve_config_path(self) -> Path:
        """Resolve the configuration file path."""
        if self._config_path:
            return Path(self._config_path)

        config_path = None
        try:
            config_path = self.context.config.agent_config_path
        except Exception:
            config_path = None

        if config_path:
            return Path(config_path)

        # Look in devgodzilla package directory
        package_dir = Path(__file__).parent.parent
        return package_dir / self.DEFAULT_CONFIG_PATH
    
    def _create_default_config(self, path: Path) -> None:
        """Create a default configuration file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        # Minimal default config
        default_config = {
            "agents": {
                "codex": {
                    "name": "OpenAI Codex",
                    "kind": "cli",
                    "command": "codex",
                    "enabled": True,
                },
                "opencode": {
                    "name": "OpenCode",
                    "kind": "cli",
                    "command": "opencode",
                    "enabled": True,
                },
            },
            "defaults": {
                "code_gen": "opencode",
            },
        }
        with open(path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
    
    def get_agent(self, agent_id: str, *, project_id: Optional[int | str] = None) -> Optional[AgentConfig]:
        """Get agent configuration by ID."""
        agents = self._resolve_agents_map(project_id)
        return agents.get(agent_id)
    
    def list_agents(self, enabled_only: bool = True, *, project_id: Optional[int | str] = None) -> List[AgentConfig]:
        """List all agents."""
        agents = list(self._resolve_agents_map(project_id).values())
        if enabled_only:
            agents = [a for a in agents if a.enabled]
        return agents
    
    def get_agents_by_capability(self, capability: str, *, project_id: Optional[int | str] = None) -> List[AgentConfig]:
        """Get agents with a specific capability."""
        agents = self._resolve_agents_map(project_id).values()
        return [a for a in agents if capability in a.capabilities and a.enabled]
    
    def get_default_agent(self, task_type: str, *, project_id: Optional[int | str] = None) -> Optional[AgentConfig]:
        """Get the default agent for a task type."""
        agent_id = self.get_default_engine_id(task_type, project_id=project_id)
        if agent_id:
            return self.get_agent(agent_id, project_id=project_id)
        return None

    def get_default_engine_id(
        self,
        stage: str,
        *,
        project_id: Optional[int | str] = None,
        fallback: Optional[str] = None,
    ) -> Optional[str]:
        defaults = self._resolve_defaults(project_id)
        resolved = defaults.get(stage)
        if not resolved and stage == "exec":
            resolved = defaults.get("code_gen")
        if not resolved and stage == "code_gen":
            resolved = defaults.get("exec")
        if not resolved:
            resolved = fallback
        if isinstance(resolved, str) and resolved.strip():
            return resolved.strip()
        return None

    def list_prompts(
        self,
        *,
        project_id: Optional[int | str] = None,
        enabled_only: bool = True,
    ) -> List[Dict[str, Any]]:
        prompts = []
        for prompt_id, meta in self._resolve_prompts_map(project_id).items():
            if not isinstance(meta, dict):
                continue
            enabled = meta.get("enabled", True)
            if enabled_only and not enabled:
                continue
            payload = dict(meta)
            payload["id"] = prompt_id
            prompts.append(payload)
        return prompts

    def get_prompt(self, prompt_id: str, *, project_id: Optional[int | str] = None) -> Optional[Dict[str, Any]]:
        prompts = self._resolve_prompts_map(project_id)
        prompt = prompts.get(prompt_id)
        if not isinstance(prompt, dict):
            return None
        payload = dict(prompt)
        payload["id"] = prompt_id
        return payload

    def get_defaults(self, *, project_id: Optional[int | str] = None) -> Dict[str, Any]:
        return self._resolve_defaults(project_id)

    def get_project_overrides(self, project_id: int | str) -> Dict[str, Any]:
        self.load_config()
        overrides = self._get_project_overrides(project_id)
        payload = {
            "inherit": self._inherit_project(overrides),
            "agents": overrides.get("agents", {}) or {},
            "defaults": overrides.get("defaults", {}) or {},
            "prompts": overrides.get("prompts", {}) or {},
            "assignments": overrides.get("assignments", {}) or {},
        }
        return payload

    def resolve_prompt_assignment(
        self,
        assignment_key: str,
        *,
        project_id: Optional[int | str] = None,
    ) -> Optional[Dict[str, Any]]:
        defaults = self._resolve_defaults(project_id)
        assignments = defaults.get("prompts") if isinstance(defaults, dict) else None
        if not isinstance(assignments, dict):
            return None
        prompt_id = assignments.get(assignment_key)
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            return None
        prompt_id = prompt_id.strip()
        prompts = self._resolve_prompts_map(project_id)
        prompt = prompts.get(prompt_id)
        if isinstance(prompt, dict):
            payload = dict(prompt)
            payload["id"] = prompt_id
            return payload
        if "/" in prompt_id or prompt_id.endswith(".md"):
            return {"id": prompt_id, "path": prompt_id}
        return None
    
    def check_health(self, agent_id: str) -> HealthCheckResult:
        """Check if an agent is available."""
        agent = self.get_agent(agent_id)
        if not agent:
            return HealthCheckResult(
                agent_id=agent_id,
                available=False,
                error="Agent not found",
            )
        
        if not agent.enabled:
            return HealthCheckResult(
                agent_id=agent_id,
                available=False,
                error="Agent is disabled",
            )
        
        if agent.is_cli:
            return self._check_cli_health(agent)
        elif agent.is_api:
            return self._check_api_health(agent)
        else:
            return HealthCheckResult(
                agent_id=agent_id,
                available=False,
                error=f"Health check not supported for kind: {agent.kind}",
            )
    
    def _check_cli_health(self, agent: AgentConfig) -> HealthCheckResult:
        """Check health of a CLI-based agent."""
        import time
        
        if not agent.command:
            return HealthCheckResult(
                agent_id=agent.id,
                available=False,
                error="No command configured",
            )
        
        try:
            start = time.time()
            # Try to get version
            result = subprocess.run(
                [agent.command, "--version"],
                capture_output=True,
                text=True,
                timeout=self._health_config.get("timeout_seconds", 30),
            )
            response_time = (time.time() - start) * 1000
            
            if result.returncode == 0:
                version = result.stdout.strip().split("\n")[0] if result.stdout else None
                return HealthCheckResult(
                    agent_id=agent.id,
                    available=True,
                    version=version,
                    response_time_ms=response_time,
                )
            else:
                return HealthCheckResult(
                    agent_id=agent.id,
                    available=False,
                    error=result.stderr.strip() or "Command failed",
                    response_time_ms=response_time,
                )
                
        except FileNotFoundError:
            return HealthCheckResult(
                agent_id=agent.id,
                available=False,
                error=f"Command not found: {agent.command}",
            )
        except subprocess.TimeoutExpired:
            return HealthCheckResult(
                agent_id=agent.id,
                available=False,
                error="Health check timed out",
            )
        except Exception as e:
            return HealthCheckResult(
                agent_id=agent.id,
                available=False,
                error=str(e),
            )
    
    def _check_api_health(self, agent: AgentConfig) -> HealthCheckResult:
        """Check health of an API-based agent."""
        # Placeholder for API health checks
        return HealthCheckResult(
            agent_id=agent.id,
            available=False,
            error="API health checks not yet implemented",
        )
    
    def check_all_health(self) -> List[HealthCheckResult]:
        """Check health of all enabled agents."""
        self.load_config()
        results = []
        for agent in self.list_agents(enabled_only=True):
            results.append(self.check_health(agent.id))
        return results

    def update_config(
        self,
        agent_id: str,
        *,
        enabled: Optional[bool] = None,
        default_model: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        command_dir: Optional[str] = None,
        name: Optional[str] = None,
        kind: Optional[str] = None,
        command: Optional[str] = None,
        endpoint: Optional[str] = None,
        sandbox: Optional[str] = None,
        format: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        project_id: Optional[int | str] = None,
    ) -> AgentConfig:
        """Update agent configuration and save to YAML."""
        self.load_config()

        if yaml is None:
            raise RuntimeError("PyYAML is required to update agent configuration")

        update_data: Dict[str, Any] = {}
        if enabled is not None:
            update_data["enabled"] = enabled
        if default_model is not None:
            update_data["default_model"] = default_model
        if capabilities is not None:
            update_data["capabilities"] = capabilities
        if command_dir is not None:
            update_data["command_dir"] = command_dir
        if name is not None:
            update_data["name"] = name
        if kind is not None:
            update_data["kind"] = kind
        if command is not None:
            update_data["command"] = command
        if endpoint is not None:
            update_data["endpoint"] = endpoint
        if sandbox is not None:
            update_data["sandbox"] = sandbox
        if format is not None:
            update_data["format"] = format
        if timeout_seconds is not None:
            update_data["timeout_seconds"] = timeout_seconds
        if max_retries is not None:
            update_data["max_retries"] = max_retries

        if not update_data:
            agent = self.get_agent(agent_id, project_id=project_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            return agent

        try:
            data = self._load_raw_config()
            if project_id is not None:
                projects = data.setdefault("projects", {})
                project_key = str(project_id)
                project = projects.setdefault(project_key, {})
                agents_section = project.setdefault("agents", {})
            else:
                agents_section = data.setdefault("agents", {})

            agent_data = agents_section.setdefault(agent_id, {})
            agent_data.update(update_data)

            self._write_raw_config(data)
            self.load_config(force=True)

            self.logger.info(
                "agent_config_updated",
                extra={"agent_id": agent_id, "path": str(self._resolve_config_path())},
            )

            agent = self.get_agent(agent_id, project_id=project_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found after update")
            return agent

        except Exception as e:
            self.logger.error(
                "agent_config_update_failed",
                extra={"agent_id": agent_id, "error": str(e)},
            )
            raise

    def update_defaults(
        self,
        defaults: Dict[str, Any],
        *,
        project_id: Optional[int | str] = None,
    ) -> Dict[str, Any]:
        if yaml is None:
            raise RuntimeError("PyYAML is required to update agent configuration")
        data = self._load_raw_config()
        if project_id is not None:
            projects = data.setdefault("projects", {})
            project_key = str(project_id)
            project = projects.setdefault(project_key, {})
            target = project.setdefault("defaults", {})
        else:
            target = data.setdefault("defaults", {})
        if isinstance(defaults, dict):
            target.update(defaults)
        self._write_raw_config(data)
        self.load_config(force=True)
        return self.get_defaults(project_id=project_id)

    def update_prompt(
        self,
        prompt_id: str,
        prompt_data: Dict[str, Any],
        *,
        project_id: Optional[int | str] = None,
    ) -> Dict[str, Any]:
        if yaml is None:
            raise RuntimeError("PyYAML is required to update agent configuration")
        data = self._load_raw_config()
        if project_id is not None:
            projects = data.setdefault("projects", {})
            project_key = str(project_id)
            project = projects.setdefault(project_key, {})
            prompts_section = project.setdefault("prompts", {})
        else:
            prompts_section = data.setdefault("prompts", {})

        prompt = prompts_section.setdefault(prompt_id, {})
        if isinstance(prompt_data, dict):
            prompt.update(prompt_data)
        self._write_raw_config(data)
        self.load_config(force=True)
        updated = self.get_prompt(prompt_id, project_id=project_id)
        if not updated:
            raise ValueError(f"Prompt {prompt_id} not found after update")
        return updated

    def update_project_overrides(
        self,
        project_id: int | str,
        overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        if yaml is None:
            raise RuntimeError("PyYAML is required to update agent configuration")
        data = self._load_raw_config()
        projects = data.setdefault("projects", {})
        project_key = str(project_id)
        project = projects.setdefault(project_key, {})
        if isinstance(overrides, dict):
            project.update(overrides)
        self._write_raw_config(data)
        self.load_config(force=True)
        return self.get_project_overrides(project_id)
