# Brownfield Task Cycle Feature Validation Checklist

Use this checklist to validate the task-cycle implementation before shipping.

## Product Flow

- [ ] There is one visible primary entry point for brownfield delivery.
- [ ] The entry point asks for project or repo, feature request, and output mode.
- [ ] The UI does not force the user through separate SpecKit, plan, and protocol wizards for the common path.
- [ ] `task_cycle` is an `output_mode` branch inside `brownfield_feature`, not a separate user-facing intake flow.
- [ ] The work-item loop in the UI matches [task-cycle-flow.md](../DevGodzilla/task-cycle-flow.md).
- [ ] [task-cycle-flow.md](../DevGodzilla/task-cycle-flow.md) is treated as the default v1 task-cycle reference until a future flow manager exists.

## Context Builder

- [ ] A `ContextPack` artifact is created before implementation begins.
- [ ] `ContextPack` is persisted as both `context_pack.json` and `context_pack.md`.
- [ ] `context_pack.json` includes `work_item_id`, `project_id`, `protocol_run_id`, `step_run_id`, goal, acceptance criteria, entry points, required files, contracts, types, schemas, test commands, review focus, and risk notes.
- [ ] `context_pack.json` also captures project manifests and style-guide references needed by review and QA.
- [ ] File references in `ContextPack` are curated and reusable by downstream agents, not just raw logs.
- [ ] The system can detect insufficient context and request clarification or deeper tracing.
- [ ] For brownfield repos, the context path is code-first, not spec-first.
- [ ] Work-item artifacts are stored under the project temp folder in per-task subfolders.

## Backend Contract

- [ ] There is a stable intent-level API for starting brownfield task-cycle runs.
- [ ] Work-item state is available through API without exposing raw protocol internals as the primary contract.
- [ ] In v1, work items are projected from existing `step_runs` with a stable identity mapping.
- [ ] Work-item state includes context, review, QA, owner, helper-agent summary, and PR-ready fields.
- [ ] Work-item state includes a canonical task folder path and artifact references.
- [ ] Blocking clarifications stop execution cleanly.
- [ ] Policy findings can block or warn according to enforcement mode.

## Execution Model

- [ ] Single-owner work-items can be assigned and executed.
- [ ] A single `owner_agent` is accountable for each work item.
- [ ] Helper agents may run bounded parallel subtasks under the owner without creating first-class workflow lanes.
- [ ] Review failure returns the work-item to rework.
- [ ] QA failure returns the work-item to rework.
- [ ] Successful review and QA can mark the work-item `PR-ready`.

## Agent Handoffs

- [ ] `context_builder` writes reusable artifacts, not only logs.
- [ ] `dev` consumes `context_pack.json` as the primary machine-readable contract.
- [ ] `review` is a dedicated stage in the flow with a separate review agent.
- [ ] `review` consumes the `ContextPack`, current diff or artifacts, project manifests, and project style-guide references.
- [ ] `test` consumes the `ContextPack`, diff, and exact test commands.
- [ ] Rework feedback is stored as a structured artifact, not only as free text in logs.

## Windmill

- [ ] `brownfield_feature` can branch into `task_cycle`.
- [ ] The task-cycle branch is part of the same user-facing intake flow.
- [ ] Windmill scripts remain thin API adapters.
- [ ] Flow runs and job runs are visible through existing API passthrough endpoints.
- [ ] Operator actions in Windmill are named according to business meaning, not raw internal step verbs.

## Next.js UI

- [ ] The project page shows task-cycle progress as work-items, not only protocol steps.
- [ ] The work-item UI is a higher-level projection over existing `step_runs`.
- [ ] The user can see owner, helper-agent activity summary, status, review state, QA state, and PR-ready state.
- [ ] The user can open the latest context, review, and test artifacts from the UI.
- [ ] The user can see the task folder path and reusable artifact links for the current work item.
- [ ] The user can trigger implement, review, QA, and mark PR-ready actions from the UI.
- [ ] Empty states explain the next useful action.

## Windmill Apps

- [ ] Windmill project detail has a first-class `Task Cycle` or `Feature Delivery` tab.
- [ ] Windmill protocol detail actions are semantically correct.
- [ ] No button labeled `Start` actually runs a raw step action by mistake.

## Testing

- [ ] Backend unit tests cover context creation, work-item transitions, and rework loops.
- [ ] Windmill workflow tests cover the `task_cycle` branch.
- [ ] Frontend tests cover task-cycle board rendering and actions.
- [ ] Property or transition tests cover invalid state transitions.
- [ ] Manual test verifies one complete brownfield feature from intake to PR-ready.

## Manual End-to-End Scenario

- [ ] Start from an existing project.
- [ ] Enter one brownfield feature request.
- [ ] Generate work-items.
- [ ] Build `context_pack.json` and `context_pack.md` for the first work-item.
- [ ] Run a `dev` implementation cycle.
- [ ] Run `review`.
- [ ] Verify the review agent uses manifests, style-guide references, and test commands from `context_pack.json`.
- [ ] Force one review failure and verify rework loop.
- [ ] Run `test`.
- [ ] Force one QA failure and verify rework loop.
- [ ] Reach `PR-ready`.

## Deferred Phase 2

- [ ] First-class parallel work-items honor `parallel_group`.
- [ ] Parallel execution respects configured `cap_n`.
- [ ] Dependency ordering respects `depends_on` across independently scheduled lanes.
- [ ] An `integrator` role exists only when multiple first-class lanes are actually implemented.

## Release Readiness

- [ ] Docs are updated in `docs/DevGodzilla/`.
- [ ] No route, flow, or UI label still uses the old fragmented journey as the recommended path.
- [ ] New artifacts and APIs are included in `openapi.json` and tested.
- [ ] Basic `PR-ready` criteria are implemented and visible in the work-item contract.
- [ ] Rollout can be gated by a feature flag if needed.
