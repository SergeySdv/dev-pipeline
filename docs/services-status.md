# Services Refactor – Implementation Status

This document tracks progress on the new `tasksgodzilla.services.*` layer and the
service-oriented refactor. It complements `STATUS.md` (orchestrator track) and
`docs/services-architecture.md`.

## Scope

- Define a forward-looking services API under `tasksgodzilla/services/…`.
- Migrate API/CLI/TUI and workers to use services instead of legacy helpers.
- Allow non-backwards-compatible changes to old worker flows where needed.

## High-level milestones

- [x] **Architecture & plan**
  - `docs/services-architecture.md` describing target services and platform layers.
  - Decision: services layer is the new primary contract; legacy worker helpers
    may be simplified or removed as we migrate.

- [x] **Initial service stubs**
  - `tasksgodzilla/services/orchestrator.py` (`OrchestratorService`)
  - `tasksgodzilla/services/execution.py` (`ExecutionService`)
  - `tasksgodzilla/services/onboarding.py` (`OnboardingService`)
  - `tasksgodzilla/services/spec.py` (`SpecService`)
  - `tasksgodzilla/services/quality.py` (`QualityService`)
  - `tasksgodzilla/services/prompts.py` (`PromptService`)
  - `tasksgodzilla/services/decomposition.py` (`DecompositionService`)
  - `tasksgodzilla/services/platform/queue.py` (`QueueService`)
  - `tasksgodzilla/services/platform/telemetry.py` (`TelemetryService`)

- [ ] **Wire services into API**
  - Replace direct calls to `codex_worker`, `project_setup`, and raw DB helpers
    in `tasksgodzilla/api/app.py` with service calls.
  - [x] Use `OrchestratorService.create_protocol_run` for `/projects/{project_id}/protocols`.
  - [x] Route protocol actions `start|run_next_step|retry_latest` through `OrchestratorService`.
  - [x] Expose onboarding start via `/projects/{id}/onboarding/actions/start` (service-backed job enqueue).
  - [x] Route open_pr enqueue through `OrchestratorService` (`/protocols/{id}/actions/open_pr`).
  - [ ] Route remaining protocol/step actions through services where appropriate.
  - Ensure request/response shapes remain compatible for existing clients.

- [ ] **Wire services into CLI/TUI**
  - Update `tasksgodzilla/cli/main.py` and `scripts/tasksgodzilla_cli.py` to use
    `OnboardingService`, `OrchestratorService`, and `ExecutionService`.
  - TUI flows use API or service client wrappers instead of reaching into workers.

- [ ] **Refactor worker job handlers**
  - Change `tasksgodzilla/worker_runtime.process_job` to call services:
    - [x] `plan_protocol_job` → `OrchestratorService.plan_protocol`
    - [x] `execute_step_job` → `ExecutionService.execute_step`
    - [x] `run_quality_job` → `QualityService.run_for_step_run`
    - [x] `project_setup_job` → `OnboardingService.run_project_setup_job`
    - [x] `open_pr_job` → `OrchestratorService.open_protocol_pr`
  - Keep job payloads and event shapes stable where possible.

- [ ] **Move orchestration logic out of `codex_worker`**
  - Gradually migrate planning/decomposition/QA/loop/trigger logic into
    `OrchestratorService`, `SpecService`, `DecompositionService`, and `QualityService`.
  - Leave `codex_worker` as a thin adapter (or retire it once all callers use services).

- [ ] **Service-level tests**
  - Add focused tests for each service:
    - Orchestrator: protocol lifecycle transitions and policy behaviour.
    - Execution: correct engine/model selection and output handling.
    - Quality: QA policy handling and verdict propagation.
    - Onboarding: project creation and workspace/onboarding flows.
    - Spec: spec build/validate + step creation.
  - Ensure tests do not depend on legacy worker internals.

- [ ] **Docs and migration notes**
  - Update `docs/orchestrator.md` and `docs/architecture.md` to reference the
    services layer as the main integration surface.
  - Add short migration notes for contributors: “use services, not workers”.

## Current focus

- Stabilize the initial `tasksgodzilla.services.*` APIs.
- Identify and document the first API/CLI endpoints to migrate to services.
