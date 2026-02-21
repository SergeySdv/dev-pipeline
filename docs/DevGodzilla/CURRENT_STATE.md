# DevGodzilla Current State

> Status: Active
> Scope: Current Runtime (Implemented)
> Source of truth: `devgodzilla/api/app.py`, `devgodzilla/api/routes/`, `frontend/next.config.mjs`, `nginx.local.conf`, `docker-compose.yml`, `windmill/`
> Last updated: 2026-02-21

This document describes what runs in this repository today.

## Canonical Documentation

- Runtime truth: `docs/DevGodzilla/CURRENT_STATE.md` (this file)
- Architecture (current + target boundaries): `docs/DevGodzilla/ARCHITECTURE.md`
- API architecture: `docs/DevGodzilla/API-ARCHITECTURE.md`
- Windmill workflows: `docs/DevGodzilla/WINDMILL-WORKFLOWS.md`
- Legacy/history docs: `docs/legacy/README.md`

## Runtime Topology (Local Dev)

Local default workflow is hybrid:

1. Docker Compose runs infra: nginx, windmill, windmill workers, postgres, redis, lsp.
2. Host runs DevGodzilla API (`:8000`) and Next.js frontend (`:3000`).
3. nginx proxies API paths to host API and `/console` to host frontend.
4. Windmill UI remains served at `/`.

Primary files:

- `docker-compose.yml`
- `docker-compose.local.yml`
- `scripts/run-local-dev.sh`
- `nginx.local.conf`

## Frontend

Current primary console is Next.js at `frontend/` with base path `/console`:

- Config: `frontend/next.config.mjs` (`basePath: '/console'`)
- API calls: frontend rewrites `/api/*` to DevGodzilla API base URL

Windmill UI remains available at root path (`/`) for workflow operations.

## API Surface (Implemented)

FastAPI app entrypoint: `devgodzilla/api/app.py`.

Route groups currently registered:

- Health: `/health`, `/health/live`, `/health/ready`
- Core: `/projects`, `/protocols`, `/steps`, `/agents`, `/clarifications`
- SpecKit: `/speckit/*`, `/projects/{id}/speckit/*`
- Agile: `/sprints`, `/tasks`
- Governance: `/policy_packs`, project policy endpoints under `/projects/{id}/policy*`
- Quality and specs: `/quality/dashboard`, `/specifications*`
- Ops: `/events*`, `/logs*`, `/metrics*`, `/queues*`, `/cli-executions*`, `/runs*`
- Windmill passthrough: `/flows*`, `/jobs*`
- Webhooks: `/webhooks/github`, `/webhooks/gitlab`, `/webhooks/windmill/*`
- Profile: `/profile`

For exact request/response shapes, use `GET /openapi.json`.

## Planning and Execution Model

Current planning is protocol-file driven:

1. A protocol run exists in DB.
2. Planning reads `.protocols/<protocol_name>/step-*.md` (or SpecKit-backed sources when used).
3. `StepRun` rows are materialized from protocol step files.

If step files are missing and auto-generation is enabled, protocol files are generated via headless agent before planning proceeds.

Execution artifacts are written under protocol worktree:

- `.protocols/<protocol_name>/.devgodzilla/steps/<step_run_id>/artifacts/*`

QA runs automatically after successful step execution, with manual re-run available via step QA endpoint.

## SpecKit Artifacts

SpecKit-style artifacts are generated in `.specify/` through DevGodzilla services and prompts. Current implementation does not depend on an external `specify` binary.

## Discovery Artifacts

Onboarding can run optional discovery. Current expected outputs include legacy-named files under `tasksgodzilla/` for compatibility with existing downstream tooling:

- `tasksgodzilla/ARCHITECTURE.md`
- `tasksgodzilla/API_REFERENCE.md`
- `tasksgodzilla/CI_NOTES.md`

These are generated artifacts, not the active code package.

## Windmill Integration Model

Supported pattern: Windmill scripts call DevGodzilla API (thin adapters), rather than importing the `devgodzilla` Python package into Windmill runtime.

Repository paths:

- Scripts: `windmill/scripts/devgodzilla/`
- Flows: `windmill/flows/devgodzilla/`
- Apps: `windmill/apps/devgodzilla/`
- Resources: `windmill/resources/devgodzilla/`

Recommended flows for local stack:

- `f/devgodzilla/onboard_to_tasks`
- `f/devgodzilla/protocol_start`
- `f/devgodzilla/step_execute_with_qa`
- `f/devgodzilla/run_next_step`
