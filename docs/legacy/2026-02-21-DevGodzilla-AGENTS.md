# Agent Management Migration Notes

This note describes how to migrate Windmill agent resources into the YAML-driven agent configuration.

## Source of truth
- YAML config: `config/agents.yaml` (or `DEVGODZILLA_AGENT_CONFIG_PATH`).
- Windmill resources are inputs for migration only; they are not read at runtime by DevGodzilla.

## Field mapping (Windmill -> YAML)
- `value.default_agent` -> `defaults.exec` (or `defaults.code_gen` if you prefer the legacy key)
- `agents.<id>.cli_tool` -> `agents.<id>.command`
- `agents.<id>.available` -> `agents.<id>.enabled`
- `agents.<id>.format` -> `agents.<id>.format`
- `agents.<id>.default_model` -> `agents.<id>.default_model`
- `agents.<id>.sandbox` -> `agents.<id>.sandbox`
- `agents.<id>.command_dir` -> `agents.<id>.command_dir`
- `agents.<id>.endpoint` -> `agents.<id>.endpoint`
- `agents.<id>.timeout_seconds` -> `agents.<id>.timeout_seconds`
- `agents.<id>.max_retries` -> `agents.<id>.max_retries`
- `agents.<id>.capabilities` -> `agents.<id>.capabilities`

## Capability normalization
Windmill resource capabilities often use verbose names (e.g. `code_generation`, `documentation`).
DevGodzilla runtime expects short capability strings (e.g. `code_gen`, `qa`, `reasoning`).
Normalize capability names during migration to keep filters consistent.

## Example migration snippet

```yaml
# windmill/resources/devgodzilla/agents.resource.yaml
value:
  default_agent: "opencode"
  agents:
    codex:
      cli_tool: "codex"
      available: true
      default_model: "gpt-4.1"
```

```yaml
# config/agents.yaml
agents:
  codex:
    name: OpenAI Codex
    kind: cli
    command: codex
    default_model: gpt-4.1
    enabled: true

defaults:
  exec: opencode
```

## Prompt templates
If Windmill stores prompt references elsewhere, add them to the YAML `prompts` section and
reference them from `defaults.prompts` or project overrides (`projects.<id>.prompts`).
