# TUI UX Improvement Plan

We will iterate in three phases to make the Textual dashboard more usable and CodeMachine-like.

## Phase 1 – Layout and bindings
- Adopt docked header/footer and a grid for three columns; keep headers visible.
- Split global vs contextual bindings: keep global priority for quit/help/refresh; move step actions onto the steps pane with `show=True` for footer hints; add focus cycling (tab/shift+tab) and escape/back per pane.
- Add a help modal/command palette bound to `?`/`h` that lists active bindings; hide noisy defaults.
- Improve selection highlighting and status pills; ensure events are limited and readable.

## Phase 2 – Contextual modals and actions
- Steps pane: `enter` opens a contextual action menu (run next, retry latest, run QA, approve, open PR) with confirmations for destructive actions.
- CodeMachine import modal: pre-fill base branch from protocol, validate path, choose enqueue vs inline.
- Add modal to set/update project token and API base from within the TUI (no env edit needed).
- Add toast/status bar for action results; keep loader non-blocking and disable auto-refresh during modals.

## Phase 3 – Event/status polish and filters
- Protocol detail pane (description, branch, status, updated_at, counts) under protocols.
- Steps pane filters (by status) and “QA latest” shortcut when pending.
- Events: group by type, limit to recent N, expandable metadata on keypress.
- Error banners for API failures (401/404/unreachable) with retry hints; keep TUI running.
- Update docs with keybindings, screenshots/GIF, and troubleshooting (API down, tokens, non-TTY).
