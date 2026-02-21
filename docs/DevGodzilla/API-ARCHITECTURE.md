# DevGodzilla API Architecture

> Status: Active
> Scope: Current API architecture (implemented) + short target notes
> Source of truth: `devgodzilla/api/app.py`, `devgodzilla/api/routes/*.py`, `GET /openapi.json`
> Last updated: 2026-02-21

## Summary

DevGodzilla API is a FastAPI service that exposes project/protocol/step lifecycle management, SpecKit operations, governance, agile artifacts, operations telemetry, and Windmill passthrough endpoints.

For exact schemas, request/response payloads, and required fields, use `GET /openapi.json`.

## Request Flow

```text
Client -> nginx -> FastAPI route -> dependency injection -> service layer -> db/windmill/filesystem
```

- App entrypoint: `devgodzilla/api/app.py`
- Route modules: `devgodzilla/api/routes/*.py`
- Main dependencies: `devgodzilla/api/dependencies.py`

## Authentication and Access

- Most route groups are protected by API token dependency.
- Webhook endpoints use webhook-token dependency.
- Metrics endpoint is exposed without the API-token dependency.

Configured in app wiring (`app.include_router(...)`) rather than a separate gateway.

## Route Domains (Implemented)

### Core Lifecycle

- `/projects*`
- `/protocols*`
- `/steps*`
- `/agents*`
- `/clarifications*`

### Specification

- `/speckit/*`
- `/projects/{project_id}/speckit/*`
- `/specifications*`

### Agile

- `/sprints*`
- `/tasks*`

### Governance and Quality

- `/policy_packs*`
- `/projects/{project_id}/policy*`
- `/quality/dashboard`

### Operations

- `/events*`
- `/logs/recent`, `/logs/stream`
- `/queues`, `/queues/stats`, `/queues/jobs`
- `/cli-executions*`
- `/runs*`
- `/metrics`, `/metrics/summary`

### Windmill and External Signals

- `/flows*`, `/jobs*` (Windmill passthrough)
- `/webhooks/github`, `/webhooks/gitlab`, `/webhooks/windmill/job`, `/webhooks/windmill/flow`

### Profile and Health

- `/profile`
- `/health`, `/health/live`, `/health/ready`

## API Naming Notes

- Policy pack API uses underscore path: `/policy_packs`.
- Frontend route slug uses hyphen path: `/console/policy-packs`.

This is intentional and currently implemented.

## Streaming Endpoints

Server-sent event style streaming endpoints exist for long-running operations/log tails:

- `/events/stream`
- `/runs/{run_id}/logs/stream`
- `/cli-executions/{execution_id}/logs/stream`
- `/logs/stream`

## Service Layer Relationship

Route handlers are thin orchestration endpoints and delegate business logic to services in `devgodzilla/services/`.

## Target Notes (Not Implemented Yet)

Potential improvements (non-blocking for current implementation):

- automated route-doc drift checks in CI,
- stricter typed response envelopes for all async job endpoints,
- explicit API versioning policy.

## Related Docs

- Runtime truth: `docs/DevGodzilla/CURRENT_STATE.md`
- Architecture: `docs/DevGodzilla/ARCHITECTURE.md`
- Windmill workflows: `docs/DevGodzilla/WINDMILL-WORKFLOWS.md`
- Legacy archive index: `docs/legacy/README.md`
