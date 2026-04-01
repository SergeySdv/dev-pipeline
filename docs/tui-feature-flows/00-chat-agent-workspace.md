# Chat Agent Workspace

Date: 2026-03-31

## Goal

Add a default `Chat` workspace where the operator and agent talk in one transcript, the agent can launch existing local flows, and both sides can see live flow progress without leaving the shell.

This page becomes the primary entrypoint for the TUI. All other pages stay available, but `Chat` is the first surface and the control center.

## Primary User Flow

1. User opens the default `Chat` tab.
2. User selects or confirms a project, protocol, and agent context from the left navigator.
3. User types a plain-language request such as `continue brownfield flow for api-core` or uses a slash command like `/flow run brownfield`.
4. The agent decides whether to answer directly, inspect the repo, or start an existing flow.
5. The center transcript shows normal chat messages plus flow lifecycle blocks:
   `queued`, `starting`, `running`, `waiting_input`, `step_complete`, `failed`, `completed`.
6. The right inspector shows the current run, current step, selected agent, and available actions.
7. The lower-right results pane shows tool output, logs, artifact links, and validation summaries for the active run.
8. User can interrupt, clarify, resume, retry, approve, or switch focus without losing transcript context.

## UI Mockup

```text
+--------------------------------------------------------------------------------------------------+
| Tabs: [Chat] [Projects] [Protocols] [Steps] [Runs] [Quality] [Policy] [Agents] [Events] [Queues]|
+--------------------------------------------------------------------------------------------------+
| Actions: /agent use   /flow run   /flow resume   /step show   /logs run   /tool list   /search  |
+-------------------------+------------------------------------------+------------------------------+
| Context / Navigator     | Chat / Transcript                        | Active Flow                  |
|                         |                                          |                              |
| Project                 | You> continue brownfield flow for        | run: brownfield-20260331-01  |
| > api-core              |      api-core and use codex              | status: running              |
|   billing               |                                          | agent: codex                 |
|                         | Agent> I loaded project api-core and     | flow: brownfield_feature     |
| Agent                   |        selected the brownfield flow.     | step: inspect repo           |
| > codex                 |        I am starting repo inspection     | started: 20:14               |
|   opencode              |        and context build.                |                              |
|   claude-code           |                                          | tabs: summary steps logs     |
|                         | [flow ] brownfield_feature queued        |       tools artifacts        |
| Saved Flows             | [flow ] inspect_repo started             |                              |
| * brownfield_feature    | [tool ] rg --files src tests docs        +------------------------------+
| * protocol_execute      | [flow ] inspect_repo completed           | Results / Logs               |
| * qa_repair             | [flow ] clarify_requirements waiting     |                              |
|                         |                                          | rg --files src tests docs    |
|                         | Agent> I found two unclear contracts.    | src/api/app.py               |
|                         |        Do you want me to continue with   | src/services/policy.py       |
|                         |        the current assumptions?          | tests/test_api.py            |
|                         |                                          |                              |
|                         | You> yes, continue                       | artifact: context-pack.json  |
+-------------------------+------------------------------------------+------------------------------+
| Composer: message or /command...                                                            [Enter]|
+--------------------------------------------------------------------------------------------------+
| Status: connected | mode=chat | project=api-core | agent=codex | flow=running | refresh=live    |
+--------------------------------------------------------------------------------------------------+
```

## Command Surface

- `/agent use codex`
- `/agent show codex`
- `/flow list`
- `/flow run brownfield_feature`
- `/flow run protocol_execute --protocol 88`
- `/flow resume <run_id>`
- `/flow cancel <run_id>`
- `/flow retry <run_id>`
- `/flow use-tool <tool_name>`
- `/step show <id>`
- `/run show <run_id>`
- `/logs run <run_id>`

## Chat Semantics

- Plain messages are the default interaction mode.
- The agent may autonomously choose an existing flow when the request matches a known workflow.
- Flow events must be rendered inline in the transcript rather than only in a side panel.
- Tool execution must also be visible inline, but in compact blocks.
- User clarifications must pause the flow cleanly and resume the same run after an answer.

Recommended transcript block types:

- `You>`: operator message
- `Agent>`: natural-language response
- `[flow ]`: flow lifecycle event
- `[step ]`: current workflow step update
- `[tool ]`: executed tool or shell command
- `[check]`: validation result
- `[warn ]`: policy, approval, or failure notice

## Existing Flow Mapping

This page should run the flows already modeled by the product rather than inventing a second workflow system in the UI.

Initial flow targets:

- brownfield / context-builder journey
- protocol start / resume / step execution
- specification workflow actions
- QA / approve / retry loops
- agent test and targeted utility flows

The `Chat` tab is the conversational front-end for these flows. The underlying entities stay `project`, `protocol`, `step`, and `run`.

## Implementation Notes

Existing Rust files:

- `tui-rs/src/app.rs`: command dispatch, chat submit, run actions, flow lifecycle updates
- `tui-rs/src/state.rs`: chat transcript state, active flow state, composer state, pinned context
- `tui-rs/src/api.rs`: start/resume/cancel/retry run endpoints, agent/tool capability fetches
- `tui-rs/src/models.rs`: chat event, flow event, tool event, active run DTOs
- `tui-rs/src/ui.rs`: shell and tab wiring for the new default page

Suggested new Rust files:

- `tui-rs/src/ui/chat.rs`
- `tui-rs/src/ui/flows/chat_agent.rs`
- `tui-rs/src/ui/composer.rs`
- `tui-rs/src/app/chat.rs`
- `tui-rs/src/app/flows.rs`

State additions:

- `chat_messages`
- `composer_input`
- `active_chat_agent`
- `active_flow_run`
- `active_flow_step`
- `flow_event_buffer`
- `tool_event_buffer`
- `chat_context_scope`
- `pending_user_question`

## Done When

- `Chat` is the first and default page in the shell
- user can talk to an agent without switching to another page
- the agent can start and resume existing flows from the chat surface
- transcript shows flow and tool progress live
- the same run is inspectable in the right pane and reusable from `Runs`
- flow pauses for user input and resumes in-place
- chat remains useful even when no flow is running
