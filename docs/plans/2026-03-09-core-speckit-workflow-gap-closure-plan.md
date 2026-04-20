# Core SpecKit Workflow Gap-Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the missing real-workflow coverage and highest-risk logic gaps in the per-project SpecKit workspace flow, with the first slice centered on exported Windmill SpecKit flows and their backend wrappers.

**Architecture:** Treat the project-scoped SpecKit lifecycle as the canonical workflow: `init -> specify -> clarify -> plan -> tasks -> checklist/analyze -> implement`. Tighten contracts at the Windmill flow and API-wrapper layer first, then harden backend path resolution and workflow semantics, then add real integration and live coverage on top of those repaired contracts.

**Tech Stack:** FastAPI, pytest, Windmill JSON flows, Python wrapper scripts, SQLite/Postgres-backed DevGodzilla services

---

### Task 1: Save the workflow assumptions in code-facing docs

**Files:**
- Modify: `docs/plans/2026-03-09-core-speckit-workflow-gap-closure-plan.md`
- Reference: `devgodzilla/api/routes/project_speckit.py`
- Reference: `devgodzilla/services/specification.py`

**Step 1: Confirm the canonical workflow assumptions in this plan**

Document and keep fixed for this execution batch:
- project-scoped SpecKit routes are the source of truth
- Windmill `*_api.py` scripts are thin transport wrappers, not business-logic owners
- `implement` must produce or reuse exactly one protocol/bootstrap result for a spec run
- live workflow coverage must assert `spec_run_id`, `worktree_path`, artifact paths, and protocol linkage

**Step 2: Keep this plan updated only if implementation scope changes materially**

Run: `sed -n '1,260p' docs/plans/2026-03-09-core-speckit-workflow-gap-closure-plan.md`
Expected: Header, goal, architecture, and first tasks are present.

### Task 2: Add failing tests for exported Windmill flow contracts

**Files:**
- Create: `tests/test_devgodzilla_windmill_flow_contracts.py`
- Reference: `windmill/flows/devgodzilla/brownfield_feature.flow.json`
- Reference: `windmill/flows/devgodzilla/spec_to_protocol.flow.json`
- Reference: `windmill/scripts/devgodzilla/sync_tasks_api.py`

**Step 1: Write the failing contract tests**

Add tests that prove:
- every exported `u/devgodzilla/*` script in product flows only receives parameters accepted by its `main(...)` wrapper
- `brownfield_feature.flow.json` forwards `overwrite_existing` to `sync_tasks_api`
- `spec_to_protocol.flow.json` does not create a second protocol after `speckit_implement`

**Step 2: Run the focused tests to verify RED**

Run: `pytest -q tests/test_devgodzilla_windmill_flow_contracts.py`
Expected:
- FAIL because `sync_tasks_api` does not accept `overwrite_existing`
- FAIL because `spec_to_protocol.flow.json` still has a duplicate protocol bootstrap path

**Step 3: Implement the minimal fixes**

- make `sync_tasks_api.main(...)` accept `overwrite_existing`
- switch `sync_tasks_api` to the shared `_api` helper instead of hardcoded `requests` + fixed base URL
- change `spec_to_protocol.flow.json` so `protocol_start` consumes `results.speckit_implement.protocol_id`
- remove the redundant `create_protocol` step from `spec_to_protocol.flow.json`

**Step 4: Re-run the focused tests to verify GREEN**

Run: `pytest -q tests/test_devgodzilla_windmill_flow_contracts.py`
Expected: PASS.

### Task 3: Add a service/API regression test for single protocol bootstrap semantics

**Files:**
- Modify: `tests/test_devgodzilla_project_speckit_api.py`
- Modify: `tests/test_devgodzilla_protocol_from_spec.py`
- Reference: `devgodzilla/services/specification.py`

**Step 1: Write the failing regression test**

Add coverage showing that:
- project-scoped `implement` returns `protocol_id`, `protocol_root`, and `step_count`
- the intended flow contract is to reuse that protocol bootstrap instead of creating a second protocol from the same spec run

**Step 2: Run the focused tests to verify RED when semantics drift**

Run: `pytest -q tests/test_devgodzilla_project_speckit_api.py tests/test_devgodzilla_protocol_from_spec.py -k 'implement or from_spec'`
Expected: current tests may partially pass, but the new semantic assertion should fail before the fix if duplicate bootstrap behavior remains encoded in flow coverage.

