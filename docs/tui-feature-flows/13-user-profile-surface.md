# User Profile Surface

Date: 2026-03-26

## Goal

Add a lightweight user/profile area for identity, tokens, activity, and personal preferences.

## Primary User Flow

1. User opens `Settings` and switches to `Profile`.
2. Center pane explains current identity and activity summary.
3. Right inspector shows token, session, and preference details.
4. User updates local preferences or checks recent activity.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Runs] [Events] [Queues] [Settings]                 |
+--------------------------------------------------------------------------------------------------+
| Actions: /profile show   /profile activity   /config tokens   /config theme                      |
+-------------------------+------------------------------------------+------------------------------+
| Settings                | Chat / Transcript                        | Profile                      |
|                         |                                          |                              |
| > Profile               | You> /profile show                       | user: sergei                 |
|   Tokens                |                                          | api token: configured        |
|   Preferences           | Agent> Loaded local profile settings and | project token: configured    |
|   Activity              |        recent TUI activity.              | theme: default               |
|                         |                                          | session: current             |
|                         | [tool ] activity loaded                  |                              |
|                         |                                          | tabs: summary activity       |
|                         |                                          |       tokens preferences     |
+-------------------------+------------------------------------------+------------------------------+
| Status: mode=settings | section=profile | identity=sergei | session=current                         |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/profile show`
- `/profile activity`
- `/config tokens`
- `/config theme`

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: settings and profile command routing
- `tui-rs/src/state.rs`: profile state
- `tui-rs/src/ui.rs`: expand settings into sub-sections

Suggested new Rust files:

- `tui-rs/src/ui/flows/profile.rs`

State additions:

- `profile_summary`
- `profile_activity`
- `preferences`

Done when:

- settings is more than token configuration
- the user can inspect activity and preferences in the TUI
- profile remains lightweight and does not block core operator work

