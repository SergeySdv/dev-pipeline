# Quality Dashboard

Date: 2026-03-26

## Goal

Expose global quality outcomes, gate summaries, recent findings, and review paths instead of limiting quality to step QA actions.

## Primary User Flow

1. User opens `Quality` or asks the agent for current failures.
2. Center pane summarizes the current quality picture.
3. Right inspector breaks down pass, warn, fail, and constitutional gate status.
4. Lower-right pane shows recent findings or linked runs.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Runs] [Quality] [Events] [Queues] [Settings]       |
+--------------------------------------------------------------------------------------------------+
| Actions: /quality show   /quality findings   /quality protocol 88   /quality step 331            |
+-------------------------+------------------------------------------+------------------------------+
| Quality Views            | Chat / Transcript                        | Quality Summary              |
|                          |                                          |                              |
| > Global                 | You> show me current quality failures    | pass: 42                     |
|   Project 12             |                                          | warn: 6                      |
|   Protocol 88            | Agent> Two warnings and one failure      | fail: 1                      |
|                          |        need review. The failed item      | constitutional: warn         |
| Gate Filters             |        is step 331 in protocol 88.       |                              |
| [pass] [warn] [fail]     |                                          | tabs: summary findings       |
| [constitutional]         | [warn ] quality finding gate=P-4         |       gates runs review      |
|                          | [tool ] opened protocol 88 on right      |                              |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=quality | filter=fail | selected=step331 | refresh=manual                              |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/quality show`
- `/quality findings --status fail`
- `/quality protocol 88`
- `/quality step 331`
- `/quality open-run 6d31d2a`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: quality command family and navigation
- `tui-rs/src/state.rs`: quality summary and filters
- `tui-rs/src/api.rs`: add quality dashboard and finding endpoints
- `tui-rs/src/models.rs`: add quality summary and finding models
- `tui-rs/src/ui.rs`: add `Quality` page or quality inspector tab

Suggested new Rust files:

- `tui-rs/src/ui/flows/quality.rs`

State additions:

- `quality_summary`
- `quality_findings`
- `quality_filters`
- `quality_scope`

Done when:

- quality can be reviewed as a first-class operational surface
- findings link cleanly to protocols, steps, and runs
- QA actions are contextualized by visible evidence

