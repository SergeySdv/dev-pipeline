# Filtering And Search

Date: 2026-03-26

## Goal

Add broad search and scoped filtering across projects, protocols, specifications, events, queues, and clarifications.

## Primary User Flow

1. User presses `/` or `Ctrl+K`.
2. An overlay or inline composer switches into search mode.
3. Results update left navigator, center list, or inspector context depending on scope.
4. User pins a result and continues chatting without losing state.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Runs] [Events] [Queues] [Settings]                 |
+--------------------------------------------------------------------------------------------------+
| Actions: /search projects   /search protocols   /search events   /filter saved                   |
+-------------------------+------------------------------------------+------------------------------+
| Navigator               | Chat / Search                            | Inspector                    |
|                         |                                          |                              |
| Filters                 | /search protocols auth qa                | Search Results               |
| scope: protocols        |                                          | 1. 0042-auth                 |
| status: running         | Agent> Found 3 protocols matching        | 2. 0049-auth-cleanup         |
| project: api-core       |        "auth" and "qa".                 | 3. protocol 88 event stream  |
|                         |                                          |                              |
| Saved Filters           | [tool ] query applied                    | tabs: results preview        |
| > auth failures         |                                          |                              |
|   active projects       |                                          |                              |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=search | scope=protocols | query="auth qa" | results=3                                 |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/search projects api`
- `/search protocols auth`
- `/search events qa_failed`
- `/filter save auth_failures`
- `/filter use auth_failures`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: global search and filter key handling
- `tui-rs/src/state.rs`: scoped filters, saved presets, query state
- `tui-rs/src/api.rs`: add server-backed search where available
- `tui-rs/src/ui.rs`: search composer and result rendering

Suggested new Rust files:

- `tui-rs/src/ui/overlays.rs`
- `tui-rs/src/ui/flows/search.rs`

State additions:

- `global_query`
- `search_scope`
- `saved_filters`
- `search_results`

Done when:

- any major resource can be filtered without manual list scanning
- saved filters are reusable across sessions
- search is a first-class keyboard workflow

