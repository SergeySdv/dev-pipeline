# Architecture and Workflow Overview

This repository is a starter kit for TasksGodzilla_Ilyas_Edition_1.0: a protocol-driven way to ship work in parallel streams. The codebase is mostly orchestration around the Codex CLI, Git worktrees, and shared CI stubs for GitHub and GitLab.

For deeper design and delivery detail, see:
- `docs/solution-design.md` — current-state review and target orchestrator architecture.
- `docs/implementation-plan.md` — phased plan from refactors to console/CI integration.
- `Makefile` — convenience targets: `orchestrator-setup` (venv + deps + migrations) using Alembic and the Postgres/SQLite adapters.

## Repository layout (current state)
- `README.md`: quickstart and high-level Mermaid diagrams.
- `docs/`: deep dive on TasksGodzilla (`tasksgodzilla.md`), CI notes (`ci.md`), TerraformManager demo workflow plan, and this architecture doc.
- `prompts/`: operational prompt library (new/resume/review protocols, project/init/bootstrap, CI discovery, QA, Java testing).
- `scripts/`: orchestration utilities (protocol pipeline, project setup, CI discovery, QA orchestrator, dataset report generator) plus `scripts/ci/*` stubs.
- `.github/workflows/ci.yml` and `.gitlab-ci.yml`: dual CI entrypoints that call the same `scripts/ci/*.sh` hooks.
- `schemas/`: JSON schema for planning agent output.
- `tests/`: harnesses covering orchestration code paths; optional Codex integration test gated by `RUN_REAL_CODEX`.
- `tasksgodzilla/`: reusable library for protocol pipeline, QA, project setup, and the new orchestrator (API + storage + domain).

## Workspace layout (default)
```text
projects/
  <project_id>/
    <repo_name>/            # main working copy (from git_url or local_path)
      .protocols/<protocol>/...
    worktrees/
      <protocol_name>/      # created from origin/<base_branch> during planning
        .protocols/<protocol_name>/...
```
`TASKSGODZILLA_PROJECTS_ROOT` overrides the `projects/` root; `local_path` overrides the repo path when provided.

## Control plane (orchestrator)

The orchestrator uses a **service-oriented architecture** where services are the primary integration layer for all business logic. The architecture consists of three main layers:

### Services Layer (Primary Integration Surface)

**Application Services** (`tasksgodzilla/services/`):
- **OrchestratorService**: Protocol lifecycle management (create, start, pause, resume, cancel), step orchestration, trigger/loop policy application
- **ExecutionService**: Step execution via engine registry, prompt/output resolution
- **QualityService**: QA evaluation with policy-driven workflows (skip/light/full)
- **SpecService**: ProtocolSpec/StepSpec building, validation, and step run materialization
- **OnboardingService**: Project registration, workspace setup, discovery flows
- **DecompositionService**: Step decomposition with heuristics
- **PromptService**: Prompt resolution with version fingerprinting
- **GitService**: Git operations, worktree management, PR/MR creation, CI triggering
- **BudgetService**: Token budget tracking and enforcement
- **CodeMachineService**: CodeMachine workspace import and management

**Platform Services** (`tasksgodzilla/services/platform/`):
- **QueueService**: Semantic job enqueue operations wrapping Redis/RQ
- **TelemetryService**: Token observation, metrics, and event logging
- **StorageService**: Repository layer over BaseDatabase (future)
- **EnginesService**: Engine registry and model selection policies

All API endpoints, CLI commands, and worker jobs delegate to services. Services provide stable, testable contracts and are the single source of truth for business logic. See `docs/services-architecture.md` for detailed service design and `docs/services-migration-guide.md` for usage patterns.

### Interface Layer

- **FastAPI API** (`tasksgodzilla/api/app.py`): HTTP endpoints with bearer/project-token auth, queue stats, metrics, events feed, and webhook listeners. All endpoints use services.
- **CLI** (`tasksgodzilla/cli/main.py`, `scripts/tasksgodzilla_cli.py`): Command-line interface for protocol operations
- **TUI** (`tasksgodzilla/cli/tui.py`, `tui-rs`): Terminal UI for interactive protocol management
- **Web Console** (`/console`): Lightweight web UI for projects, protocol runs, steps, events, and queue visibility

### Infrastructure Layer