**Step 3: Implement the minimal semantic repair**

- keep `SpecificationService.run_implement(...)` as the protocol/bootstrap owner for the SpecKit flow
- keep `/protocols/from-spec` as a separate explicit API path, not a second automatic step in `spec_to_protocol.flow.json`

**Step 4: Re-run the focused tests to verify GREEN**

Run: `pytest -q tests/test_devgodzilla_project_speckit_api.py tests/test_devgodzilla_protocol_from_spec.py -k 'implement or from_spec'`
Expected: PASS.

### Task 4: Harden SpecRun context resolution for per-project workspaces

**Files:**
- Modify: `devgodzilla/services/specification.py`
- Modify: `tests/test_devgodzilla_speckit.py`
- Modify: `tests/test_devgodzilla_spec_run_statuses.py`

**Step 1: Write the failing test**

Add a test proving that relative `spec_path`, `plan_path`, or `tasks_path` can still resolve to the correct `SpecRun.worktree_path` when `spec_run_id` is omitted.

**Step 2: Run the focused test to verify RED**

Run: `pytest -q tests/test_devgodzilla_speckit.py tests/test_devgodzilla_spec_run_statuses.py -k 'resolve_spec_run_context or worktree_path'`
Expected: FAIL because `_resolve_spec_run_context()` falls back to the project root for relative stored-path lookups.

**Step 3: Write the minimal implementation**

- normalize candidate paths against the project root before matching stored paths
- compare both raw stored paths and project-root-resolved absolute paths
- return the matched `SpecRun.worktree_path` whenever any stored artifact path resolves to the same file

**Step 4: Re-run the focused test to verify GREEN**

Run: `pytest -q tests/test_devgodzilla_speckit.py tests/test_devgodzilla_spec_run_statuses.py -k 'resolve_spec_run_context or worktree_path'`
Expected: PASS.

### Task 5: Repair `/speckit/workflow` contract semantics

**Files:**
- Modify: `devgodzilla/api/routes/speckit.py`
- Modify: `tests/test_devgodzilla_project_speckit_api.py` or create a focused workflow test

**Step 1: Write the failing API test**

Add a test for `skip_existing` that proves the route either:
- reuses existing artifacts when the flag is true, or
- no longer advertises the flag in the request model/route contract

**Step 2: Run the focused test to verify RED**

Run: `pytest -q tests/test_devgodzilla_project_speckit_api.py -k workflow`
Expected: FAIL because `skip_existing` is currently ignored.

**Step 3: Implement the minimal fix**

Recommended approach:
- honor `skip_existing` by short-circuiting stages whose artifacts already exist for the same `spec_run_id` or artifact path
- if that is too large for the slice, remove the flag from the public request model and route documentation in the same change

**Step 4: Re-run the focused test to verify GREEN**

Run: `pytest -q tests/test_devgodzilla_project_speckit_api.py -k workflow`
Expected: PASS.

### Task 6: Add a real-agent integration test for the real project-scoped SpecKit lifecycle

**Files:**
- Create: `tests/test_devgodzilla_project_speckit_integration.py`
- Reference: `devgodzilla/api/routes/project_speckit.py`
- Reference: `devgodzilla/services/specification.py`

**Step 1: Write the failing integration test**

Build a temp repo + real DB test that performs:
- create project with `local_path`
- `init`
- `specify`
- `plan`
- `tasks`
- optional `clarify` / `checklist` / `analyze`
- `implement`

Assert:
- one `spec_run_id` flows through the lifecycle
- `worktree_path` is stable
- artifact paths exist and belong to the expected worktree
- generated artifacts are materially updated by a real engine, not left as template placeholders
- `implement` yields one linked protocol/bootstrap result

Use a real engine (`opencode` today, or another engine only after it is registered in DevGodzilla) with the dev GLM-5 model path instead of `dummy`, because `dummy` cannot validate end-to-end artifact generation.

**Step 2: Run the focused test to verify RED**

Run: `pytest -q tests/test_devgodzilla_project_speckit_integration.py`
Expected: FAIL until the contract repairs above are in place.

**Step 3: Write the minimal implementation needed for GREEN**

Only fix behavior actually required by this end-to-end lifecycle. Do not expand to brownfield delivery branches in this task.

**Step 4: Re-run the focused test to verify GREEN**

