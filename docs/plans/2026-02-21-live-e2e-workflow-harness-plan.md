# Live E2E Workflow Harness and Path-Alignment Hardening Plan
Date: 2026-02-21
Owner: DevGodzilla Core
Status: In Progress

## 1. Objective
Build a reusable live E2E harness that can onboard suitable GitHub projects and validate full workflow coverage end-to-end, while eliminating current folder/file-location misalignment risks in core services.

## 2. Problem Statement
Current E2E coverage is partial and mostly opt-in/skipped, so path/layout misalignment breaks appear late. Core services also depend on implicit/hardcoded folder and file paths (Windmill script path, import layout, env file path, projects root), making onboarding and workflow execution fragile across repo layouts.

## 3. Success Criteria
1. Harness can run a full scenario from GitHub onboarding to executed workflow artifacts.
2. Harness validates:
   - onboarding/discovery/spec outputs,
   - feature addition flow,
   - worktree/branch lifecycle,
   - protocol plan/generate/step execution.
3. Path contract violations fail fast with explicit diagnostics.
4. Harness runs in automation (nightly + manual) with reproducible outputs.
5. New repo onboarding support requires only adapter/scenario JSON changes.

## 4. Scope

### In Scope
1. Config/path hardening in core services.
2. JSON-schema-driven live E2E harness in pytest.
3. Adapter-based layout handling for heterogeneous repositories.
4. Infra auto-start and bounded retry strategy.
5. CI wiring for nightly/manual live runs.

### Out of Scope
1. Replacing existing workflow engines or Windmill architecture.
2. Converting all existing tests to harness format immediately.
3. Running full live harness on every PR.

## 5. Constraints and Decisions (Locked)
1. Harness mode: Live-only.
2. Repo source: Allowlist + override, with allowlist populated from GitHub owner `ilyafedotov-ops`.
3. Primary interface: Pytest integration suite.
4. Feature flow depth: Full flow.
5. Layout strategy: Contract + adapters.
6. Config format: JSON schema + JSON manifests.
7. Services exercised: GitHub + DevGodzilla + Windmill.
8. Infra policy: Auto-start infra from harness.
9. Workspace policy: Persistent workspace.
10. CI policy: Nightly + manual.
11. Retry policy: Bounded retries with backoff.
12. Initial repo matrix: Small stable set (3 repos) selected from GitHub owner `ilyafedotov-ops`:
    - `test-glm5-demo`
    - `SimpleAdminReporter`
    - `demo-spring`
13. Runtime budget: live stages may run up to 45 minutes (`2700` seconds) for onboard/planning/execution.

## 6. Current-State Findings (Key Risks)
1. Hardcoded Windmill onboarding path (`u/devgodzilla/project_onboard_api`) in onboarding queue.
2. Fixed import assumptions for `windmill/scripts`, `windmill/flows`, app files.
3. Implicit env/token file location assumptions.
4. Projects-root path assumptions affecting clone/resolve behavior.
5. Existing E2E tests use skip gates and do not continuously enforce full live path.

## 7. Target Architecture

### 7.1 Path Contract Layer
Add explicit path contract configuration and startup validation:
- `windmill_onboard_script_path`
- `windmill_import_root`
- normalized `projects_root`
- validation of required files/directories before workflow execution

### 7.2 Harness Components
Create `tests/e2e/harness/`:
1. `preflight.py`
   - service availability checks
   - infra auto-start hooks
   - auth/token/CLI prerequisites
2. `scenario_loader.py`
   - load + schema-validate scenario/adapters
3. `runner.py`
   - execute scenario stages and polling
4. `assertions.py`
   - standardized assertions + diagnostics capture

### 7.3 Configuration Artifacts
1. `schemas/e2e-workflow-harness.schema.json`
2. `tests/e2e/scenarios/*.json`
3. `tests/e2e/adapters/*.adapter.json`

## 8. Public Interface and Type Additions

### 8.1 Config Additions
In `devgodzilla/config.py`:
- `windmill_onboard_script_path: str`
- `windmill_import_root: str`
- strict normalization/validation for `projects_root`

### 8.2 Scenario Schema (JSON)
Top-level fields:
- `scenario_id`
- `repo` (`owner`, `name`, `url`, `default_branch`, optional `pin_ref`)
- `adapter_id`
- `workflow` (ordered stage config)
- `expectations`
- `timeouts`
- `retries`
- `source` (`github_user_allowlist` by default)

### 8.3 Adapter Schema (JSON)
- `required_paths`
- `path_aliases`
- `discovery_expectations`
- `artifact_patterns`
- `worktree_branch_expectations`

## 9. Scenario Flow (Per Run)
1. Preflight + infra auto-start.
2. Resolve repo from `ilyafedotov-ops` allowlist (or explicit override).
3. Clone/update repo in persistent harness workspace.
4. Create project and onboard.
5. Validate discovery/spec artifacts.
6. Execute feature-add flow:
   - spec creation
   - protocol creation
   - worktree creation
   - plan/generate
   - run steps