- **Storage**: SQLite (default) or Postgres (`TASKSGODZILLA_DB_URL`), initialized with Alembic migrations
- **Queue**: Redis/RQ (`tasksgodzilla/jobs.py`, `worker_runtime.py`) with optional inline worker for local dev (`TASKSGODZILLA_INLINE_RQ_WORKER=true`)
- **Workers**: Thin job adapters (`tasksgodzilla/workers/*`) that deserialize payloads and delegate to services
- **Engines**: Pluggable execution engines (Codex, CodeMachine) via registry pattern

```mermaid
graph TB
  subgraph "Interface Layer"
    Console["Web Console"]
    API["FastAPI API"]
    CLI["CLI"]
    TUI["TUI"]
  end
  
  subgraph "Services Layer (Primary Integration)"
    Orchestrator["OrchestratorService"]
    Execution["ExecutionService"]
    Quality["QualityService"]
    Spec["SpecService"]
    Onboarding["OnboardingService"]
    Git["GitService"]
    Budget["BudgetService"]
    Prompts["PromptService"]
    Queue["QueueService"]
    Telemetry["TelemetryService"]
  end
  
  subgraph "Infrastructure Layer"
    DB[(Database)]
    Redis["Redis/RQ"]
    Workers["Workers (thin adapters)"]
    Engines["Engine Registry"]
  end
  
  Console --> API
  CLI --> Orchestrator
  TUI --> API
  API --> Orchestrator
  API --> Onboarding
  
  Orchestrator --> Execution
  Orchestrator --> Quality
  Orchestrator --> Spec
  Orchestrator --> Queue
  
  Execution --> Spec
  Execution --> Prompts
  Execution --> Budget
  Execution --> Engines
  
  Quality --> Spec
  Quality --> Prompts
  Quality --> Engines
  
  Onboarding --> Git
  Onboarding --> Telemetry
  
  Queue --> Redis
  Redis --> Workers
  Workers --> Orchestrator
  Workers --> Execution
  Workers --> Quality
  
  Orchestrator --> DB
  Spec --> DB
  Git --> DB
  Telemetry --> DB
```

### Worktree creation (Mermaid)
```mermaid
flowchart LR
  Repo["projects/<project_id>/<repo> (default workspace)"] --> Plan["plan_protocol_job\ncreates branch + worktree"]
  Plan --> WT["projects/<project_id>/<repo_name>/worktrees/<protocol_name>"]
  WT --> Branch["git checkout -b <protocol_name> origin/<base_branch>"]
  WT --> Prot[".protocols/<protocol_name>/plan + steps"]
```

## Orchestrator pipelines (detailed)

### Protocol lifecycle (jobs, policies, QA)

```mermaid
flowchart TD
  A[/POST /projects/] --> B["project_setup_job\nresolve workspace projects/<id>/<repo>, discovery,\nensure starter assets, clarifications"]
  A --> C["optional codemachine_import_job\npersist ProtocolSpec + steps"]
  B --> D[/POST /projects/{id}/protocols + start/]
  D --> E["plan_protocol_job\nemit ProtocolSpec\nsync StepRuns from spec"]
  E --> F{"Step pending/blocked?"}
  F -->|execute| G[/steps/{id}/actions/execute → execute_step_job/]
  G --> H["Resolve prompt + outputs via spec\nengine registry dispatch"]
  H --> I["Prompt QA auto-run"]
  I --> J{"QA verdict"}
  J -->|PASS| M["Step completed\ntrigger policies may enqueue other steps"]
  J -->|FAIL| N{"Loop policy?"}
  N -->|apply| F
  N -->|none| O["Protocol blocked; retry_latest/run_next_step"]
```

### CI feedback and completion

```mermaid
flowchart LR
  A["execute_step_job\n(per spec outputs; potential push/open PR)"] --> B["CI (GitHub/GitLab) pipelines"]
  B --> C["report.sh or webhooks\n/webhooks/github|gitlab\n(branch or protocol_run_id)"]
  C --> D{"Normalized status"}
  D -->|running| E["Step status → running"]
  D -->|success| H["Step completed (CI passed)"]
  D -->|failure| I["Step failed; Protocol blocked\nloop/trigger policies may reset steps"]
  H --> J{"PR/MR merged?"}
  J -->|yes| K["Protocol → completed"]
```

