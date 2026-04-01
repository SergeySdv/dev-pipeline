# Operations Coverage

Date: 2026-03-26

## Goal

Deepen the operations area with logs, metrics, richer event filtering, saved presets, refresh control, and searchable queue jobs.

## Primary User Flow

1. User opens `Events`, `Queues`, or `Ops`.
2. Top action bar exposes filters, tailing, and refresh actions.
3. Center pane remains explanatory and command-driven.
4. Right inspector shows details for the selected event, queue job, or metric card.
5. Lower-right pane handles live streaming logs.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Runs] [Events] [Queues] [Ops] [Settings]           |
+--------------------------------------------------------------------------------------------------+
| Actions: /logs app   /logs agents   /event tail   /queue jobs   /metrics show                    |
+-------------------------+------------------------------------------+------------------------------+
| Ops / Filters           | Chat / Transcript                        | Inspector                    |
|                         |                                          |                              |
| Event Presets           | You> /event tail --project 12 --qa       | Event stream                 |
| > QA failures           |                                          | source: protocol events      |
|   Agent errors          | Agent> Tailing QA-related events for     | refresh: 2s                  |
|   Queue backlog         |        project 12. App and agent logs    | filter: qa                   |
|                         |        are available as lower-right       |                              |
| Queue Filters           |        stream sources.                   | tabs: detail raw export      |
| [queued] [started]      |                                          |                              |
| [done] [failed]         | [event] qa_failed step=331               +------------------------------+
|                         |                                          | Live Logs                    |
|                         |                                          | [12:43] worker started       |
|                         |                                          | [12:43] qa failure emitted   |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=ops | preset=QA failures | refresh=2s | source=events+logs                            |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/event tail --project 12 --category qa`
- `/event preset use qa_failures`
- `/logs app`
- `/logs agents`
- `/logs run 6d31d2a`
- `/queue jobs --status started`
- `/metrics show`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: refresh timers, filter state, command routing
- `tui-rs/src/state.rs`: saved presets, active log source, refresh interval
- `tui-rs/src/api.rs`: add logs and metrics endpoints if available
- `tui-rs/src/models.rs`: add metric and log stream models
- `tui-rs/src/ui.rs`: add Ops tab or expand Events/Queues layout

Suggested new Rust files:

- `tui-rs/src/ui/flows/ops.rs`
- `tui-rs/src/ui/results.rs`
- `tui-rs/src/ui/event_detail.rs`

State additions:

- `ops_presets`
- `event_filters`
- `queue_filters`
- `refresh_interval`
- `log_stream_source`
- `metrics_snapshot`

Done when:

- events, queues, logs, and metrics feel like one coherent operational workspace
- the user can freeze, tail, filter, and resume streams
- queue jobs are searchable and selectable

