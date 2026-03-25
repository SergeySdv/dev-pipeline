# Spec-Driven Workflow Gap Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the highest-impact gaps in the project onboarding and SpecKit-driven workflow so the core path from onboarding through execution and review behaves consistently across backend, frontend, and tests.

**Architecture:** Treat the core product path as one workflow: `onboarding -> SpecKit -> protocol bootstrap -> sprint/execution -> review`. Fix semantic drift first, then fix frontend request-contract and workflow-state bugs, then add deterministic verification around the repaired path. Prefer additive API changes and reuse existing services/components instead of inventing a parallel flow.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy/SQLite, Next.js 16, React Query, SWR, Vitest, pytest

---

## Context and Constraints

- Primary scope is the core spec-driven path only. Broader ops/admin pages are out of scope unless they block that path.
- Existing route names should be preserved where reasonable; use additive response/request changes before breaking renames.
- Follow TDD for each behavior change.
- Do not touch `Origins/`.
- Ignore existing untracked `test-output/` content.

## Phase Order

1. Backend contract correctness for protocol/spec workflow.
2. Frontend workflow correctness for routing and filter/validation bugs.
3. Deterministic test coverage for the repaired slice.
4. Only after that, broader flow orchestration and review-surface improvements.

## Task 1: Save the workflow assumptions in code-facing docs

**Files:**
- Modify: `docs/plans/2026-03-08-spec-driven-workflow-gap-closure-plan.md`
- Reference: `frontend/app/projects/[id]/page.tsx`
- Reference: `devgodzilla/api/routes/protocols.py`

**Step 1: Confirm the canonical route shape and workflow stages in this plan**

Document these defaults explicitly in this plan file:
- existing project execution routes remain valid; do not rewrite them based on assumption
- `run_next_step` means execute, not preview
- `implement` means execution bootstrap/readiness, not metadata-only scaffolding

**Step 2: Keep this plan updated if implementation scope changes**

Run: `sed -n '1,260p' docs/plans/2026-03-08-spec-driven-workflow-gap-closure-plan.md`
Expected: Header, goal, phase order, and first-slice tasks are present.

## Task 2: Fix clarification filter semantics end to end

**Files:**
- Modify: `frontend/app/projects/[id]/components/clarifications-tab.tsx`
- Modify: `frontend/app/protocols/[id]/components/clarifications-tab.tsx`
- Modify: `frontend/lib/api/hooks/use-projects.ts`
- Modify: `frontend/lib/api/hooks/use-protocols.ts`
- Test: `frontend/__tests__/features` or a new focused hook/component test file

**Step 1: Write the failing frontend test**

Create a focused test that proves selecting `all` does not append `status=all` to the request URL.

**Step 2: Run the focused test to verify RED**

Run: `cd frontend && pnpm vitest --run <new-test-file>`
Expected: FAIL because `status=all` is still emitted.

**Step 3: Implement the minimal fix**

- Treat `all` the same as an undefined status in the tabs and hooks.
- Preserve explicit status filtering for `open` and `answered`.

**Step 4: Re-run the focused test to verify GREEN**

Run: `cd frontend && pnpm vitest --run <new-test-file>`
Expected: PASS.

**Step 5: Run the nearby frontend tests**

Run: `cd frontend && pnpm vitest --run frontend/__tests__/features/event-feed-properties.test.tsx`
Expected: PASS with no regressions from hook changes.

## Task 3: Add project-level SpecKit initialization from the UI

**Files:**
- Modify: `frontend/app/projects/[id]/components/spec-tab.tsx`
- Test: new focused regression test under `frontend/__tests__/workflow`

**Step 1: Write the failing UI regression test**

Add a test that asserts the uninitialized project spec tab exposes an `Initialize SpecKit` action instead of only CLI instructions.

**Step 2: Run the focused test to verify RED**

Run: `cd frontend && pnpm vitest --run <new-init-test-file>`
Expected: FAIL because the tab currently only renders CLI guidance.

**Step 3: Implement the minimal UI fix**

- Reuse the existing `useInitSpecKit` mutation.
- Add a primary initialize button in the uninitialized state.
- Keep the CLI command visible as fallback documentation.

**Step 4: Re-run the focused test to verify GREEN**

Run: `cd frontend && pnpm vitest --run <new-init-test-file>`
Expected: PASS.

**Step 5: Keep the UX aligned with the existing wizard**

Mirror the success/error behavior already used by `frontend/components/wizards/generate-specs-wizard.tsx`.

## Task 4: Align spec generation validation with backend rules

**Files:**
- Modify: `frontend/components/wizards/generate-specs-wizard.tsx`
- Test: new wizard validation test under `frontend/__tests__/features` or `frontend/__tests__/workflow`
- Reference: `devgodzilla/api/routes/speckit.py`

**Step 1: Write the failing validation test**

Add a test proving descriptions shorter than 10 characters are rejected client-side.

**Step 2: Run the focused test to verify RED**

Run: `cd frontend && pnpm vitest --run <new-validation-test-file>`
Expected: FAIL because the wizard currently allows 5+ characters.

**Step 3: Implement the minimal validation fix**

- Change the UI minimum from 5 to 10.
- Keep copy/error text synchronized with backend validation.

**Step 4: Re-run the focused test to verify GREEN**

Run: `cd frontend && pnpm vitest --run <new-validation-test-file>`
Expected: PASS.

## Task 5: Make planner context a real backend contract

**Files:**
- Modify: `devgodzilla/api/routes/speckit.py`
- Modify: `devgodzilla/api/routes/project_speckit.py` if needed for parity
- Modify: `devgodzilla/services/specification.py`
- Test: `tests/test_devgodzilla_project_speckit_api.py` and/or a new service/API test
- Reference: `frontend/components/wizards/design-solution-wizard.tsx`

