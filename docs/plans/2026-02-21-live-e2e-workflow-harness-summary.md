# Live E2E Workflow Harness Plan Summary
Date: 2026-02-21

## Goal
Add a live pytest-based harness that can onboard GitHub repositories and verify full DevGodzilla workflows end-to-end, while fixing path/folder misalignment risks in core services.

## What Will Be Built
1. Path hardening in core config/services:
   - remove hardcoded onboarding script path usage,
   - formalize path contract and startup validation,
   - make Windmill import resources declarative.
2. Reusable E2E harness framework under `tests/e2e/harness/`:
   - preflight + auto-start infra,
   - JSON scenario/adapters loader,
   - stage runner,
   - assertion/diagnostics helpers.
3. JSON artifacts:
   - `schemas/e2e-workflow-harness.schema.json`,
   - scenario manifests,
   - adapter manifests for differing repo layouts.
4. Live integration entrypoint:
   - `tests/e2e/test_workflow_harness_live.py`.
5. CI automation:
   - nightly and manual job via `scripts/ci/test-harness-live.sh`.

## Locked Decisions
1. Live-only harness.
2. Allowlist repos + override, with the allowlist coming from GitHub owner `ilyafedotov-ops`.
3. Full feature flow validation (spec -> protocol -> worktree -> steps -> artifacts).
4. Contract + adapters for layout differences.
5. JSON schema + JSON manifests.
6. Auto-start infra.
7. Persistent workspace.
8. Nightly/manual CI schedule.
9. Bounded retries with backoff.

## Initial Default Coverage
Small stable set (3 repos) from GitHub owner `ilyafedotov-ops` with mixed layouts, each validating:
1. `https://github.com/ilyafedotov-ops/test-glm5-demo`
2. `https://github.com/ilyafedotov-ops/SimpleAdminReporter`
3. `https://github.com/ilyafedotov-ops/demo-spring`
4. Onboarding and discovery outputs.
5. Feature-add workflow.
6. Worktree/branch integrity.
7. Protocol execution and artifacts.

## GitHub Source Inputs
1. `HARNESS_GITHUB_OWNER` defaulting to `ilyafedotov-ops` (`https://github.com/ilyafedotov-ops`).
2. `HARNESS_GITHUB_REPOS` defaulting to `test-glm5-demo,SimpleAdminReporter,demo-spring`.
3. `HARNESS_REPO_URL_OVERRIDE` for ad-hoc one-off runs.

## Deliverables
1. Detailed plan doc (this summary references it):
   - `docs/plans/2026-02-21-live-e2e-workflow-harness-plan.md`
2. Summary doc:
   - `docs/plans/2026-02-21-live-e2e-workflow-harness-summary.md`

## Execution Update (2026-02-21)
1. Path contract enforcement is now wired into API and CLI startup paths (fail-fast with diagnostics).
2. Live harness repo matrix supports allowlist filtering via `HARNESS_GITHUB_REPOS`.
3. Preflight now enforces matrix coverage (3 repos) for full runs while still allowing focused single-scenario runs.
4. Harness execution engine is configurable via `HARNESS_STEP_ENGINE` (`opencode` default, `dummy` supported).
5. Nightly/manual automation is added via `.github/workflows/live-harness.yml`.
6. Harness diagnostics are uploaded from `runs/harness/**` in CI.
7. CI operations doc now includes runbook for:
   - running live harness locally,
   - using the three seeded `ilyafedotov-ops` repos,
   - adding new scenario/adapter manifests.
8. Seeded live scenario stage timeouts are raised to `2700s` (45 minutes) for onboard/planning/execution.
