# Light Codex Control Plane Plan

Lean control plane for monitoring, starting, and governing Codex executions without over-engineering.

## Objectives
- Centralize runs, prompts, and execution parameters with minimal dependencies.
- Keep executor thin; use filesystem + SQLite/Postgres (configurable) and HTTP/CLI entrypoints.
- Provide basic controls (start/status/cancel/retry), structured logs, and a small metrics surface.

## Phase 1 – Run registry and logging
- Add `runs` table (SQLite default, Postgres-compatible) with `run_id` (uuid), `job_type`, `status`, `created_at`, `updated_at`, `started_at`, `finished_at`, `prompt_version`, `params` (json), `result` (json), `error` (text), `log_path` (text), `cost_tokens` (int), `cost_cents` (int).
- Create lightweight ORM/data access helpers in `tasksgodzilla` (or nearest module) to insert on start, patch status on transitions, and fetch by `run_id`.
- Standardize structured JSON logging fields: `run_id`, `job_type`, `status`, `prompt_version`, `phase`, `duration_ms`, `cost_tokens`, `cost_cents`.
- Emit run lifecycle hooks around the existing bootstrap/executor: `record_run_start`, `record_run_success`, `record_run_failure`, `record_run_cancelled`.
- Store stdout/stderr tails under `runs/<run_id>/logs.txt`; capture the path in the registry row.
- Build a simple executions log/console (HTML page or TUI) that lists all runs with filters (job type, status, date), shows status badges, links to per-run log tail, and exposes start/status/cancel/retry buttons or shortcuts.

## Phase 2 – Prompt registry and config
- Create `prompts/index.json` mapping `name -> {version, path, checksum, owner, updated_at}`; enforce immutability per version.
- Add loader to resolve `prompt_version` for a job type, read prompt file, and verify checksum before use; allow override flag for manual runs.
- Define per-job-type config file (`configs/jobs/<job_type>.yaml`) with `max_tokens`, `timeout`, `allowed_tools`, `concurrency_limit`, and default `prompt_version`.
- Validate job inputs with pydantic models tied to the job config; reject invalid payloads before enqueue/execute.

## Phase 3 – Control surface (HTTP/CLI)
- Implement minimal HTTP endpoints (or extend existing API): `POST /runs/start`, `GET /runs/{id}`, `POST /runs/{id}/cancel`, `POST /runs/{id}/retry`. Require shared bearer token.
- Mirror the same actions in a CLI (`scripts/codex_ctl.py`): `start`, `status`, `cancel`, `retry`, `tail` for logs.
- Enforce per-job-type concurrency using DB row locks or a Redis counter; block/return 429 when the limit is reached.
- Implement cancellation via SIGTERM to worker process plus registry update to `cancelled`; ensure cleanup of temp artifacts.

## Phase 4 – Metrics and housekeeping
- Add a small `/metrics` endpoint (Prometheus exposition) with counters for successes/failures, histogram for duration, and gauges for in-flight runs per job type. Update metrics on lifecycle transitions only.
- Track token/cost in registry and metrics when the model returns usage; default to zero if unavailable.
- Add a cron/CLI task `cleanup_runs` to delete `runs/<run_id>/` artifacts and prune DB rows older than 14 days.

## Phase 5 – Safety and auth
- Use a single shared API token (env `CODEX_CONTROL_TOKEN`) checked by HTTP endpoints and CLI.
- Enforce guardrails from job config: max tokens, timeout, allowed tools; hard-stop on violation before execution.
- Keep prompts and config in Git; changes go through PRs for auditability.

## Deliverables and acceptance
- New docstrings and README snippet showing how to start a run, check status, cancel, and view logs.
- Passing unit tests for registry CRUD, prompt resolution, concurrency guard, and lifecycle hooks.
- Demonstrated end-to-end flow: start run -> see registry/log entry -> cancel/retry -> metrics reflect transitions.
