# DevGodzilla

DevGodzilla is the primary stack in this repository: a FastAPI backend (`devgodzilla/`), a Next.js console (`frontend/`), and Windmill orchestration assets (`windmill/`) behind nginx.

## Documentation Source of Truth

Use these docs first:

- `docs/DevGodzilla/CURRENT_STATE.md` (what runs today)
- `docs/DevGodzilla/ARCHITECTURE.md` (layered architecture, current vs target)
- `docs/DevGodzilla/API-ARCHITECTURE.md` (API architecture and domains)
- `docs/DevGodzilla/WINDMILL-WORKFLOWS.md` (Windmill scripts/flows/resources)

Historical docs are archived under `docs/legacy/` with mapping in `docs/legacy/README.md`.

## Repository Layout

- `devgodzilla/`: FastAPI API, services, engines, DB access, Windmill client integration
- `frontend/`: Next.js console (served at `/console`)
- `windmill/`: Windmill scripts/flows/apps/resources exported from this repo
- `Origins/`: vendored upstream sources (do not edit unless explicitly required)
- `scripts/`: operational scripts and CI wrappers
- `tests/`: pytest suite for backend/services/workflows
- `docs/`: active + archived documentation
- `prompts/`: reusable agent/system prompts used by protocol/project workflows
- `schemas/`: JSON schema contracts for protocol planning/spec/task artifacts

## Runtime Topology (Local)

- nginx entrypoint: `http://localhost:8080`
- Host processes:
  - DevGodzilla API: `:8000`
  - Next.js frontend: `:3000`
- Docker services:
  - nginx, windmill, windmill workers, postgres, redis, lsp

Routing is defined in `nginx.local.conf`:

- `/console`, `/_next` -> frontend
- API routes (`/projects`, `/protocols`, `/steps`, etc.) -> DevGodzilla API
- `/` -> Windmill UI

## Quick Start

### 0) Install host prerequisites

- Python 3.12
- Node.js + `pnpm` (required by `scripts/run-local-dev.sh frontend start`)
- Docker + Docker Compose

### 1) Bootstrap Python environment

```bash
scripts/ci/bootstrap.sh
```

### 2) Start local stack

```bash
# infra in Docker
scripts/run-local-dev.sh up

# backend + frontend on host
scripts/run-local-dev.sh backend start
scripts/run-local-dev.sh frontend start

# or all at once
scripts/run-local-dev.sh dev
```

### 3) Import Windmill assets (optional but recommended)

```bash
scripts/run-local-dev.sh import
```

### 4) Open interfaces

- DevGodzilla API docs: `http://localhost:8080/docs`
- Next.js console: `http://localhost:8080/console`
- Windmill UI: `http://localhost:8080/`

## Development Commands

```bash
# Lint
scripts/ci/lint.sh

# Type/import checks
scripts/ci/typecheck.sh

# Tests
scripts/ci/test.sh
```

## API Surface (High-Level)

Route domains are implemented under `devgodzilla/api/routes/`:

- Core: `/projects`, `/protocols`, `/steps`, `/agents`, `/clarifications`
- SpecKit/specifications: `/speckit/*`, `/projects/{id}/speckit/*`, `/specifications*`
- Agile: `/sprints*`, `/tasks*`
- Governance/quality: `/policy_packs*`, `/projects/{id}/policy*`, `/quality/dashboard`
- Operations: `/events*`, `/logs*`, `/metrics*`, `/queues*`, `/cli-executions*`, `/runs*`
- Windmill passthrough: `/flows*`, `/jobs*`
- Webhooks: `/webhooks/*`

For exact schemas use `GET /openapi.json`.

## Implementation Notes

- Business logic lives in `devgodzilla/services/`.
- Engine adapters live in `devgodzilla/engines/` and are configured by `devgodzilla/config/agents.yaml`.
- Windmill scripts in `windmill/scripts/devgodzilla/` are expected to call the DevGodzilla API (thin adapter model).
- Optional discovery writes runtime artifacts under `specs/discovery/_runtime/`.

## Documentation Maintenance Rule

If docs and code disagree, trust code first, then update the canonical docs listed above.
