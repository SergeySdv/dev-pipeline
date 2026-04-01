# Policy Pack Management

Date: 2026-03-26

## Goal

Add governance management for policy pack listing, creation, detail inspection, and effective policy snapshots on projects and protocols.

## Primary User Flow

1. User opens `Policy` or runs `/policy packs`.
2. Center pane explains selected pack or effective policy.
3. Right inspector shows pack contents, assignments, and impacted projects or protocols.
4. User creates or updates assignments through commands and overlays.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Runs] [Quality] [Policy] [Settings]                |
+--------------------------------------------------------------------------------------------------+
| Actions: /policy packs   /policy show   /policy create   /policy assign                          |
+-------------------------+------------------------------------------+------------------------------+
| Policy Packs            | Chat / Transcript                        | Policy Pack strict-default   |
|                         |                                          |                              |
| > strict-default        | You> /policy show strict-default         | rules: 14                    |
|   relaxed-review        |                                          | assigned projects: 8         |
|   onboarding-default    | Agent> Loaded policy pack strict-default | assigned protocols: 3        |
|                         |        and effective assignments.        | version: 5                   |
| Effective Policy        |                                          |                              |
| > project 12            | [tool ] fetched pack and project usage   | tabs: summary rules          |
|   protocol 88           |                                          |       assignments history    |
|                         |                                          |                              |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=policy | selected_pack=strict-default | scope=project12                               |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/policy packs`
- `/policy show strict-default`
- `/policy create strict-default`
- `/policy assign project 12 strict-default`
- `/policy assign protocol 88 strict-default`
- `/project policy 12`
- `/protocol policy 88`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: policy commands and page routing
- `tui-rs/src/state.rs`: packs, effective policy selection
- `tui-rs/src/api.rs`: add pack listing/detail/create/assign endpoints
- `tui-rs/src/models.rs`: add policy pack models
- `tui-rs/src/ui.rs`: add `Policy` page or tab

Suggested new Rust files:

- `tui-rs/src/ui/flows/policy.rs`
- `tui-rs/src/ui/overlays.rs`

State additions:

- `policy_packs`
- `policy_pack_index`
- `policy_pack_detail`
- `effective_policy_scope`

Done when:

- policy packs are visible and manageable from the TUI
- project and protocol policy snapshots share the same renderer
- assignment changes do not require the web UI

