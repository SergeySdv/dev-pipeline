# DevGodzilla Architecture

> Status: Active
> Scope: Current + Target (explicitly separated)
> Source of truth: `docs/DevGodzilla/CURRENT_STATE.md`, `devgodzilla/`, `frontend/`, `windmill/`
> Last updated: 2026-02-21

## Summary

DevGodzilla in this repo is a layered system:

1. Edge and routing (`nginx.local.conf`)
2. UI layer (Next.js `/console` + Windmill root UI)
3. API layer (FastAPI)
4. Service layer (`devgodzilla/services/`)
5. Engine layer (`devgodzilla/engines/`)
6. Data and integration layer (Postgres, Redis, Windmill, filesystem)

## Current Architecture (Implemented)

```text
Browser
  -> nginx (:8080)
     -> /console, /_next ............. frontend (Next.js on host :3000)
     -> /projects|/protocols|... ..... devgodzilla API (host :8000)
     -> / (default) .................. windmill UI/server (container :8000)

DevGodzilla API
  -> services/* (planning, execution, quality, policy, spec, orchestration)
  -> engines/* (opencode, codex, claude-code, gemini-cli, dummy)
  -> db (PostgreSQL or SQLite for dev)
  -> redis (queues/cache)
  -> filesystem (project repos, .protocols, .specify, run artifacts)
```

## Layer Responsibilities

### 1) Edge and Routing

- nginx routes API endpoints to FastAPI, `/console` to Next.js, and root to Windmill.
- Route definitions are in `nginx.local.conf` and `nginx.devgodzilla.conf`.

### 2) UI Layer

- Primary product console: `frontend/` (Next.js, base path `/console`).
- Windmill UI remains available at root for workflow/operator use.

### 3) API Layer

- FastAPI app: `devgodzilla/api/app.py`.
- Route modules: `devgodzilla/api/routes/*.py`.
- API dependencies centralize auth/context/db wiring.

### 4) Service Layer

Implemented service modules include:

- `devgodzilla/services/orchestrator.py`
- `devgodzilla/services/planning.py`
- `devgodzilla/services/execution.py`
- `devgodzilla/services/quality.py`
- `devgodzilla/services/specification.py`
- `devgodzilla/services/spec_to_protocol.py`
- `devgodzilla/services/policy.py`
- `devgodzilla/services/clarifier.py`
- `devgodzilla/services/sprint_integration.py`
- `devgodzilla/services/task_sync.py`
- `devgodzilla/services/git.py`

### 5) Engine Layer

Current engine adapters are implemented under `devgodzilla/engines/` and configured via `devgodzilla/config/agents.yaml`.

### 6) Data and Integrations

- DB access: `devgodzilla/db/`
- Alembic migrations: `devgodzilla/alembic/`
- Windmill integration: `devgodzilla/windmill/`
- Windmill assets: `windmill/flows/devgodzilla/`, `windmill/scripts/devgodzilla/`, `windmill/apps/devgodzilla/`
- Prompt assets: `prompts/` (protocol/discovery/project bootstrapping prompts)
- Schema contracts: `schemas/` (JSON schemas validating planning/spec/task documents and protocol artifacts)

## Current Constraints and Known Leftovers

- Some generated discovery artifacts still use `tasksgodzilla/*` names for compatibility.
- Historical architecture and migration documents are archived under `docs/legacy/` and are not authoritative.
- API path naming is intentionally mixed in places (`/policy_packs` in API vs `/policy-packs` as a frontend page slug).

## Target Architecture (Not Implemented Yet)

The following items are target-state directions and should not be read as completed work:

- Additional hardening of service boundaries with stricter internal contracts.
- Broader automated doc validation (broken links, stale path detection, route drift checks).
- Expanded observability correlation across API, Windmill jobs, and artifact lineage.

## Documentation Governance

Use this order when documentation conflicts:

1. Runtime truth in code (`devgodzilla/api/app.py`, route modules, config files)
2. `docs/DevGodzilla/CURRENT_STATE.md`
3. Other active docs in `docs/DevGodzilla/`
4. Archived docs in `docs/legacy/` (historical only)

## Legacy Archive

Historical architecture/layer docs were moved to `docs/legacy/`.

Migration index: `docs/legacy/README.md`
