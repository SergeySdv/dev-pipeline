# Brownfield Workflow

> Status: Active design direction, exported as `f/devgodzilla/brownfield_feature`
> Scope: Small brownfield project and feature-delivery journey
> Last updated: 2026-03-07

## Why this flow exists

The current DevGodzilla journey is split across multiple concepts:

- project onboarding
- SpecKit specification and clarification
- plan and task generation
- protocol creation and planning
- sprint synchronization

That separation matches internal architecture, but it is too heavy for a user who usually wants one simple outcome:

- understand the repo
- define one feature
- get either tasks, a runnable protocol, or a sprint-ready backlog

## Recommended customer journey

For a small brownfield feature, the UI and flow runner should ask only four things:

1. Which repo or existing project are we working on?
2. What customer outcome are we trying to deliver?
3. Do we only need tasks, or should DevGodzilla create an executable protocol?
4. Should the result land in an existing sprint or create a new sprint?

Everything else should stay optional and advanced:

- discovery
- clarifications
- checklist generation
- analysis report
- protocol overwrite behavior

## Windmill flow

The exported flow is:

- `f/devgodzilla/brownfield_feature`

Source file:

- `windmill/flows/devgodzilla/brownfield_feature.flow.json`

It reuses existing API-wrapper scripts instead of adding new backend orchestration:

- `windmill/scripts/devgodzilla/project_onboard_api.py`
- `windmill/scripts/devgodzilla/speckit_specify_api.py`
- `windmill/scripts/devgodzilla/speckit_clarify_api.py`
- `windmill/scripts/devgodzilla/speckit_plan_api.py`
- `windmill/scripts/devgodzilla/speckit_checklist_api.py`
- `windmill/scripts/devgodzilla/speckit_tasks_api.py`
- `windmill/scripts/devgodzilla/speckit_analyze_api.py`
- `windmill/scripts/devgodzilla/protocol_from_spec_api.py`
- `windmill/scripts/devgodzilla/protocol_plan_and_wait.py`
- `windmill/scripts/devgodzilla/sync_tasks_api.py`
- `windmill/scripts/devgodzilla/sprint_from_protocol_api.py`

## Flow shape

Base path:

1. onboard existing or new project
2. generate spec
3. optionally apply clarifications
4. generate plan
5. optionally generate checklist
6. generate tasks
7. optionally generate analysis

Delivery branch:

- `tasks_only`
- `tasks_to_sprint`
- `protocol`
- `protocol_to_sprint`

This keeps one entry point while still supporting the most common brownfield outcomes.

## What to simplify in UI next

The frontend should stop exposing separate wizards for each internal artifact stage when the user intent is feature delivery.

Recommended replacement:

- one "Brownfield Feature" entry point
- step 1: repo/project
- step 2: feature request
- step 3: desired output mode
- step 4: optional advanced settings

The existing wizard components show the current fragmentation:

- `frontend/components/wizards/project-wizard.tsx`
- `frontend/components/wizards/generate-specs-wizard.tsx`
- `frontend/components/wizards/implement-feature-wizard.tsx`

## Backend/API follow-up

The flow works without backend changes, but the next backend improvement should be a compound intent-based endpoint, for example:

- `POST /projects/{id}/brownfield/run`

That endpoint should accept the same high-level inputs as the Windmill flow and internally decide whether to stop at tasks, create a protocol, or create or sync a sprint. That would remove backend leakage of SpecKit and protocol internals from the UI.
