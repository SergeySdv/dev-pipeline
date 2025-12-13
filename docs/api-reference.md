# TasksGodzilla Orchestrator API Reference (alpha)

HTTP API for managing projects, protocol runs, steps, events, queues, and CI/webhook signals. Default base: `http://localhost:8011` (compose; use 8010 for direct local runs).

**Architecture Note**: All API endpoints use the services layer (`tasksgodzilla/services/`) as the primary integration surface. Endpoints delegate business logic to services (OrchestratorService, ExecutionService, QualityService, OnboardingService, etc.) rather than calling workers or database operations directly. This provides stable, testable contracts and clear separation of concerns.

- Auth: set `TASKSGODZILLA_API_TOKEN` in the API env and send `Authorization: Bearer <token>`. If unset, auth is skipped.
- Per-project token (optional): `X-Project-Token: <project secrets.api_token>`.
- Content type: `application/json` for all JSON bodies. Responses use standard HTTP codes (400/401/404/409 on validation/auth/state conflicts).

## Status enums and models
- ProtocolRun.status: `pending`, `planning`, `planned`, `running`, `paused`, `blocked`, `failed`, `cancelled`, `completed`.
- StepRun.status: `pending`, `running`, `needs_qa`, `completed`, `failed`, `cancelled`, `blocked`.
- StepRun.policy/runtime_state: arbitrary JSON from CodeMachine modules (loop/trigger metadata, inline trigger depth, loop_counts, etc.).

## Health & metrics
- `GET /health` → `{"status": "ok"|"degraded"}`.
- `GET /metrics` → Prometheus text format.

## Projects
- `POST /projects`
  - Body: `{ "name": str, "git_url": str, "base_branch": "main", "ci_provider": str|null, "project_classification": str|null, "default_models": obj|null, "secrets": obj|null, "local_path": str|null }`
  - Response: Project object with `id`, timestamps.
  - **Service**: Uses `OnboardingService.register_project()` to create project and enqueue setup
  - Behavior: persists `local_path` when provided so future jobs resolve the repo without recomputing; falls back to cloning under `TASKSGODZILLA_PROJECTS_ROOT` (default `projects/<project_id>/<repo_name>`) when missing.
  - Side effects: enqueues `project_setup_job` protocol run for onboarding progress visibility and onboarding clarifications.
  - Notes:
    - `project_classification` is a user-friendly “project type” that selects the initial policy pack; supported values include `default`, `beginner-guided`, `startup-fast`, `team-standard`, `enterprise-compliance` (see `docs/project-classifications.md`).
- `GET /projects` → list of projects.
- `GET /projects/{id}` → project (401 if project token required and missing).
- `GET /projects/{id}/clarifications` → list persisted clarification questions (filter with `?status=open|answered`).
- `POST /projects/{id}/clarifications/{key}` → set an answer for a clarification key (body: `{ "answer": <any>, "answered_by": <str|null> }`).
- `GET /projects/{id}/onboarding` → onboarding summary (status, workspace, stages, recent events) for `setup-{id}`.
- `POST /projects/{id}/onboarding/actions/start`
  - Body: `{ "inline": bool }` (optional; default false)
  - Behavior: mirrors project-creation onboarding; when `inline=true`, runs the setup job in-process (no worker required). When `inline=false`, enqueues `project_setup_job`.
  - Side effects: emits `setup_enqueued` and then `setup_*` progress events.
- `GET /projects/{id}/branches`
  - Response: `{ "branches": [str] }`
  - Behavior: resolves repo via stored `local_path` or `git_url` (defaulting to `projects/<project_id>/<repo_name>`); clones when allowed; records an event.
- `POST /projects/{id}/branches/{branch:path}/delete`
  - Body: `{ "confirm": true }` (required)
  - Behavior: deletes the remote branch on origin, records an event; 409 when the repo is unavailable locally.

Event visibility
- Onboarding emits `setup_discovery_*` events (started/skipped/completed/warning) around Codex repo discovery so console/TUI/CLI can show discovery progress per project.
  - Discovery uses the multi-pass pipeline (inventory → architecture → API reference → CI notes) via `prompts/discovery-*.prompt.md`.

## CodeMachine import
- `POST /projects/{id}/codemachine/import`
  - Body: `{ "protocol_name": str, "workspace_path": str, "base_branch": "main", "description": str|null, "enqueue": bool }`
  - Response:
    - `enqueue=true`: `{ protocol_run: ProtocolRun, job: {job_id,...}, message }` after enqueuing `codemachine_import_job`.
    - `enqueue=false` (default): `{ protocol_run: ProtocolRun, job: null, message }` after immediate import.
  - **Service**: Uses `CodeMachineService.import_workspace()` for immediate import or `QueueService.enqueue_codemachine_import()` for async
  - Behavior: parses `.codemachine/config/*.js` + `template.json`, persists `template_config`/`template_source`, and creates StepRuns for main agents with module policies attached.