## Runtime configuration (env vars)
- `TASKSGODZILLA_DB_URL` / `TASKSGODZILLA_DB_PATH` — Postgres URL or SQLite path (SQLite default).
- `TASKSGODZILLA_REDIS_URL` — required Redis/RQ URL; e.g., `redis://localhost:6379/15` or `redis://localhost:6380/0` (docker-compose). Set `TASKSGODZILLA_INLINE_RQ_WORKER=true` to run an inline worker in the API process for local dev/tests.
- `TASKSGODZILLA_API_TOKEN` / `TASKSGODZILLA_WEBHOOK_TOKEN` — bearer auth + webhook HMAC/token validation.
- `TASKSGODZILLA_MAX_TOKENS_PER_STEP` / `TASKSGODZILLA_MAX_TOKENS_PER_PROTOCOL` + `TASKSGODZILLA_TOKEN_BUDGET_MODE=strict|warn|off` — guardrails for Codex calls.
- `TASKSGODZILLA_PROJECTS_ROOT` — base folder for auto-cloned repos (default `projects/<project_id>/<repo_name>`). `TASKSGODZILLA_AUTO_CLONE=false` leaves onboarding blocked until the repo exists locally.
- `TASKSGODZILLA_GH_SSH` — prefer rewriting GitHub origins to SSH during onboarding; `TASKSGODZILLA_GIT_USER` / `TASKSGODZILLA_GIT_EMAIL` set git identity when provided.
- `TASKSGODZILLA_REQUIRE_ONBOARDING_CLARIFICATIONS` — when true, onboarding emits blocking clarifications for CI/model/branch policies in the console/TUI.
- Logging: `TASKSGODZILLA_LOG_JSON=true` for structured logs; `TASKSGODZILLA_LOG_LEVEL=info|debug`.
- Models: project `default_models` override per phase; fallbacks in `tasksgodzilla.config`.

## Job types and workers
- `project_setup_job` — ensure starter assets exist; emits setup events (no git mutation).
- `plan_protocol_job` — create worktree, run planning + step decomposition via Codex, emit `ProtocolSpec`/`StepSpec`, write `.protocols/`, and sync StepRuns from the spec.
- `execute_step_job` — resolve prompt and outputs from the StepSpec, dispatch via the engine registry (Codex/CodeMachine today), write outputs map, and auto-run prompt QA.
- `open_pr_job` — push branch and open PR/MR via `gh`/`glab` if available.
- `codemachine_import_job` — parse `.codemachine` config, emit `ProtocolSpec`/`StepSpec` (engines, QA, policies), persist template, and create steps from the spec.
- Workers: RQ workers (`scripts/rq_worker.py`) for Redis; API can auto-start a background RQ worker thread when `TASKSGODZILLA_INLINE_RQ_WORKER=true` (dev/test convenience).

## Data model (core fields)
- Project: `id`, `name`, `git_url`, `local_path`, `base_branch`, `ci_provider`, `default_models`, `secrets` (optional `api_token`).
- ProtocolRun: `id`, `project_id`, `protocol_name`, `status`, `base_branch`, `worktree_path`, `protocol_root`, `description`, `template_config`/`template_source`, timestamps.
- StepRun: `id`, `protocol_run_id`, `step_index`, `step_name`, `step_type`, `status`, `retries`, `model`, `engine_id`, `policy`, `runtime_state`, `summary`.
- Event: `id`, `protocol_run_id`, `step_run_id`, `event_type`, `message`, `metadata`, `created_at` (+ joined protocol/project names in list views).

## Failure, retries, and policies
- RQ retries: default `max_attempts=3` with exponential backoff (capped 60s) for enqueued jobs.
- State guards: API uses optimistic checks; conflicting status transitions return 409.
- Loop policies (from StepSpec; often from CodeMachine modules): can reset steps to `pending` and increment `loop_counts` in `runtime_state`; bounded by `max_iterations` and skip lists.
- Trigger policies: can re-queue/inline other steps; inline depth capped (`MAX_INLINE_TRIGGER_DEPTH`) to avoid recursion.
- CI failures: webhook/report.sh set step to `failed` and protocol to `blocked`; manual retry resumes.
- Codex/Repo unavailable: workers stub execution/QA, set `needs_qa` or `completed` with events and avoid crashing pipelines.

## Git, CI, and webhooks

## Findings and gaps (as of alpha)

The core control plane is in place (Projects/ProtocolRuns/StepRuns + queue + services), but a few end-to-end product gaps remain important for real-world usage across different teams and experience levels:

### 1) Project classification needs a first-class onboarding choice

