# Implementation Status – Orchestrator Track

## Recently completed
- Postgres adapter alongside SQLite with factory selection via `DEKSDENFLOW_DB_URL`; pool size configurable.
- Alembic scaffolding + initial migration (projects, protocol_runs, step_runs, events) applied to default SQLite.
- Token budgeting enforced in pipeline/QA (`DEKSDENFLOW_MAX_TOKENS_*`, strict/warn/off).
- Structured logging extended (JSON option via `DEKSDENFLOW_LOG_JSON`); workers/CLIs/API share logger init, request IDs, and standard exit codes; events now include protocol/step IDs and workers log job start/end with IDs.
- Makefile helpers: `orchestrator-setup`, `deps`, `migrate`.
- Compose stack + Dockerfile for `deksdenflow-core`; optional codex-worker service; K8s manifests for API/worker with probes and resource limits.

## How to run now
```bash
make orchestrator-setup \
  DEKSDENFLOW_DB_URL=postgresql://user:pass@host:5432/dbname  # or use DEKSDENFLOW_DB_PATH for SQLite
```
Then start API: `.venv/bin/python scripts/api_server.py`
# Or use docker-compose: `docker-compose up --build` (API on :8000)

## Next focus
- Harden logging/error handling across all CLIs/workers with richer structured fields (protocol/step IDs everywhere).
- Refine token accounting with real usage data instead of heuristic.
- Extend Postgres path with connection pooling and Alembic-managed upgrades in CI.
- Console/API polish: surface DB choice/status, expose migrations health endpoint, richer console filters.

## Phase 0 gaps to close
- Logging normalization: codex/CI helpers should emit structured fields (protocol/step IDs, branch) consistently.
- Container hardening: publish images, add secrets templates for DB/Redis/API tokens, and include readiness/liveness for codex/generic workers.