## Protocol runs
- `POST /projects/{id}/protocols`
  - Body: `{ "protocol_name": str, "status": "pending"|..., "base_branch": "main", "worktree_path": str|null, "protocol_root": str|null, "description": str|null, "template_config": obj|null, "template_source": obj|null }`
  - Response: ProtocolRun object.
  - **Service**: Uses `OrchestratorService.create_protocol_run()`
- `GET /projects/{id}/protocols` → list protocol runs for project.
- `GET /protocols/{id}` → protocol run.
- `GET /protocols/{id}/clarifications` → list protocol-scope clarifications (planning/execution gates).
- `POST /protocols/{id}/clarifications/{key}` → set an answer for a protocol clarification key.

### Protocol actions
All return `{ "message": str, "job": obj|null }` unless noted. All actions use `OrchestratorService` methods.
- `POST /protocols/{id}/actions/start`
  - **Service**: `OrchestratorService.start_protocol_run()` → enqueues `plan_protocol_job`
  - Returns 409 if not pending/planned/paused
- `POST /protocols/{id}/actions/pause`
  - **Service**: `OrchestratorService.pause_protocol()` → updates status
- `POST /protocols/{id}/actions/resume`
  - **Service**: `OrchestratorService.resume_protocol()` → updates status
- `POST /protocols/{id}/actions/cancel`
  - **Service**: `OrchestratorService.cancel_protocol()` → updates status, cancels pending steps
- `POST /protocols/{id}/actions/run_next_step`
  - **Service**: `OrchestratorService.enqueue_next_step()` → moves first pending/blocked/failed step to running and enqueues `execute_step_job`
- `POST /protocols/{id}/actions/retry_latest`
  - **Service**: `OrchestratorService` → retries latest failed/blocked step
- `POST /protocols/{id}/actions/open_pr`
  - **Service**: `QueueService.enqueue_open_pr()` → enqueues `open_pr_job`

Status conflicts return 409 (e.g., starting an already-running protocol).

## Steps
- `POST /protocols/{id}/steps`
  - Body: `{ "step_index": int>=0, "step_name": str, "step_type": str, "status": "pending"|..., "model": str|null, "summary": str|null, "engine_id": str|null, "policy": obj|[obj]|null }`
  - Creates a StepRun (no job enqueued).
  - **Service**: Direct database operation (no service wrapper needed for simple CRUD)
- `GET /protocols/{id}/steps` → list StepRuns.
- `GET /steps/{id}` → StepRun.

### Step actions
All step actions use services for business logic:
- `POST /steps/{id}/actions/run`
  - **Service**: `ExecutionService.execute_step()` via `QueueService.enqueue_execute_step()`
  - Sets to running, enqueues `execute_step_job`
- `POST /steps/{id}/actions/run_qa`
  - **Service**: `QualityService.run_for_step_run()` via `QueueService.enqueue_run_quality()`
  - Sets to `needs_qa`, enqueues `run_quality_job`
- `POST /steps/{id}/actions/approve`
  - **Service**: `OrchestratorService.handle_step_completion()`
  - Marks completed, may complete protocol

## Events & queues
- `GET /protocols/{id}/events` → events for a protocol.
- `GET /events?project_id=<id>&limit=<int>` → recent events (default limit 50).
- `GET /queues` → queue stats (per queue).
- `GET /queues/jobs?status=queued|started|failed|finished` → jobs snapshot with payload/metadata.
  - Jobs include `job_id`, `job_type`, `payload`, `status`, timestamps, and error/meta where present.

## Runs, logs, and artifacts

The orchestrator records each job attempt as a **run** in `codex_runs` (despite the name, it covers all job types). Runs are the primary “execution record” and are linkable to protocols/steps:
- Core linkage fields: `project_id`, `protocol_run_id`, `step_run_id`, `run_kind`, `attempt`, `worker_id`.
- Logs: each run has a log file at `runs/<run_id>/logs.txt` (or a configured override).
- Structured results: execution/QA services enrich `codex_runs.result` with fields like `exec`, `qa`, and `qa_inline` (engine/model/prompt versions/outputs/verdict).
- Artifacts: files created during exec/QA are registered in `run_artifacts` and exposed via the API below.

### Run listing
- `GET /codex/runs`
  - Query params:
    - `job_type=<str>` (optional)
    - `status=<str>` (optional)
    - `project_id=<int>` (optional)
    - `protocol_run_id=<int>` (optional)
    - `step_run_id=<int>` (optional)
    - `run_kind=<str>` (optional; e.g. `plan|exec|qa|setup|open_pr|spec_audit`)
    - `limit=<int>` (default 100)
