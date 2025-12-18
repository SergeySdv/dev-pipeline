# Windmill → TasksGodzilla: Codex Run Refs (Logs + Result)

> Legacy integration note:
> DevGodzilla no longer wires this into the default Windmill flows/scripts. If you still run the legacy TasksGodzilla UI and want it to proxy Windmill logs/results, use the bridge assets under `archive/windmill/tasksgodzilla_bridge/`.

This repo supports displaying Windmill job logs/results in the TasksGodzilla web UI by storing special references in:
- `codex_runs.log_path`
- `run_artifacts.path`

References use the URI form:
- `windmill://job/<job_id>/logs`
- `windmill://job/<job_id>/result`
- `windmill://job/<job_id>/error`

The TasksGodzilla API proxies these to Windmill when you open:
- `GET /codex/runs/{run_id}/logs`
- `GET /codex/runs/{run_id}/logs/tail`
- `GET /codex/runs/{run_id}/logs/stream` (SSE)
- `GET /codex/runs/{run_id}/artifacts/{artifact_id}/content`

## Windmill script: emit refs
Windmill script (bridge): `archive/windmill/tasksgodzilla_bridge/scripts/emit_tasksgodzilla_codex_refs.py`

It reads the current Windmill job ID from `WM_JOB_ID` and calls the TasksGodzilla API to:
1) upsert a codex run via `POST /codex/runs/start` with `log_path=windmill://job/<WM_JOB_ID>/logs`
2) upsert three artifacts (optional): `windmill.logs`, `windmill.result`, `windmill.error`

## Windmill flow wiring
This is no longer enabled in the default DevGodzilla flows.

If you still need this behavior, create a legacy-specific flow pack that runs the bridge script first, then calls the DevGodzilla scripts/flows.

Recommended inputs to pass to the bridge script:
- `run_id`: use an existing TasksGodzilla `codex_runs.run_id` (otherwise defaults to `WM_JOB_ID`)
- `params`: store in `codex_runs.params`
- `attach_default_artifacts`: defaults `true`
- optionally `project_id`, `protocol_run_id`, `step_run_id` for best-effort association

## Windmill scripts (direct execution)
DevGodzilla Windmill scripts no longer emit TasksGodzilla refs automatically. If you need this, wrap calls with `archive/windmill/tasksgodzilla_bridge/scripts/emit_tasksgodzilla_codex_refs.py`.

## Required configuration (Windmill runtime env)
Windmill jobs need to be able to call the TasksGodzilla API.

Set environment variables for the Windmill worker/runtime:
- `TASKSGODZILLA_API_URL` (example: `http://tasksgodzilla-api:8011` or `http://host.docker.internal:8011`)
- `TASKSGODZILLA_API_TOKEN` (optional; must match `TASKSGODZILLA_API_TOKEN` on the API if auth is enabled)

## TasksGodzilla API: artifact upsert
The API exposes an internal-friendly endpoint for Windmill to register references:
- `POST /codex/runs/{run_id}/artifacts/upsert` (body: `{name, kind, path, sha256?, bytes?}`)
