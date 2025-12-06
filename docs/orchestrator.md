# DeksdenFlow Orchestrator (alpha)

This folder describes the first slice of a central orchestrator/API you can run locally. It is intentionally minimal: SQLite persistence, FastAPI endpoints, and a Redis/RQ-backed queue (fakeredis works for tests).

## Components
- `deksdenflow/storage.py`: SQLite schema + small DAO for Projects, ProtocolRuns, StepRuns, and Events.
- `deksdenflow/domain.py`: status enums and dataclasses for the core entities.
- `deksdenflow/api/app.py`: FastAPI app with health, project, protocol, step, and event endpoints plus action hooks that enqueue placeholder jobs.
- `deksdenflow/jobs.py`: queue abstraction backed by Redis/RQ via `DEKSDENFLOW_REDIS_URL`.
- `deksdenflow/worker_runtime.py`: job processors that call Codex/onboarding handlers, plus background worker helper (SimpleWorker for fakeredis).
- `deksdenflow/logging.py`: minimal structured logging helpers and request-id filter.
- `scripts/api_server.py`: uvicorn runner for the API; starts a SimpleWorker thread when using fakeredis (dev/tests).
- `scripts/ci_trigger.py`: optional helper to trigger CI (gh/glab) for a protocol branch.
- `scripts/rq_worker.py`: RQ worker entrypoint when using Redis-backed queue (fakeredis works for tests).

## Quickstart
```bash
pip install fastapi uvicorn pydantic
python scripts/api_server.py
# API listens on 0.0.0.0:8000 by default

# optional: start a dedicated RQ worker if using real Redis
python scripts/rq_worker.py
```

Environment toggles:
- `DEKSDENFLOW_DB_PATH` (default `.deksdenflow.sqlite`)
- `DEKSDENFLOW_ENV` (default `local`)
- `DEKSDENFLOW_API_TOKEN` (optional; when set, require `Authorization: Bearer <token>` on non-health endpoints)
- `DEKSDENFLOW_API_HOST` / `DEKSDENFLOW_API_PORT` for server binding
- `DEKSDENFLOW_REDIS_URL` to enable Redis-backed queue (required; `fakeredis://` works for tests)
- `DEKSDENFLOW_LOG_LEVEL` (default `INFO`)
- `DEKSDENFLOW_WEBHOOK_TOKEN` (optional shared secret for webhook calls)
Retry/backoff:
- Jobs default to `max_attempts=3` with exponential backoff up to 60s; failures append events and block the protocol.

## API sketch
- `GET /health` → `{ "status": "ok" }`
- `POST /projects` (name, git_url, base_branch, optional ci_provider/default_models)
- `GET /projects` / `GET /projects/{id}`
- `POST /projects/{id}/protocols`
- `GET /projects/{id}/protocols`
- `GET /protocols/{id}`
- `POST /protocols/{id}/actions/start` → enqueues `plan_protocol_job`
- `POST /protocols/{id}/steps` → adds StepRun
- `GET /protocols/{id}/steps`
- `POST /steps/{id}/actions/run` → enqueues `execute_step_job`
- `POST /steps/{id}/actions/run_qa` → enqueues `run_quality_job`
- `POST /steps/{id}/actions/approve` → marks completed and logs event
- `GET /protocols/{id}/events`

## Next upgrades
- Harden queue abstraction (visibility timeouts, retries) and add dedicated worker images for Redis-backed deployments.
- Extend actions to attach git/worktree data and Codex model selections per project.
- Add auth (API tokens), correlation IDs, and structured logging.
- Wire CI/webhook listeners and surface status in the console (TUI/web).
