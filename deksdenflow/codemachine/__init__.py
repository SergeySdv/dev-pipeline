"""
Helpers for ingesting CodeMachine-style configuration into the orchestrator.
"""

from .config_loader import (
    AgentSpec,
    CodeMachineConfig,
    ConfigError,
    ModulePolicy,
    agent_to_dict,
    config_to_template_payload,
    load_codemachine_config,
    policy_to_dict,
)

__all__ = [
    "AgentSpec",
    "CodeMachineConfig",
    "ConfigError",
    "ModulePolicy",
    "agent_to_dict",
    "config_to_template_payload",
    "load_codemachine_config",
    "policy_to_dict",
]