7. Validate protocol status, artifacts, logs, and branch/worktree integrity.
8. Emit diagnostics bundle on failure.

## 10. Detailed Work Breakdown

### Phase A: Path Hardening
1. Replace hardcoded onboarding script path usage with config.
2. Add path contract validator and integrate into startup/service init.
3. Refactor Windmill import script to use declarative manifest.
4. Add unit tests for path contract + overrides.

### Phase B: Harness Foundation
1. Add schema and loader.
2. Implement preflight + infra boot.
3. Implement runner skeleton with stage orchestration.
4. Implement standardized assertion helpers.

### Phase C: Scenario/Adapter Implementation
1. Add 3 stable default scenarios sourced from GitHub owner `ilyafedotov-ops`:
   - `tests/e2e/scenarios/live_onboarding_test_glm5_demo.json`
   - `tests/e2e/scenarios/live_onboarding_simple_admin_reporter.json`
   - `tests/e2e/scenarios/live_onboarding_demo_spring.json`
2. Add corresponding adapters for layout differences.
3. Implement retries/backoff around transient operations.
4. Capture per-stage timing and diagnostics.

### Phase D: Pytest and CI Integration
1. Add `tests/e2e/test_workflow_harness_live.py` with scenario parameterization.
2. Add CI script `scripts/ci/test-harness-live.sh`.
3. Wire nightly and manual workflow jobs.
4. Add reporting artifact upload path.

## 11. Test Plan

### Unit-Level
1. Schema validation pass/fail cases.
2. Adapter path resolution behavior.
3. Retry/backoff behavior for transient/non-transient classes.
4. Path-contract validator messages and exit behavior.

### Integration-Level (Live)
1. Scenario completes successfully for each allowlisted repo.
2. Worktree path exists and maps to expected branch.
3. Protocol reaches terminal status with expected executed steps.
4. Artifacts and logs produced in expected locations.
5. Controlled transient failure recovers within retry budget.
6. Persistent failure yields diagnostics bundle and clear failure reason.

## 12. Failure Handling and Diagnostics
On any stage failure:
1. Save request/response snapshots.
2. Save protocol/step metadata and statuses.
3. Save Windmill job references and available logs.
4. Save local git/worktree state summary.
5. Output a single actionable failure summary + bundle path.

Diagnostics root:
`runs/harness/<run_id>/diagnostics/`

## 13. Rollout Plan
1. Merge path-hardening first.
2. Merge harness framework with one scenario behind integration marker.
3. Expand to 3 default scenarios.
4. Enable nightly/manual CI job.
5. Review flake rate for 1 week; tune retries/timeouts.
6. Document repo onboarding guide for adding new scenario/adapter.

## 14. GitHub Source Configuration (User Repositories)
1. Add harness configuration inputs:
   - `HARNESS_GITHUB_OWNER` (default: `ilyafedotov-ops`, from `https://github.com/ilyafedotov-ops`)
   - `HARNESS_GITHUB_REPOS` (comma-separated allowlist, e.g. `repo-a,repo-b,repo-c`)
   - `HARNESS_REPO_URL_OVERRIDE` (single-run override)
2. Scenario manifests should reference repos by `owner` + `name`; `url` is derived as `https://github.com/<owner>/<name>.git` unless explicitly provided.
3. Initial seeded scenarios must be created from three repos under `HARNESS_GITHUB_OWNER` (`ilyafedotov-ops` by default), chosen by:
   - repository accessibility and clone reliability,
   - varied folder/layout patterns to exercise adapter logic,
   - active default branch suitable for onboarding/protocol flows.
4. Preflight should fail fast when `HARNESS_GITHUB_REPOS` is empty, with a message asking to provide at least three repositories from `ilyafedotov-ops`.
5. If a configured repo is unavailable, harness marks scenario as failed with diagnostics and continues remaining scenarios when `continue_on_error=true`.
6. Seed `HARNESS_GITHUB_REPOS` default with:
   - `test-glm5-demo,SimpleAdminReporter,demo-spring`
7. Seed scenario repo URLs as:
   - `https://github.com/ilyafedotov-ops/test-glm5-demo.git`
   - `https://github.com/ilyafedotov-ops/SimpleAdminReporter.git`
   - `https://github.com/ilyafedotov-ops/demo-spring.git`

## 15. Risks and Mitigations
1. External instability (GitHub/network/Windmill):
   - bounded retries, explicit transient classification.
2. Slow runtime:
   - small initial matrix, nightly/manual only.
3. Environment drift:
   - strict preflight and fail-fast diagnostics.
4. Repo layout diversity:
   - adapter contract with required paths and aliases.

## 16. Acceptance Checklist
1. Configurable path contract implemented and tested.
2. No hardcoded onboarding path remains in queue service.
3. Harness schema + loader + runner + assertions implemented.
4. Three default live scenarios pass in stable environment.
5. Full feature-add/worktree/protocol lifecycle validated by harness.
6. Nightly/manual CI jobs configured.
7. Diagnostics bundle generated for failures.
8. Documentation added for adding repo scenarios/adapters.
