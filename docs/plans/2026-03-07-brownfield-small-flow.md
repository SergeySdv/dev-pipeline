# Brownfield Small Flow

## Why this exists

The current journey exposes too many internal orchestration concepts to the operator:

- project onboarding is separate from feature delivery
- SpecKit generation is split across multiple wizard steps
- protocol creation is a separate mental model after tasks already exist
- Windmill apps and the Next.js console both surface overlapping project/protocol controls

For a small brownfield change, the operator usually wants one narrow path:

1. pick an existing project
2. describe the requested change
3. review generated plan and tasks
4. hand off either to backlog/tasks or to a planned execution protocol

## Current friction in the repo

- The main project page exposes multiple parallel entry points and tabs for spec, workflow, onboarding, execution, and settings instead of one primary delivery path: `frontend/app/projects/[id]/page.tsx`
- The SpecKit workflow component shows eight visible stages, many of which are implementation details rather than user decisions: `frontend/components/speckit/spec-workflow.tsx`
- The implementation wizard chains clarify, checklist, analysis, implement, sprint import, and protocol creation in one modal, which is powerful but too heavy for a small brownfield request: `frontend/components/wizards/implement-feature-wizard.tsx`
- Windmill already ships long serial flows that mirror every internal phase, especially `spec_to_tasks.flow.json`, `spec_to_protocol.flow.json`, and `onboard_to_tasks.flow.json`: `windmill/flows/devgodzilla/`
- The protocol wizard is mostly placeholder UI and adds another layer of abstraction instead of simplifying entry into execution: `frontend/components/wizards/protocol-wizard.tsx`

## Proposed user journey

Use four operator-facing states:

1. `Context`
   Refresh repo/spec context only when needed.
2. `Intent`
   Capture the feature request and optional clarification answers.
3. `Plan`
   Produce spec, plan, tasks, and optional analysis/checklist.
4. `Handoff`
   Stop at tasks or create a planned protocol.

This keeps the UI contract smaller:

- one launch form for brownfield work
- one progress view with four sections
- one result card showing generated artifacts and next action

## V1 execution contract

For implementation, keep `task_cycle` inside the same intake flow instead of creating a second user-facing flow.

- `brownfield_feature` remains the single entry point
- `output_mode` gains `task_cycle`
- the flow branches into the task-cycle loop when that mode is selected

For v1, a work item should be a higher-level view over the existing backend `step_runs` model, not a brand new top-level table:

- one work item maps to one `StepRun`
- the UI and API present `work_item` language
- the backend reuses existing step execution, artifact, and QA plumbing

Execution ownership should also stay simple in v1:

- one `owner_agent` is accountable for the work item
- the owner may spawn helper agents for bounded parallel subtasks
- helper agents are internal delegation, not first-class workflow lanes
- review, QA, and `PR-ready` run once on the consolidated result

Before coding starts, the flow should create a reusable context artifact pair:

- `context_pack.json` as the canonical machine-readable contract
- `context_pack.md` as the human-readable debug and operator view

Store work-item artifacts under the project temp folder in task-specific subfolders so they are easy to inspect and reuse:

- project temp root
- `task-cycle/`
- `task-cycle/work-items/<step_run_id>/`

That folder should contain at minimum:

- `context_pack.json`
- `context_pack.md`
- `review_report.json`
- `review_report.md`
- `test_report.json`
- `test_report.md`
- optional `rework_pack.json`

The JSON artifact should include at minimum:

- `work_item_id`
- `project_id`
- `protocol_run_id`
- `step_run_id`
- `title`
- `goal`
- `acceptance_criteria`
- `entry_points`
- `required_files`
- `contracts`
- `types`
- `schemas`
- `manifest_files`
- `style_guides`
- `test_commands`
- `review_focus`
- `risks`
- `assumptions`
- `artifact_refs`

The default v1 task-cycle reference should be:

- `docs/DevGodzilla/task-cycle-flow.md`

Later, a flow manager can be added to select or generate custom task-cycle variants, but v1 should not depend on that abstraction.

## New Windmill flow

New flow export: `windmill/flows/devgodzilla/brownfield_feature.flow.json`

It reuses existing API-wrapper scripts and keeps configuration intentionally small. `task_cycle` should be implemented as another `output_mode` branch inside this same flow:

- optional context refresh via `u/devgodzilla/project_onboard_api`
- spec generation via `u/devgodzilla/speckit_specify_api`
- optional clarification append via `u/devgodzilla/speckit_clarify_api`
- plan and tasks via `u/devgodzilla/speckit_plan_api` and `u/devgodzilla/speckit_tasks_api`
- optional checklist and analysis via `u/devgodzilla/speckit_checklist_api` and `u/devgodzilla/speckit_analyze_api`
- optional protocol handoff via `u/devgodzilla/protocol_from_spec_api`
- optional task-cycle branch over projected work items backed by `step_runs`

## Recommended UI/backend contract

The UI should call this flow with a compact payload:

```json
{
  "project_id": 42,
  "feature_request": "Add audit trail to invoice status changes",
  "feature_name": "invoice-audit-trail",
  "output_mode": "task_cycle",
  "run_discovery_agent": false,
  "clarification_entries": [],
  "clarification_notes": "",
  "run_analysis": true,
  "owner_agent": "dev",
  "allow_helper_agents": true
}
```

That contract is easier to explain than the current split across onboarding, SpecKit, protocol creation, and execution-specific screens.

## Basic v1 review and PR-ready rules

The task-cycle branch should include a dedicated `review` stage with a separate review agent.

The review agent should read:

- task details and current work-item status
- `context_pack.json`
- changed files and diff summary
- project manifests
- project style guides and conventions
- exact test commands

The review stage should produce:

- `review_report.json`
- `review_report.md`

Basic v1 `PR-ready` criteria should be:

- `context_pack.json` exists
- implementation finished successfully
- latest review passed or only contains non-blocking warnings
- latest QA passed
- no blocking clarifications remain open
- no blocking policy findings remain
- latest required artifacts are present and linked from the work item
