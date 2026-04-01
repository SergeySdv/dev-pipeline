# Specification Workflow

Date: 2026-03-26

## Goal

Bring the spec lifecycle into the TUI: init, generate, clarify, checklist, analyze, implement, create protocol, cleanup, and filtered spec listing.

## Primary User Flow

1. User selects a project and enters `Chat`.
2. User asks for spec work in natural language or with slash commands.
3. The center transcript narrates the workflow step-by-step.
4. The right inspector shows the current spec, run status, checklist, or review output.
5. The lower-right pane streams spec task results and cleanup actions.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Events] [Queues] [Settings]                         |
+--------------------------------------------------------------------------------------------------+
| Actions: /spec list   /spec init   /spec clarify   /spec analyze   /spec implement               |
+-------------------------+------------------------------------------+------------------------------+
| Context / Specs         | Chat / Transcript                        | Spec Inspector               |
|                         |                                          |                              |
| Project                 | You> /spec analyze 12 specs/0042-auth    | specs/0042-auth/spec.md      |
| > api-core              |                                          | status: analyzing            |
|                         | Agent> Analysis started for auth spec.   | review: pending              |
| Specs                   |        I pinned checklist and review     | checklist: 18 items          |
| > 0042-auth/spec.md     |        tabs on the right.                | last run: spec-run-31        |
|   0041-queue/spec.md    |                                          |                              |
|                         | [tool ] analysis job enqueued            | tabs: summary review         |
| Saved Views             | [event] spec_analysis_started            |       checklist history      |
| * Needs clarify         |                                          |                              |
| * Ready to implement    | You> /spec implement 12 specs/0042-auth  |                              |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=chat | project=12 | spec=0042-auth/spec.md | agent=codex | refresh=live               |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/spec list --project 12`
- `/spec init 12`
- `/spec generate 12 --title "auth"`
- `/spec clarify 12 specs/0042-auth/spec.md`
- `/spec checklist 12 specs/0042-auth/spec.md`
- `/spec analyze 12 specs/0042-auth/spec.md`
- `/spec implement 12 specs/0042-auth/spec.md`
- `/spec cleanup --project 12`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: add spec command family and modal or overlay hooks
- `tui-rs/src/state.rs`: active spec, spec tab, spec run state
- `tui-rs/src/api.rs`: add spec endpoints beyond audit
- `tui-rs/src/models.rs`: add spec list, spec run, checklist, clarify result types

Suggested new Rust files:

- `tui-rs/src/ui/flows/specs.rs`
- `tui-rs/src/ui/overlays.rs`
- `tui-rs/src/ui/results.rs`

State additions:

- `specs`
- `selected_spec`
- `spec_runs`
- `spec_review`
- `spec_checklist`
- `spec_filters`

Done when:

- specs are first-class objects in chat and inspector
- implement-from-spec can create or open a protocol
- cleanup and deep-link style navigation are exposed in commands