- `GET /protocols/{protocol_run_id}/runs`
  - Query params: `run_kind=<str>` (optional), `limit=<int>`
- `GET /steps/{step_run_id}/runs`
  - Query params: `run_kind=<str>` (optional), `limit=<int>`
- `GET /codex/runs/{run_id}` → single run record.

### Logs
- `GET /codex/runs/{run_id}/logs` → plain text log output for that run.

### Artifacts
- `GET /codex/runs/{run_id}/artifacts`
  - Query params: `kind=<str>` (optional), `limit=<int>`
  - Returns metadata (name/kind/path/sha256/bytes/created_at).
- `GET /codex/runs/{run_id}/artifacts/{artifact_id}/content`
  - Returns the artifact file as plain text (currently capped at 1MB to avoid heavy responses).

## Webhooks & CI callbacks
- `POST /webhooks/github?protocol_run_id=<optional>`
  - Headers: `X-GitHub-Event`, optional `X-Hub-Signature-256` when `TASKSGODZILLA_WEBHOOK_TOKEN` set.
  - Body: standard GitHub webhook payload. Maps by branch (or `protocol_run_id` query) to update step/protocol status, enqueue QA on success when `TASKSGODZILLA_AUTO_QA_ON_CI`=true, mark protocol completed on PR merge.
- `POST /webhooks/gitlab?protocol_run_id=<optional>`
  - Headers: `X-Gitlab-Event`, token via `X-Gitlab-Token` or `X-TasksGodzilla-Webhook-Token`, optional HMAC `X-Gitlab-Signature-256`.
  - Similar mapping and QA/autocomplete behavior to GitHub handler.
- `scripts/ci/report.sh success|failure` can call these endpoints from CI with `TASKSGODZILLA_API_BASE`, `TASKSGODZILLA_API_TOKEN`, `TASKSGODZILLA_WEBHOOK_TOKEN`, `TASKSGODZILLA_PROTOCOL_RUN_ID` for explicit mapping.

## Queue/runtime notes
- Backend: Redis/RQ; set `TASKSGODZILLA_INLINE_RQ_WORKER=true` to have the API start a background RQ worker thread for inline job processing during local development.
- **Service Integration**: All jobs are enqueued via `QueueService` and processed by workers that delegate to services
- Jobs: `project_setup_job`, `plan_protocol_job`, `execute_step_job`, `run_quality_job`, `open_pr_job`, `codemachine_import_job`.
  - Workers are thin adapters: deserialize payload → call service method → return
  - Business logic lives in services, not workers
- CodeMachine policies: loop/trigger policies on steps may reset statuses or inline-trigger other steps (depth-limited) with events and `runtime_state` recorded. Handled by `OrchestratorService.apply_trigger_policy()` and `OrchestratorService.apply_loop_policy()`.
- Token budgets: `TASKSGODZILLA_MAX_TOKENS_PER_STEP` / `TASKSGODZILLA_MAX_TOKENS_PER_PROTOCOL` with mode `TASKSGODZILLA_TOKEN_BUDGET_MODE=strict|warn|off`; overruns raise (strict) or log (warn). Enforced by `BudgetService`.

## Curl examples

Create project:
```bash
curl -X POST http://localhost:8011/projects \
  -H "Authorization: Bearer $TASKSGODZILLA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"demo","git_url":"/path/to/repo","base_branch":"main"}'
```

Run onboarding inline for an existing project:
```bash
curl -X POST http://localhost:8011/projects/1/onboarding/actions/start \
  -H "Authorization: Bearer $TASKSGODZILLA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inline": true}'
```

## CLIs

- `python scripts/discovery_pipeline.py`
  - Purpose: re-run all or selected discovery artifacts on an existing repo without full onboarding.
  - Key args: `--repo-root <path>`, `--artifacts inventory,architecture,api_reference,ci_notes`, `--model <model>`, `--sandbox workspace-write`, `--timeout-seconds <int>`.
  - Example:
    ```bash
    python scripts/discovery_pipeline.py --repo-root . --artifacts inventory,ci_notes
    ```

Start planning a protocol:
```bash
curl -X POST http://localhost:8011/protocols/1/actions/start \
  -H "Authorization: Bearer $TASKSGODZILLA_API_TOKEN"
```

Run QA for a step:
```bash
curl -X POST http://localhost:8011/steps/10/actions/run_qa \
  -H "Authorization: Bearer $TASKSGODZILLA_API_TOKEN"
```

List queue jobs:
```bash
curl -X GET "http://localhost:8011/queues/jobs?status=queued" \
  -H "Authorization: Bearer $TASKSGODZILLA_API_TOKEN"
```
