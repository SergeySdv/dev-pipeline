# Project Lifecycle Actions

Date: 2026-03-26

## Goal

Cover archive, unarchive, delete, duplicate, open repository, and richer project list management in the TUI.

## Primary User Flow

1. User selects a project from the navigator.
2. `Enter` or `a` opens a compact action overlay.
3. Risky actions require confirmation overlays.
4. Center pane narrates the result and any follow-up suggestions.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Runs] [Events] [Queues] [Settings]                 |
+--------------------------------------------------------------------------------------------------+
| Actions: /project archive   /project unarchive   /project duplicate   /project delete            |
+-------------------------+------------------------------------------+------------------------------+
| Projects                | Chat / Transcript                        | Actions                      |
|                         |                                          |                              |
| > api-core              | You> /project archive 12                 | archive                      |
|   billing               |                                          | duplicate                    |
|   docs                  | Agent> Project api-core archived.        | open repo                    |
|                         |        Hidden from default active view.  | delete                       |
| Filters                 |                                          |                              |
| [active] [archived]     | [tool ] project state updated            | confirm on destructive       |
|                         |                                          | actions                      |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=projects | selected=12 | filter=active | overlay=actions                             |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/project archive 12`
- `/project unarchive 12`
- `/project duplicate 12`
- `/project delete 12`
- `/project open-repo 12`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: action palette and confirm modal routing
- `tui-rs/src/state.rs`: project filters and project action state
- `tui-rs/src/api.rs`: add lifecycle endpoints
- `tui-rs/src/ui.rs`: action overlay and filter chips

Suggested new Rust files:

- `tui-rs/src/ui/overlays.rs`
- `tui-rs/src/ui/flows/project_list.rs`

State additions:

- `project_filters`
- `project_action_overlay`
- `project_action_result`

Done when:

- project list can manage real lifecycle operations
- destructive actions are safe and explicit
- archive and duplicate are one-step operator actions

