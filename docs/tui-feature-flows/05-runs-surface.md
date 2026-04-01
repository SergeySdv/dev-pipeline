# Runs Surface

Date: 2026-03-26

## Goal

Create a dedicated runs surface with global list, protocol-scoped list, run detail, and navigation from protocols and steps into run investigation.

## Primary User Flow

1. User opens a run from a step, protocol, or slash command.
2. The center transcript explains what the run represents.
3. The right inspector shows metadata, timestamps, attempt, kind, token cost, and status.
4. The lower-right pane tails logs or outputs selected artifacts.
5. User moves back to step or protocol without losing thread context.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Runs] [Events] [Queues] [Settings]                 |
+--------------------------------------------------------------------------------------------------+
| Actions: /run list   /run show   /logs run   /run artifacts   /run open-step                     |
+-------------------------+------------------------------------------+------------------------------+
| Runs                    | Chat / Transcript                        | Run 6d31d2a                  |
|                         |                                          | status: failed               |
| > 6d31d2a failed        | You> /run show 6d31d2a                   | protocol: 88                 |
|   6d31c11 success       |                                          | step: 331                    |
|   6d31b02 success       | Agent> Loaded run 6d31d2a. The failure   | attempt: 3                   |
|                         |        happened during QA after tool      | kind: qa                     |
| Filters                 |        execution completed.               | token cost: 14.2k            |
| [failed] [qa] [latest]  |                                          | started: 12:42               |
|                         | [tool ] fetched run metadata and logs    | ended: 12:43                 |
|                         |                                          | tabs: summary logs           |
|                         |                                          |       artifacts lineage      |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=runs | run=6d31d2a | protocol=88 | step=331 | refresh=live                    |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/run list`
- `/run list --protocol 88`
- `/run show 6d31d2a`
- `/run artifacts 6d31d2a`
- `/run open-step 6d31d2a`
- `/logs run 6d31d2a`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/state.rs`: add a `Runs` page and selected run state
- `tui-rs/src/app.rs`: navigation, data loading, run commands
- `tui-rs/src/api.rs`: add run list/detail endpoints
- `tui-rs/src/models.rs`: add run models
- `tui-rs/src/ui.rs`: add runs tab and rendering entry point

Suggested new Rust files:

- `tui-rs/src/ui/flows/runs.rs`
- `tui-rs/src/ui/results.rs`

State additions:

- `runs`
- `run_index`
- `selected_run`
- `run_logs`
- `run_artifacts`
- `run_filters`

Done when:

- run detail is directly navigable
- protocol and step workspaces can open a run in one action
- logs and artifacts are tied to the selected run

