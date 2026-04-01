# External Navigation And Review Links

Date: 2026-03-26

## Goal

Give the TUI clear drill-down and review affordances for repository URLs, external review pages, and cross-resource jumps inside the shell.

## Primary User Flow

1. User selects a project, protocol, step, run, or artifact.
2. Right inspector shows internal navigation targets and external review actions.
3. User opens linked context through commands, copies IDs, or launches a browser if supported.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Runs] [Events] [Queues] [Settings]                 |
+--------------------------------------------------------------------------------------------------+
| Actions: /open project   /open protocol   /open run   /open repo   /copy link                    |
+-------------------------+------------------------------------------+------------------------------+
| Objects                 | Chat / Transcript                        | Review Links                 |
|                         |                                          |                              |
| > Protocol 88           | You> open the implementation review      | project page                 |
|   Step 331              |                                          | protocol page                |
|   Run 6d31d2a           | Agent> I pinned the available review     | step page                    |
|                         |        targets on the right.             | run page                     |
| Quick Links             |                                          | repository URL               |
| > repo                  | [tool ] copied run detail URL            | artifact preview             |
|   run detail            |                                          |                              |
|   artifact review       |                                          |                              |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=links | object=run:6d31d2a | action=copy-url                                         |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/open project 12`
- `/open protocol 88`
- `/open step 331`
- `/open run 6d31d2a`
- `/open repo 12`
- `/copy link protocol 88`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: cross-resource navigation and launch actions
- `tui-rs/src/state.rs`: selected object and link state
- `tui-rs/src/models.rs`: store URLs where provided by backend
- `tui-rs/src/ui.rs`: link action rendering

Suggested new Rust files:

- `tui-rs/src/ui/flows/links.rs`

State additions:

- `selected_object_ref`
- `review_links`
- `external_action_result`

Done when:

- cross-resource drill-down is easy from any inspector
- review URLs are visible and actionable
- copy/open actions are consistent across objects

