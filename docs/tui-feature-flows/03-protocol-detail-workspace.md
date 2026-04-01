# Protocol Detail Workspace

Date: 2026-03-26

## Goal

Turn protocols into a real workspace with tabs for steps, events, logs, spec, policy, clarifications, feedback, quality, runs, and artifacts.

## Primary User Flow

1. User selects a protocol from the navigator or mentions `@protocol:88`.
2. Center pane remains a running conversation about the protocol.
3. Right inspector becomes the structured protocol workspace.
4. Lower-right pane switches between live events, run logs, or command results.
5. User stays in one thread while moving across protocol tabs.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Events] [Queues] [Settings]                         |
+--------------------------------------------------------------------------------------------------+
| Actions: /protocol show   /protocol runs   /logs run   /protocol feedback   /protocol quality    |
+-------------------------+------------------------------------------+------------------------------+
| Protocols               | Chat / Transcript                        | Protocol 88                  |
|                         |                                          | 0042-auth                    |
| > 0042-auth             | You> continue protocol 88 and summarize  | status: running              |
|   0041-queue-fix        |                                          | steps: 12                    |
|   0039-ci-cleanup       | Agent> Protocol 88 resumed. One step     | failed qa: 1                 |
|                         |        needs QA and one clarification     | last run: 6d31d2a            |
| Saved Views             |        is pending.                        |                              |
| * Running               |                                          | tabs: summary steps runs     |
| * Needs QA              | [event] step_qa_failed step=331          |       logs quality           |
| * Needs feedback        | [tool ] fetched quality and artifacts    |       policy clarify spec    |
|                         |                                          |       artifacts feedback     |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=protocols | protocol=88 | focus=chat | inspector=quality | refresh=live               |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/protocol show 88`
- `/protocol runs 88`
- `/protocol logs 88`
- `/protocol quality 88`
- `/protocol policy 88`
- `/protocol clarify 88`
- `/protocol feedback 88`
- `/protocol artifacts 88`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: protocol tab handling, command dispatch, selection syncing
- `tui-rs/src/state.rs`: protocol detail tabs, protocol summary state
- `tui-rs/src/api.rs`: add protocol feedback, runs, artifact, quality, policy, clarification endpoints
- `tui-rs/src/models.rs`: add protocol detail and protocol summary models
- `tui-rs/src/ui.rs`: keep shell and move protocol rendering into a feature module

Suggested new Rust files:

- `tui-rs/src/ui/flows/protocol_detail.rs`
- `tui-rs/src/ui/inspector.rs`
- `tui-rs/src/ui/results.rs`

State additions:

- `protocol_workspace_tab`
- `protocol_summary`
- `protocol_runs`
- `protocol_artifacts`
- `protocol_feedback`
- `protocol_quality`
- `protocol_policy`
- `protocol_clarifications`

Done when:

- protocol selection drives a rich inspector
- runs, logs, quality, policy, and artifacts are navigable without page hopping
- feedback and clarifications can be submitted from the TUI

