# TUI Feature Flows

Date: 2026-03-26

Purpose:

- turn each gap from `docs/TUI-FEATURE-GAPS.md` into a Rust-first implementation flow
- anchor every flow to the shell and interaction rules in `docs/TUI-CHAT-DESIGN-STYLES.md`
- give `tui-rs` a concrete pre-coding spec pack

Shared assumptions:

- keep the current shell: top tabs, action bar, left navigator, center transcript, right inspector, lower-right results, bottom status
- use PI-style minimal chat rendering in the center pane
- make `Chat` the default page and primary control surface for flow execution
- implement everything in Rust under `tui-rs/`
- translate web UI forms into commands, pickers, overlays, and inspector tabs

Recommended implementation order:

1. [00 Chat Agent Workspace](./00-chat-agent-workspace.md)
2. [01 Project Detail Workspace](./01-project-detail-workspace.md)
3. [03 Protocol Detail Workspace](./03-protocol-detail-workspace.md)
4. [04 Step Detail Workspace](./04-step-detail-workspace.md)
5. [05 Runs Surface](./05-runs-surface.md)
6. [06 Operations Coverage](./06-operations-coverage.md)
7. [02 Specification Workflow](./02-specification-workflow.md)
8. [08 Quality Dashboard](./08-quality-dashboard.md)
9. [09 Policy Pack Management](./09-policy-pack-management.md)
10. [07 Agent Administration](./07-agent-administration.md)
11. [10 Project Lifecycle Actions](./10-project-lifecycle-actions.md)
12. [11 Filtering And Search](./11-filtering-and-search.md)
13. [12 External Navigation And Review Links](./12-external-navigation-and-review-links.md)
14. [13 User Profile Surface](./13-user-profile-surface.md)

Shared Rust files that nearly every feature will touch:

- `tui-rs/src/app.rs`
- `tui-rs/src/state.rs`
- `tui-rs/src/api.rs`
- `tui-rs/src/models.rs`
- `tui-rs/src/ui.rs`

Recommended UI module split before deeper feature work:

- `tui-rs/src/ui/chat.rs`
- `tui-rs/src/ui/navigator.rs`
- `tui-rs/src/ui/inspector.rs`
- `tui-rs/src/ui/results.rs`
- `tui-rs/src/ui/composer.rs`
- `tui-rs/src/ui/overlays.rs`
- `tui-rs/src/ui/flows/`
