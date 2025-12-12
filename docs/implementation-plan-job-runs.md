# Implementation Plan: Job Runs / Executions (V1)

Goal: make every attempt (plan/exec/qa/etc) a first-class, queryable execution record in `codex_runs`, with consistent linkage to `project_id`, `protocol_run_id`, `step_run_id`, plus durable logs and structured outputs.

## Priorities

### P0 (must-have)
- Enrich run records with execution details (`tasksgodzilla/storage.py` + `tasksgodzilla/services/*`):
  - Record engine/model, prompt versions, outputs paths, QA verdict/report path in `codex_runs.result`.
  - Ensure run finalization does not overwrite previously recorded `result` fields.
- Console wiring:
  - Add “Runs” links/views for Protocol and Step pages using:
    - `GET /protocols/{protocol_run_id}/runs`
    - `GET /steps/{step_run_id}/runs`
  - Add direct links to `GET /codex/runs/{run_id}/logs`.

### P1 (should-have)
- Normalize attempt/retry semantics:
  - Prefer queue-provided attempt counts (RQ) when available; fall back to local counter.
  - Display attempt consistently in API/UI/log lines.
- Console filtering:
  - Client-side filter by `run_kind` (`plan/exec/qa/setup/open_pr/spec_audit/...`).

### P2 (nice-to-have)
- Add a minimal artifacts registry keyed by `run_id`:
  - Store `{name, path, bytes, sha256, created_at}` for stdout/stderr/reports/aux outputs.
  - Keep `codex_runs.result` as pointers/summary rather than large blobs.
- Cancellation:
  - Provide “cancel” semantics (mark run cancelled + best-effort worker stop).

## Definition of Done (V1)
- A step page can show its run history (attempts) and link to logs.
- A protocol page can show all runs across steps and protocol-level jobs.
- For exec/QA runs, `codex_runs.result` contains enough metadata to debug without scanning `events`.
