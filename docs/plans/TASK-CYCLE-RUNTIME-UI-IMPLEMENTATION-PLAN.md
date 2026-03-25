# Task Cycle Runtime UI Implementation Plan

> Status: Proposed
> Scope: unify task-cycle stage status, active agents, Windmill execution detail, and stage artifacts into one user-facing runtime experience
> Last updated: 2026-03-20
> Source inputs: `docs/DevGodzilla/BROWNFIELD-WORKFLOW.md`, `docs/DevGodzilla/task-cycle-flow.md`, `docs/DevGodzilla/CONTEXT-BUILDER-FLOW.md`

## Goal

Make the brownfield/task-cycle experience understandable from the user perspective without requiring the user to mentally join:

- the task-cycle board
- the protocol DAG
- raw Windmill runs
- backend events
- artifact file paths

The user should be able to answer, for any work item:

1. what is happening now
2. which agent is working
3. which stage is active
4. what artifacts have been produced
5. what is blocking progress

## Current Gap

Today the UI has two separate mental models:

- `Task Cycle` shows work-item status and manual actions
- `Workflow` shows protocol DAG and step state

That split is technically understandable but poor as a product surface. A user should not need to interpret low-level protocol steps just to understand where a work item is in its lifecycle.

## Product Principle

Default UI should be business-stage first.

Technical execution detail should still exist, but as secondary drill-down:

- primary: `Build Context`, `Implement`, `Review`, `QA`, `PR Ready`
- secondary: Windmill flow/module, raw step state, run IDs, logs

## User Experience

### Primary surface

Keep one primary `Task Cycle` board per project.

Each work-item card should show:

- title
- overall state
- active stage
- active agent or owner
- latest completed stage
- latest artifact summary
- blocking reason if present
- protocol link for advanced detail

### Work-item runtime drawer

Clicking a work item should open a runtime drawer or side panel.

The runtime drawer should have these sections:

- `Overview`
  - current stage
  - overall status
  - owner agent
  - active agents
  - iteration count
  - blocking clarifications
  - policy findings
- `Stage Timeline`
  - ordered business stages
  - status for each stage
  - started/finished timestamps
  - short summary
- `Artifacts`
  - grouped by stage
  - open artifact content inline
- `Live Activity`
  - stage events
  - agent assignment
  - Windmill execution updates
- `Technical Detail`
  - protocol id
  - step id
  - Windmill flow id
  - Windmill job id
  - raw run links

### Advanced view

Keep DAG/protocol visualization as an advanced view or secondary tab inside the same runtime surface.

Users who want orchestration detail can inspect it, but the default runtime story stays work-item centric.

## UX States

Each stage should support:

- `pending`
- `running`
- `completed`
- `failed`
- `blocked`
- `waiting_for_clarification`
- `skipped`

The UI should avoid fake percentage progress. Prefer discrete stage progress and timestamps over imprecise percent bars.

## Deep Context Reuse

The context stage should support three visible modes:

- `fresh_context`
- `reuse_baseline_context`
- `incremental_context_refresh`

This allows epic-level deep context to be reused across follow-up work items while still showing the user what was actually refreshed.

The runtime drawer should make this explicit, for example:

- `Using epic baseline context`
- `Refreshing contracts in touched module`
- `Rebuilt test surface for impacted files`

## Backend Contract

Do not make the frontend reconstruct runtime state by joining:

- work item
- step runs
- job runs
- event stream
- artifact refs

Add a backend projection endpoint:

- `GET /work-items/{id}/runtime`

### `WorkItemRuntimeOut`

Suggested response shape:

```json
{
  "work_item": {},
  "active_stage": "build_context",
  "active_stage_status": "running",
  "progress_summary": "Building code-first context pack",
  "blocking_reasons": [],
  "active_agents": [
    {
      "agent_id": "context_builder",
      "role": "context_builder",
      "status": "running"
    }
  ],
  "stage_runs": [],
  "latest_artifacts": [],
  "windmill": {
    "flow_id": "f/devgodzilla/brownfield_feature",
    "job_id": "abc123",
    "module_id": "get_task_cycle"
  }
}
```

### `StageRunOut`

Suggested fields:

- `stage_id`
- `stage_name`
- `order`
- `status`
- `mode`
- `summary`
- `started_at`
- `finished_at`
- `agent_assignments`
- `artifacts`
- `blocking_reasons`
- `windmill_job_id`
- `windmill_module_id`
- `run_ids`

### Artifact projection

Artifacts should be projected by stage, not only exposed as raw file refs.

Suggested stage artifact groups:

- `context`
  - `context_pack.json`
  - `context_pack.md`
- `implement`
  - step artifacts
  - changed-files summary
  - diff summary if available
- `review`
  - `review_report.json`
  - `review_report.md`
- `qa`
  - `test_report.json`
  - `test_report.md`