**Step 1: Write the failing backend test**

Add a test that sends `context` to plan generation and verifies it is accepted and used in prompt/planning context preparation.

**Step 2: Run the focused backend test to verify RED**

Run: `.venv/bin/pytest -q tests/test_devgodzilla_project_speckit_api.py -k context`
Expected: FAIL because the request model drops or ignores `context`.

**Step 3: Implement the minimal backend change**

- Add optional `context` to the plan request models.
- Thread it through to `SpecificationService.run_plan(...)`.
- Append it to the planning prompt context in a clearly delimited section.

**Step 4: Re-run the focused backend test to verify GREEN**

Run: `.venv/bin/pytest -q tests/test_devgodzilla_project_speckit_api.py -k context`
Expected: PASS.

## Task 6: Make `run_next_step` semantics honest and executable

**Files:**
- Modify: `devgodzilla/api/routes/protocols.py`
- Modify: relevant orchestration/execution service module if required
- Test: `tests/test_devgodzilla_protocol_state_properties.py` and/or a new API test

**Step 1: Write the failing backend test**

Add an API test proving `POST /protocols/{id}/actions/run_next_step` causes a runnable pending step to transition out of `pending` and/or creates the execution side effect expected by the current product wording.

**Step 2: Run the focused backend test to verify RED**

Run: `.venv/bin/pytest -q tests/test_devgodzilla_protocol_state_properties.py -k run_next_step`
Expected: FAIL because the endpoint currently only returns an id.

**Step 3: Implement the minimal semantic repair**

Recommended approach:
- Keep the existing route.
- Make it invoke the existing step execution path for the selected runnable step.
- If a preview-only use case is still needed, add a new read-only endpoint instead of leaving the mutating action misleading.

**Step 4: Re-run the focused backend test to verify GREEN**

Run: `.venv/bin/pytest -q tests/test_devgodzilla_protocol_state_properties.py -k run_next_step`
Expected: PASS.

## Task 7: Start the first implementation slice in the UI from the repaired contracts

**Files:**
- Modify: `frontend/components/wizards/design-solution-wizard.tsx`
- Modify: `frontend/components/wizards/generate-specs-wizard.tsx`
- Modify: `frontend/components/wizards/implement-feature-wizard.tsx`
- Test: targeted wizard interaction tests

**Step 1: Write the failing tests for the repaired request/route behavior**

Add focused tests that cover:
- plan wizard sends real `context`
- project spec tab can initialize SpecKit directly
- clarification filter omits `all`

**Step 2: Run the focused tests to verify RED**

Run: `cd frontend && pnpm vitest --run <wizard-test-files>`
Expected: FAIL before implementation.

**Step 3: Implement only the minimal UI changes required for the repaired slice**

Do not broaden scope yet to auth overhaul, feature-component migration, or runs-page cleanup.

**Step 4: Re-run the focused tests to verify GREEN**

Run: `cd frontend && pnpm vitest --run <wizard-test-files>`
Expected: PASS.

## Task 8: Add deterministic verification for the repaired slice

**Files:**
- Modify: `tests/test_devgodzilla_project_speckit_api.py`
- Modify: `tests/test_devgodzilla_protocol_state_properties.py`
- Modify or create: focused frontend Vitest tests
- Optional follow-up docs: CI scripts after the first slice is stable

**Step 1: Run the focused backend verification set**

Run: `.venv/bin/pytest -q tests/test_devgodzilla_project_speckit_api.py tests/test_devgodzilla_protocol_state_properties.py tests/test_devgodzilla_specifications_link_api.py`
Expected: All pass.

**Step 2: Run the focused frontend verification set**

Run: `cd frontend && pnpm test:run`
Expected: PASS.

**Step 3: Record remaining follow-up work without expanding this slice**

Leave these for the next execution batch:
- duplicate `/speckit/*` and `/projects/{id}/speckit/*` surface consolidation
- real implementation bootstrap semantics for `/speckit/implement`
- project workflow agent assignment wiring
- runs list/detail placeholder cleanup
- auth guard / unauthorized handling
- browser e2e + CI wiring

## Task 9: Second slice after the first passes

**Files:**
- Modify: `devgodzilla/api/routes/speckit.py`
- Modify: `devgodzilla/services/specification.py`
- Modify: `frontend/app/projects/[id]/components/spec-tab.tsx`
- Modify: `frontend/app/specifications/[id]/page.tsx`
- Test: new backend and frontend tests for implement/review semantics

**Step 1: Write failing tests for `implement` behavior and review visibility**

Test for:
- `implement` returns execution-ready linkage, not only metadata scaffolding
- project/spec pages show checklist/analysis/implementation linkage coherently

**Step 2: Run focused tests to verify RED**

Run backend and frontend focused commands for the new tests.
Expected: FAIL.

**Step 3: Implement the minimal end-to-end bootstrap/review behavior**

- either expand `implement` additively or rename the UI action honestly if semantics must remain scaffold-only
- prefer additive expansion

**Step 4: Re-run focused tests to verify GREEN**

Run backend and frontend focused commands for the new tests.
Expected: PASS.

## Verification Checklist Before Claiming Completion

- Run the exact focused pytest commands used by the changed backend slice.
- Run the exact focused Vitest commands used by the changed frontend slice.
- If any command fails, report the real status and stop claiming the slice is done.
- Before moving to browser e2e or CI wiring, make sure the first slice is green locally.

## Suggested Commit Boundaries

1. `fix: align clarification filters with backend semantics`
2. `fix: add project spec-tab initialization action`
3. `fix: pass planning context through speckit plan contract`
4. `fix: make protocol run_next_step action execute work`
5. `test: add focused regression coverage for repaired workflow slice`