The system supports policy packs and a project policy selection API, but onboarding still needs to make “project type” selection a primary decision so defaults and required structure match the user’s context.

See:
- `docs/policy-framework.md`
- `docs/project-classifications.md`
- Policy endpoints in `docs/api-reference.md`

### 2) Clarifications are not first-class state yet

Onboarding emits `setup_clarifications` as an Event and policy packs can define `clarifications`, but there is no persisted Q/A model, no “answer clarifications” API, and no consistent gating rule to block/unblock runs based on missing answers. This blocks the “some tasks require user input / inexperienced user guidance” goal.

Recommended next step: introduce a Clarifications service + DB table that stores questions and user answers, and use it as a gate when the selected policy pack requires it.

### 3) Policy enforcement is mostly reporting today

Policy evaluation exists and can be escalated to “block” severity, but most flows treat findings as warnings and continue. For strict projects (e.g., compliance), execution and QA should block (not fail) when critical requirements are unmet.

### 4) Documentation can drift from implementation

Some docs describe targets (e.g., “thin worker”) rather than current reality. Prefer documenting:
- what is implemented today,
- what is planned next,
- and which pieces are intentionally best-effort.

## Further architecture (recommended next iteration)

If you want consistent behavior across “beginner” through “enterprise” projects, a useful next slice is:
- **Project classification → policy pack selection** in onboarding (console + CLI).
- **Policy-driven clarifications** (persisted questions + answers, with blocking rules and clear UI).
- **Policy-driven prompt injection** into planning/decomposition (required sections/checks included automatically).
- **Optional strict mode gates** in execution/QA that turn missing critical requirements into `blocked` with actionable remediation (instead of “failed” or “silent warning”).
- Project repos resolve via stored `local_path` when present; otherwise onboarding clones under `TASKSGODZILLA_PROJECTS_ROOT` using the per-project layout `projects/<project_id>/<repo_name>`, records the resolved path, configures `origin` (prefers GitHub SSH when enabled), and can set git identity from env.
- Remote branch controls: `GET /projects/{id}/branches` lists origin branches and `POST /projects/{id}/branches/{branch}/delete` (with `confirm=true`) deletes them, recording events for audit.
- Worktrees: created under `<repo_root>/worktrees/<protocol_name>` from `origin/<base_branch>`; branch name matches protocol. When `TASKSGODZILLA_SINGLE_WORKTREE=true` (default), multiple protocols share a single branch/worktree `worktrees/tasksgodzilla-worktree` and isolate state via `.protocols/<protocol_name>/`.
- Push/PR: best-effort push + `gh`/`glab` draft creation after planning/exec and in `open_pr_job`.
- CI flows: `.github/workflows/ci.yml` and `.gitlab-ci.yml` call `scripts/ci/*.sh` hooks; failures are mirrored via webhooks or `scripts/ci/report.sh`.
- Webhook mapping: branch name (or explicit `protocol_run_id` param) maps CI events to runs; success can auto-enqueue QA, merge events complete the protocol.