- `rework`
  - `rework_pack.json`

## Events

The runtime projection should be driven by stable work-item events, not only low-level system events.

Add or standardize event types such as:

- `work_item_stage_started`
- `work_item_stage_completed`
- `work_item_stage_failed`
- `work_item_stage_blocked`
- `work_item_agent_assigned`
- `work_item_artifact_created`
- `work_item_clarification_opened`
- `work_item_clarification_resolved`
- `work_item_context_reused`
- `work_item_context_refreshed`

Each event should carry:

- `project_id`
- `protocol_run_id`
- `step_run_id`
- `work_item_id`
- `stage_id`
- `agent_id` when relevant
- `artifact_key` when relevant
- `windmill_job_id` when relevant
- concise human-readable message

## Storage Strategy

V1 should avoid adding a full new table if the projection can be assembled from:

- `step.runtime_state`
- `job_runs`
- event stream
- artifact refs

However, stage state should still be stored explicitly enough that the backend can serve a stable aggregate without heavy frontend inference.

Recommended v1 storage:

- keep canonical projection source in `step.runtime_state.task_cycle`
- add a `runtime` subsection for stage runs and active agents
- derive Windmill linkage from `job_runs`
- derive artifact status from known task-cycle artifact paths

## Frontend Changes

### Existing files to update

- `frontend/app/projects/[id]/components/task-cycle-tab.tsx`
- `frontend/app/projects/[id]/components/workflow-tab.tsx`
- `frontend/components/workflow/pipeline-visualizer.tsx`
- `frontend/lib/api/types.ts`
- `frontend/lib/api/hooks/use-projects.ts`
- `frontend/lib/api/hooks/use-events.ts`

### New frontend files

- `frontend/components/workflow/work-item-runtime-drawer.tsx`
- `frontend/components/workflow/work-item-stage-timeline.tsx`
- `frontend/components/workflow/work-item-artifacts-panel.tsx`
- `frontend/components/workflow/work-item-live-activity.tsx`
- `frontend/components/workflow/agent-activity-badges.tsx`

### UI behavior

The board should:

- display `active_stage`
- display active agents inline
- surface latest artifact per stage
- show blocking reason inline
- open runtime drawer on card click
- support stage-specific actions only where valid

The drawer should:

- poll or subscribe to SSE while open
- invalidate runtime queries on relevant work-item events
- let the user open artifacts inline
- expose advanced runner detail in a collapsed section

## Backend Changes

### Existing files to update

- `devgodzilla/api/routes/brownfield.py`
- `devgodzilla/api/schemas.py`
- `devgodzilla/services/task_cycle.py`
- `devgodzilla/api/routes/events.py`
- `devgodzilla/services/event_persistence.py`
- `devgodzilla/services/orchestrator.py`

### New backend endpoints

- `GET /work-items/{id}/runtime`
- optional: `GET /work-items/{id}/events`
- optional: `GET /work-items/{id}/artifacts`

### Backend responsibilities

- compute current business stage
- map technical runs to business stages
- expose active agents
- project artifacts by stage
- emit stable work-item events
- preserve Windmill linkage as advanced metadata

## Stage Mapping

Suggested business stages:

1. `build_context`
2. `implement`
3. `review`
4. `qa`
5. `pr_ready`

Suggested mapping rules:

- `build_context` ends when `context_pack.json` exists and context stage passes sufficiency gate
- `implement` ends when execution completes and implementation artifacts exist
- `review` ends when review report is generated
- `qa` ends when QA report is generated
- `pr_ready` is terminal when review and QA passed and blocking clarifications/policies are resolved

## Failure And Blocking Rules

The runtime projection should distinguish:

- `failed`
  - stage execution failed
- `blocked`
  - stage cannot proceed because of policy, clarification, or dependency
- `waiting`
  - pending external action or queued runner

The UI should show the exact reason, not only a generic red state.

## Rollout Plan

### Phase 1

- add `active_stage` and `blocking_reason` to work-item list
- add `latest_artifact` summary
- add active agent display

### Phase 2

- add `GET /work-items/{id}/runtime`
- implement runtime drawer
- add stage timeline and artifact grouping

### Phase 3

- add work-item stage events
- add live activity feed in runtime drawer
- embed advanced DAG detail into same runtime surface

### Phase 4

- support context reuse modes
- show baseline-context reuse vs incremental refresh in UI

## Acceptance Criteria

- a user can tell the current work-item stage in under 5 seconds
- a user can tell which agent is active without opening logs
- a user can open the latest artifact for the active or last completed stage
- a user can tell whether the system is blocked, failed, or just waiting
- a user can inspect Windmill execution detail without it dominating the default workflow view

## Non-Goals

- replacing Windmill with a separate runner
- exposing every raw low-level event by default
- exact percentage progress calculation
- adding first-class multi-lane scheduling to the main runtime UI in v1
