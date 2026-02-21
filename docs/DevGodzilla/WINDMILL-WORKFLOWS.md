# DevGodzilla Windmill Workflows

> Status: Active
> Scope: Current Windmill integration and supported usage
> Source of truth: `windmill/flows/devgodzilla/`, `windmill/scripts/devgodzilla/`, `windmill/resources/devgodzilla/`, `windmill/import_to_windmill.py`
> Last updated: 2026-02-21

## Summary

Windmill is used as orchestration runtime and operator UI companion. In this repo, Windmill scripts are primarily thin API adapters that call DevGodzilla API.

## Repository Locations

- Scripts: `windmill/scripts/devgodzilla/`
- Flows: `windmill/flows/devgodzilla/`
- Apps: `windmill/apps/devgodzilla/`
- React app bundle: `windmill/apps/devgodzilla-react-app/`
- Resources: `windmill/resources/devgodzilla/`

## Local Development Pattern

1. Start infra: `docker compose up --build -d`
2. Start host services: `scripts/run-local-dev.sh backend restart` and `scripts/run-local-dev.sh frontend restart`
3. Import assets: `scripts/run-local-dev.sh import`

Default token file for import in local setup:

- `windmill/apps/devgodzilla-react-app/.env.development`

## Supported Integration Model

Preferred model:

- Windmill scripts call DevGodzilla API via helper `windmill/scripts/devgodzilla/_api.py`.

Avoid as default pattern:

- importing and executing `devgodzilla` package code directly inside Windmill workers.

## Key Scripts (Current)

Core orchestration scripts:

- `project_onboard_api.py`
- `protocol_plan_and_wait.py`
- `protocol_select_next_step.py`
- `step_execute_api.py`
- `step_run_qa_api.py`
- `onboard_to_tasks_api.py`
- `protocol_from_spec_api.py`
- `open_pr.py`
- `handle_feedback.py`

SpecKit-related API wrapper scripts:

- `speckit_specify_api.py`
- `speckit_plan_api.py`
- `speckit_tasks_api.py`
- `speckit_clarify_api.py`
- `speckit_checklist_api.py`
- `speckit_analyze_api.py`
- `speckit_implement_api.py`

## Key Flows (Current)

Available flow exports include:

- `onboard_to_tasks.flow.json`
- `protocol_start.flow.json`
- `step_execute_with_qa.flow.json`
- `run_next_step.flow.json`
- `spec_to_tasks.flow.json`
- `spec_to_protocol.flow.json`
- `execute_protocol.flow.json`
- `project_onboarding.flow.json`
- `sync_tasks_to_sprint.flow.json`
- `sprint_from_protocol.flow.json`
- `complete_sprint.flow.json`

Recommended baseline flows in local stack:

- `f/devgodzilla/onboard_to_tasks`
- `f/devgodzilla/protocol_start`
- `f/devgodzilla/step_execute_with_qa`
- `f/devgodzilla/run_next_step`

## Resources

Current resource exports:

- `windmill/resources/devgodzilla/database.resource.yaml`
- `windmill/resources/devgodzilla/agents.resource.yaml`

## Related Docs

- Runtime truth: `docs/DevGodzilla/CURRENT_STATE.md`
- API architecture: `docs/DevGodzilla/API-ARCHITECTURE.md`
- System architecture: `docs/DevGodzilla/ARCHITECTURE.md`
- Legacy archive index: `docs/legacy/README.md`
