# Project Detail Workspace

Date: 2026-03-26

## Goal

Add a project-centered workspace that keeps chat in the middle while exposing project overview, specs, branches, clarifications, policy, settings, onboarding, and workflow actions in the inspector.

## Primary User Flow

1. User opens the `Projects` tab or selects a project from the left navigator.
2. The center pane stays conversational and explains current project state.
3. The right inspector opens on `Project summary`.
4. User moves between `summary`, `specs`, `branches`, `clarifications`, `policy`, `settings`, and `onboarding`.
5. User triggers actions from commands or quick actions without leaving the shell.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Events] [Queues] [Settings]                         |
+--------------------------------------------------------------------------------------------------+
| Actions: /project use   /project show   /project policy   /project branches   /project settings  |
+-------------------------+------------------------------------------+------------------------------+
| Projects                | Chat / Transcript                        | Project 12                  |
|                         |                                          | api-core                    |
| > api-core              | You> /project show 12                    | status: active              |
|   billing               |                                          | protocols: 14               |
|   docs                  | Agent> Project api-core loaded.          | last protocol: 88           |
|                         |        Open tabs on the right for        | repo: github.com/org/api    |
| Saved Views             |        branches, specs, policy, and      |                              |
| * Needs onboarding      |        clarifications.                   | tabs: summary specs         |
| * Policy review         |                                          |       branches clarify      |
|                         | [tool ] fetched overview and settings    |       policy settings       |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=projects | project=12 | focus=inspector | agent=codex | refresh=manual             |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/project show 12`
- `/project use 12`
- `/project branches 12`
- `/project prs 12`
- `/project clarify 12`
- `/project policy 12`
- `/project settings 12`
- `/project onboarding 12`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: route tab changes, command dispatch, project actions
- `tui-rs/src/state.rs`: selected project workspace tab, pinned project context
- `tui-rs/src/api.rs`: add project detail, settings, clarifications, PR/worktree endpoints as available
- `tui-rs/src/models.rs`: add project detail DTOs
- `tui-rs/src/ui.rs`: keep shell and delegate project body rendering

Suggested new Rust files:

- `tui-rs/src/ui/flows/project_detail.rs`
- `tui-rs/src/ui/inspector.rs`
- `tui-rs/src/ui/chat.rs`

State additions:

- `project_workspace_tab`
- `project_detail`
- `project_clarifications`
- `project_policy_snapshot`
- `project_settings`
- `project_onboarding_state`

Done when:

- selecting a project opens a real detail workspace
- right inspector tabs are navigable
- project actions work through commands and quick actions
- no separate full-screen form page is required for routine project inspection