Run: `pytest -q tests/test_devgodzilla_project_speckit_integration.py`
Expected: PASS.

### Task 7: Extend the live harness with SpecKit lifecycle stages

**Files:**
- Modify: `tests/e2e/harness/live_cli.py`
- Modify: `tests/e2e/harness/scenario_loader.py`
- Modify: `tests/e2e/test_workflow_harness_live.py`
- Create: `tests/e2e/scenarios/live_speckit_<repo>.json`
- Modify: `tests/e2e/adapters/*.adapter.json`

**Step 1: Write the failing harness tests**

Add fast non-integration tests for new stage handlers:
- `speckit_init`
- `speckit_specify`
- `speckit_plan`
- `speckit_tasks`
- `speckit_implement`

Add assertions that stage metadata carries `spec_run_id`, `worktree_path`, `protocol_id`, and artifact paths forward.

**Step 2: Run the harness unit tests to verify RED**

Run: `pytest -q tests/e2e/test_harness_live_cli.py tests/e2e/test_workflow_harness_live.py -k speckit`
Expected: FAIL because no SpecKit stages or assertions exist yet.

**Step 3: Implement the minimal harness slice**

- register new stage handlers in `build_live_cli_stage_handlers()`
- persist returned SpecKit metadata in `HarnessRunContext.metadata`
- strengthen assertions to validate artifact linkage, not just existence
- add one dedicated live SpecKit scenario per repo family only where the expectations differ materially

**Step 4: Re-run the harness unit tests to verify GREEN**

Run: `pytest -q tests/e2e/test_harness_live_cli.py tests/e2e/test_workflow_harness_live.py -k speckit`
Expected: PASS.

### Task 8: Upgrade the live Windmill integration test from smoke to one real SpecKit flow

**Files:**
- Modify: `tests/test_devgodzilla_windmill_live_integration.py`
- Reference: `windmill/flows/devgodzilla/brownfield_feature.flow.json`
- Reference: `windmill/flows/devgodzilla/onboard_to_tasks.flow.json`

**Step 1: Write the failing live integration assertion**

Extend the opt-in live test so it runs one exported SpecKit flow and asserts:
- returned `spec_path`, `plan_path`, and `tasks_path`
- returned `protocol_id` or equivalent bootstrap metadata when the chosen flow includes implementation
- job completion with result payload, not just a successful `list_projects` script

**Step 2: Run the opt-in live test to verify RED**

Run: `DEVGODZILLA_RUN_LIVE_WINDMILL_TESTS=1 pytest -q tests/test_devgodzilla_windmill_live_integration.py -v`
Expected: FAIL until the flow and wrapper contracts are fixed and the live assertion is expanded.

**Step 3: Implement the minimal live-test changes**

- choose the exported flow with the fewest required inputs and clearest result contract
- keep the old health checks, then add one real SpecKit workflow invocation

**Step 4: Re-run the opt-in live test to verify GREEN**

Run: `DEVGODZILLA_RUN_LIVE_WINDMILL_TESTS=1 pytest -q tests/test_devgodzilla_windmill_live_integration.py -v`
Expected: PASS in a correctly bootstrapped live environment.

### Task 9: Run focused verification for the completed slices

**Files:**
- Verify only

**Step 1: Run fast targeted regression tests**

Run: `pytest -q tests/test_devgodzilla_windmill_flow_contracts.py tests/test_devgodzilla_project_speckit_api.py tests/test_devgodzilla_protocol_from_spec.py tests/test_devgodzilla_speckit.py tests/test_devgodzilla_spec_run_statuses.py tests/e2e/test_harness_live_cli.py tests/e2e/test_workflow_harness_live.py`
Expected: all non-live tests in the implemented slice pass.

**Step 2: Run the repo-default backend suite**

Run: `scripts/ci/test.sh`
Expected: existing `tests/test_devgodzilla_*.py` suite passes with no new failures from the SpecKit changes.

**Step 3: Run opt-in live verification only when environment is present**

Run:
- `DEVGODZILLA_RUN_E2E_HARNESS=1 pytest -q tests/e2e/test_workflow_harness_live.py -v`
- `DEVGODZILLA_RUN_LIVE_WINDMILL_TESTS=1 pytest -q tests/test_devgodzilla_windmill_live_integration.py -v`

Expected: pass in a bootstrapped local stack; if unavailable, record that explicitly instead of claiming live success.