## Deployment modes
- Local dev: `make orchestrator-setup && TASKSGODZILLA_REDIS_URL=redis://localhost:6379/15 TASKSGODZILLA_INLINE_RQ_WORKER=true .venv/bin/python scripts/api_server.py`; background worker thread handles jobs inline.
- Local host app + compose dependencies: `make compose-deps` (brings up Redis:6380, Postgres:5433) then run API/workers on host with `TASKSGODZILLA_DB_URL=postgresql://tasksgodzilla:tasksgodzilla@localhost:5433/tasksgodzilla` and `TASKSGODZILLA_REDIS_URL=redis://localhost:6380/0`.
- Docker Compose full stack: `docker compose up --build -d` for API + worker + codex-worker + Redis + Postgres (API on http://localhost:8011, default token `changeme` unless overridden); use `docker compose logs -f api worker codex-worker` for troubleshooting.
- Production: prefer external Redis + Postgres; run API separately from RQ workers; lock down `TASKSGODZILLA_API_TOKEN`/`TASKSGODZILLA_WEBHOOK_TOKEN`.

## Security and tenancy
- Auth: bearer token on all non-health endpoints; optional per-project token via `X-Project-Token`.
- Webhooks: HMAC (`X-Hub-Signature-256` or `X-Gitlab-Signature-256`) or shared token (`X-Gitlab-Token`/`X-TasksGodzilla-Webhook-Token`) when configured.
- Secrets: stored in `projects.secrets` (JSON) for project-level API token; avoid storing CI/git tokens in DB when possible.

## Observability
- Metrics: `/metrics` exposes Prometheus counters/histograms for requests, jobs, tokens, webhooks.
- Logging: structured logs via `tasksgodzilla.logging` with request/job/project/protocol/step IDs; JSON toggle via env. API runs uvicorn with `log_config=None` so the central formatter/filter stays active; workers/QA/CI helpers pass job IDs through.
- Events: persisted timeline per protocol/step; surfaced in console and `/events` API.
- Runs: every job attempt is recorded in `codex_runs` (linked by `project_id`, `protocol_run_id`, `step_run_id`, `run_kind`, `attempt`, `worker_id`) with a per-run log file under `runs/<run_id>/logs.txt`. Runs are queryable via `/codex/runs`, `/protocols/{id}/runs`, and `/steps/{id}/runs`.
- Run artifacts: output/report files are registered in `run_artifacts` and available via `/codex/runs/{run_id}/artifacts` (with optional `/content` for small text artifacts).
- Protocol logs: workers append timestamped notes to `.protocols/.../log.md` after execution and QA when the file exists.

## Core building blocks
- **Protocol assets and schema**  
  - Protocols live under `.protocols/NNNN-[task]/` inside each worktree; numbered via `next_protocol_number()` scanning existing `.protocols/` and `worktrees/`.  
  - `schemas/protocol-planning.schema.json` enforces the planning agent’s JSON (plan/context/log + step files).  
  - `schemas/protocol-spec.schema.json` + `tasksgodzilla/spec.py` define/validate the unified ProtocolSpec/StepSpec stored on runs; spec audit/backfill is available via `spec_worker`.
- **Protocol pipeline (`scripts/protocol_pipeline.py`)**  
  - Interactive CLI that: detects repo root, prompts for base branch/short name/description; creates a Git worktree/branch `NNNN-[task]` from `origin/<base>`; and builds protocol artifacts.  
  - Uses Codex CLI twice: (1) planning (`run_codex_exec` with `planning_prompt`, validated against the JSON schema) to produce `plan.md`, `context.md`, `log.md`, `00-setup.md`, and step files; (2) step decomposition (`decompose_step_prompt`) for each non-setup step.  
  - Optional `--skip-simple-decompose` flag (or `PROTOCOL_SKIP_SIMPLE_DECOMPOSE=true`) skips the second AI pass for short/simple steps using a conservative heuristic.  
  - Optional flags: `--pr-platform github|gitlab` to auto-commit/push and open Draft PR/MR (requires `gh`/`glab`); `--run-step` to auto-execute a step via Codex using `execute_step_prompt`.  
  - Model defaults come from env (`PROTOCOL_PLANNING_MODEL`, `PROTOCOL_DECOMPOSE_MODEL`, `PROTOCOL_EXEC_MODEL`) with fallbacks (`zai-coding-plan/glm-4.6`, etc.). Temporary artifacts live in `.protocols/<name>/.tmp/`.
- **QA orchestrator (`scripts/quality_orchestrator.py`)**  
  - Builds a QA prompt from `plan.md`, `context.md`, `log.md`, the current step file, git status, and last commit, then calls Codex with `prompts/quality-validator.prompt.md`. Bookkeeping drift or dirty git limited to `.protocols/**` is treated as non-blocking; the service auto-downgrades such FAILs to PASS.
  - Writes `quality-report.md`; exits non-zero on Codex failure or `VERDICT: FAIL` to gate CI/pipelines. Steps marked `qa.policy=light` run the QA pass inline during execution and short-circuit the extra queue hop.
- **Project setup (`scripts/project_setup.py`)**  
  - Ensures a repo exists (optionally `git init -b <base>`), warns if `origin` or base branch is missing, and materializes starter assets from `BASE_FILES`. Copies from this starter repo when available; otherwise writes placeholders.  
  - Marks CI scripts executable and can optionally run Codex discovery via `--run-discovery`/`PROTOCOL_DISCOVERY_MODEL`.
- **Codex CI bootstrap (`scripts/codex_ci_bootstrap.py`)**  
  - Multi-pass Codex discovery pipeline (inventory → architecture → API reference → CI notes) using `prompts/discovery-*.prompt.md`. Writes `specs/discovery/_runtime/DISCOVERY.md`, `ARCHITECTURE.md`, `API_REFERENCE.md`, `CI_NOTES.md`, and `DISCOVERY_SUMMARY.json`, and may update `scripts/ci/*`.
- **CI surfaces**  
  - GitHub Actions job `checks` and GitLab stages `bootstrap → lint → typecheck → test → build` each call the matching `scripts/ci/*.sh` if executable; otherwise emit “skip” messages. The scripts are placeholders today and must be filled per stack.
- **Prompts library**  
  - `protocol-new` defines the contract for opening a protocol (worktree creation, planning, first commit/PR, step structure, commit messaging).  
  - `protocol-resume` and `protocol-review-merge*` handle continuation and QA/merge flows with context reconciliation.  
  - `project-init` guides scaffolding a repo; `protocol-pipeline` guides running `protocol_pipeline.py`; `java-testing` and `quality-validator` provide specialized guidance.
- **CodeMachine import/runtime**  
  - `.codemachine` workspaces are parsed via `tasksgodzilla.codemachine.load_codemachine_config`, normalizing main/sub agents, module policies, placeholders, and templates into a `ProtocolSpec`.  
  - `codemachine_worker.import_codemachine_workspace` persists the spec to the protocol run and creates steps for main agents with engines, QA config, and loop/trigger policies.  
  - Execution uses the shared prompt/output resolver plus engine registry; CodeMachine outputs land in `.protocols/<protocol>/` and aux `codemachine` paths, with prompt QA auto-run and optional gates from policy.
- **Dataset helper (`scripts/generate_dataset_report.py`)**  
  - Small utility that reads `dataset.csv` (category/value), aggregates metrics, and renders a PDF via reportlab. Current inputs are toy data; output path defaults to `docs/dataset_report.pdf`.
- **TerraformManager workflow plan (`docs/terraformmanager-workflow-plan.md`)**  
  - Checklists for cloning/running the TerraformManager demo under `projects/`, covering API/CLI/UI validation and optional infra tooling; serves as an example end-to-end ops workflow.
- **Orchestrator (legacy / archived)**  
  - The legacy TasksGodzilla orchestrator lives under `archive/tasksgodzilla/` (including `archive/tasksgodzilla/api/app.py`). The old console source is in `frontend/`, and build output is published to `archive/tasksgodzilla/api/frontend_dist/`.
  - Worker jobs cover planning, execution, QA, project setup, PR open, and CodeMachine import. Execution/QA paths share the spec-driven resolver + engine registry; loop/trigger policies from StepSpecs (often CodeMachine modules) drive retries or inline triggers with runtime_state updates and events.

## Operational workflows
1. **Run the orchestrator + console**  
   - `make orchestrator-setup && TASKSGODZILLA_REDIS_URL=redis://localhost:6379/15 TASKSGODZILLA_INLINE_RQ_WORKER=true .venv/bin/python scripts/api_server.py` (SQLite + local Redis) or `docker-compose up --build` (Postgres/Redis). Visit `/console` for projects/protocols/steps/events; queue and metrics available at `/queues*` and `/metrics`. With `TASKSGODZILLA_INLINE_RQ_WORKER=true`, the API auto-starts a background RQ worker thread for inline processing.
2. **Bootstrap a repo**  
   - Run `python3 scripts/project_setup.py --base-branch <branch> [--init-if-needed] [--run-discovery]` or follow `prompts/project-init.prompt.md`. Creates docs/prompts/CI/scripts/schema, ensures git state, and optionally runs Codex discovery to prefill CI hooks.
   - Onboarding records the resolved repo path (stored on the Project) and can auto-configure `origin`/git identity; it emits `setup_clarifications` with recommended CI/model/branch policies and can block when `TASKSGODZILLA_REQUIRE_ONBOARDING_CLARIFICATIONS=true`.
   - Optional: import an existing CodeMachine workspace via `POST /projects/{id}/codemachine/import` to materialize steps and template metadata before planning/exec flows.
3. **Open a new protocol stream**  
   - From repo root, run `python3 scripts/protocol_pipeline.py ...`. It creates `worktrees/<protocol_name>/` (or reuses `worktrees/tasksgodzilla-worktree` in shared mode), generates `.protocols/<protocol_name>/` with plan + step files, optionally commits/pushes + Draft PR/MR, and can auto-run a step. Work happens in the worktree; plan/step files are the execution contract.
4. **Execute steps manually (outside auto-run)**  
   - Work from the protocol’s worktree. For each step: follow the step file, run stack checks (`lint/typecheck/test/build`), update `log.md` and `context.md`, commit with `type(scope): subject [protocol-NNNN/XX]`, push, and report per the contract in `prompts/protocol-new.prompt.md`.
5. **QA gate a step**  
   - Run `python3 scripts/quality_orchestrator.py --protocol-root <.protocols/...> --step-file XX-*.md [--model ...] [--sandbox ...]`. On FAIL, fix issues before continuing; reports land in `quality-report.md`. Or trigger QA via `/steps/{id}/actions/qa` (auto-runs after execution).
6. **CI pipelines**  
   - Both GitHub Actions and GitLab CI invoke the same `scripts/ci/*.sh` hooks. Real work requires filling those scripts; missing scripts simply print skip messages to keep empty repos green. CI results can be mirrored back via `scripts/ci/report.sh` posting to orchestrator webhooks.
7. **Optional: CI discovery**  
   - Use `python3 scripts/codex_ci_bootstrap.py` to run the discovery prompt that suggests/fills CI commands based on the detected stack.
8. **Sample data/report workflow**  
   - `scripts/generate_dataset_report.py --csv dataset.csv --out docs/dataset_report.pdf` converts the sample CSV into a PDF report; demonstrates the pattern for simple analytic tooling.
9. **TerraformManager demo**  
   - `docs/terraformmanager-workflow-plan.md` documents a full validation flow for the TerraformManager app (clone, configure env vars, run services, exercise CLI/API/UI, optional container smoke tests).

## State, conventions, and dependencies
- **Worktrees/branches:** When `TASKSGODZILLA_SINGLE_WORKTREE=false`, each protocol lives in its own worktree under `<repo_root>/worktrees/<protocol_name>/` with a same-named branch from `origin/<base>`. Default mode uses a shared worktree `worktrees/tasksgodzilla-worktree` and isolates protocols under `.protocols/<protocol_name>/`. Protocol numbering scans `.protocols/` and `worktrees/`.
- **Commit format:** `feat(protocol): add plan for ... [protocol-NNNN/00]` for initial plan; subsequent commits use `type(scope): subject [protocol-NNNN/XX]` as defined in `protocol-new.prompt.md`.
- **Models/env vars:** Planning/decompose/exec/QA models configurable via `PROTOCOL_PLANNING_MODEL`, `PROTOCOL_DECOMPOSE_MODEL`, `PROTOCOL_EXEC_MODEL`, `PROTOCOL_QA_MODEL`, `PROTOCOL_DISCOVERY_MODEL`; defaults favor `zai-coding-plan/glm-4.6`. Codex CLI timeout is controlled by `TASKSGODZILLA_CODEX_TIMEOUT_SECONDS` (work steps default to 1200s via spec). Stuck-step watchdog uses `TASKSGODZILLA_STEP_STUCK_SECONDS`. Token budgets enforced via `TASKSGODZILLA_MAX_TOKENS_*` with `strict|warn|off` modes.
- **Queue/runtime:** Redis/RQ is the canonical backend; `TASKSGODZILLA_INLINE_RQ_WORKER=true` triggers a background RQ worker thread from the API to process jobs inline during dev/tests. Trigger policies are bounded by `MAX_INLINE_TRIGGER_DEPTH` to avoid unbounded recursion.
- **External tooling:** Codex CLI (mandatory for orchestrators), optional `gh`/`glab` for PR/MR automation. The dataset helper requires `reportlab`. Redis/RQ is required for the orchestrator queue.
- **Git hygiene:** Scripts avoid destructive commands; `project_setup` warns if `origin` missing or base branch absent. `.gitignore` excludes local assets (`projects/`, dataset files, generated reports).
- **Statuses:** ProtocolRun `pending → planning → planned → running → (paused|blocked|failed|cancelled|completed)`; StepRun `pending → running → needs_qa → (completed|failed|cancelled|blocked)` with events recorded per transition.

## Quality and tests
- Unit tests cover orchestration helpers (`run_codex_exec`, QA prompt assembly, project setup discovery wiring).  
- Integration test `tests/test_readme_workflow_integration.py` can exercise the full protocol pipeline against real Codex when `RUN_REAL_CODEX=1`.  
- No stack-specific lint/type/test wired yet—`scripts/ci/*` are placeholders to be customized per project.
