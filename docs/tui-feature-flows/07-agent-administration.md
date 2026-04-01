# Agent Administration

Date: 2026-03-26

## Goal

Add a terminal-appropriate surface for agent inventory, health, metrics, prompt templates, assignments, config, and setup testing.

## Primary User Flow

1. User opens an `Agents` tab or launches `/agent list`.
2. Center pane explains agent state and suggested actions.
3. Right inspector shows the selected agent or template.
4. User edits assignments or runs setup tests from commands and overlays.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Runs] [Events] [Queues] [Agents] [Settings]        |
+--------------------------------------------------------------------------------------------------+
| Actions: /agent list   /agent show   /agent test   /agent assign   /agent templates             |
+-------------------------+------------------------------------------+------------------------------+
| Agents                  | Chat / Transcript                        | Agent opencode               |
|                         |                                          | health: healthy              |
| > opencode              | You> /agent test opencode                | models: glm-4.6              |
|   codex                 |                                          | assignments: planning, qa    |
|   review-bot            | Agent> Setup test started for            | last heartbeat: 12:40        |
|                         |        agent opencode. Results will      |                              |
| Templates               |        stream on the right.              | tabs: summary metrics        |
| > default-planning      |                                          |       assignments config     |
|   reviewer              | [tool ] connectivity check passed        |       templates test         |
|                         | [tool ] model probe running              |                              |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=agents | selected=opencode | test=running | refresh=live                             |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/agent list`
- `/agent show opencode`
- `/agent metrics opencode`
- `/agent templates`
- `/agent assign opencode planning`
- `/agent test opencode`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: add `Agents` page and agent command family
- `tui-rs/src/state.rs`: selected agent, templates, assignments
- `tui-rs/src/api.rs`: add agent inventory, health, metrics, assignment, test endpoints
- `tui-rs/src/models.rs`: add agent models
- `tui-rs/src/ui.rs`: add Agents tab and rendering entry point

Suggested new Rust files:

- `tui-rs/src/ui/flows/agents.rs`
- `tui-rs/src/ui/overlays.rs`

State additions:

- `agents`
- `agent_index`
- `agent_detail`
- `agent_templates`
- `agent_assignments`
- `agent_test_result`

Done when:

- operators can inspect and test agents without leaving the TUI
- assignment changes are possible through commands or overlays
- health and metrics are visible in one place

