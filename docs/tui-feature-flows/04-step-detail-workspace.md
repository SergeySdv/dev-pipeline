# Step Detail Workspace

Date: 2026-03-26

## Goal

Add a step investigation surface with runtime state, rerun actions, step run history, artifacts, policy findings, quality results, and engine/model/agent details.

## Primary User Flow

1. User selects a step from a protocol or asks the agent to inspect a failed step.
2. The transcript explains why the step matters and suggests actions.
3. The right inspector switches to the selected step.
4. The lower-right pane can stream the chosen run log or show QA results.
5. User triggers `run`, `qa`, or `approve` from commands or quick actions.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Events] [Queues] [Settings]                         |
+--------------------------------------------------------------------------------------------------+
| Actions: /step show   /step run   /step qa   /step approve   /step artifacts                     |
+-------------------------+------------------------------------------+------------------------------+
| Steps                   | Chat / Transcript                        | Step 331                     |
|                         |                                          | Implement auth middleware    |
| > #331 needs_qa         | You> review latest failed step           | status: needs_qa             |
|   #330 done             |                                          | engine: opencode             |
|   #329 done             | Agent> Step 331 failed on policy gate    | model: glm-4.6               |
|                         |        P-4. I loaded findings and        | agent: codex                 |
| Filters                 |        latest run metadata on the right. | latest run: 6d31d2a          |
| [needs_qa] [failed]     |                                          |                              |
|                         | [tool ] fetched run and artifact list    | tabs: summary runs           |
|                         | [warn ] policy finding P-4               |       artifacts quality      |
|                         |                                          |       policy runtime         |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=steps | protocol=88 | step=331 | focus=inspector | refresh=manual               |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/step show 331`
- `/step run 331`
- `/step qa 331`
- `/step approve 331`
- `/step artifacts 331`
- `/step runs 331`
- `/step runtime 331`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: step commands and selection focus
- `tui-rs/src/state.rs`: selected step details, step run history
- `tui-rs/src/api.rs`: add step detail, step runs, artifacts, quality, policy endpoints
- `tui-rs/src/models.rs`: add step detail DTOs

Suggested new Rust files:

- `tui-rs/src/ui/flows/step_detail.rs`
- `tui-rs/src/ui/inspector.rs`

State additions:

- `step_detail`
- `step_runs`
- `step_artifacts`
- `step_quality`
- `step_policy`
- `step_runtime`

Done when:

- selecting a step opens more than a flat list row
- step investigation can happen entirely inside the shell
- run, QA, and approval actions stay near the visible evidence

