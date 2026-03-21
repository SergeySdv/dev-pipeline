# Task Cycle Runtime UI Review And Test Plan

> Status: Proposed
> Scope: independent validation plan for the task-cycle runtime UI and backend runtime projection
> Last updated: 2026-03-20
> Companion doc: `docs/plans/TASK-CYCLE-RUNTIME-UI-IMPLEMENTATION-PLAN.md`

## Goal

Define what independent review and test agents should validate for the runtime UI feature so the implementation is judged by user value and correctness, not only by whether the code compiles.

The review and test agents should behave as independent evaluators, not as extensions of the implementation agent.

## Feature Under Test

The feature introduces a unified work-item runtime experience that shows:

- current business stage
- active agents
- Windmill execution detail as advanced metadata
- stage artifacts
- live activity and blocking reasons

## Independent Review Agent

### Role

The review agent should evaluate whether the feature is coherent as a product and technically faithful to the intended workflow.

### What the review agent must check

- the default UI is stage-first, not raw-run-first
- the user can understand current state without needing protocol DAG knowledge
- the runtime drawer or equivalent drill-down is understandable and not overloaded
- business stages are mapped consistently from backend/runtime state
- Windmill details exist but do not dominate the primary workflow surface
- artifacts are grouped by stage, not just dumped as file paths
- active-agent display is accurate and not misleading
- blocking reasons are explicit and actionable
- clarification state is distinguishable from general failure
- deep context reuse, if implemented, is visible and not silently inferred

### Review focus questions

- Can a first-time operator tell what is happening now?
- Can they identify what was already done?
- Can they see what output each stage produced?
- Can they tell whether the system is waiting, blocked, or failed?
- Does the UI expose technical detail progressively instead of all at once?
- Does the backend contract support stable UI rendering without frontend guesswork?

### Review findings should flag

- ambiguous naming between business stages and Windmill modules
- missing backend aggregation forcing frontend joins
- hidden or misleading agent activity
- unclear ownership when multiple agents appear in one stage
- artifacts that exist in backend but are invisible in UI
- states that collapse `blocked`, `waiting`, and `failed` into one generic badge
- context reuse behavior that could create stale or misleading user expectations

## Independent Test Agent

### Role

The test agent should validate correctness, state transitions, and regression safety across backend and frontend.

### Backend contract tests

The test agent should validate:

- `GET /work-items/{id}/runtime` returns stable structure
- stage ordering is deterministic
- active stage and stage status match runtime state
- active agents are correctly populated
- stage artifacts are grouped correctly
- missing artifacts do not crash runtime projection
- Windmill linkage is present when available and absent safely when not
- blocking reasons appear for clarifications, policy findings, and failed stages

### Frontend tests

The test agent should validate:

- work-item list shows `active_stage`
- work-item list shows active agent summary
- runtime drawer opens from a card
- runtime drawer renders stage timeline
- runtime drawer renders artifacts grouped by stage
- runtime drawer updates on relevant event-stream activity
- advanced technical detail is hidden by default and expandable
- archived/canceled items remain read-only

### Event-stream tests

The test agent should validate:

- stage start event updates active stage
- stage completion event updates the correct stage only
- artifact-created event updates artifact list without full page reload
- out-of-order or duplicate events do not corrupt visible state
- dropped SSE connection degrades gracefully to refetch/polling

### Artifact tests

The test agent should validate:

- `context_pack.md` can be opened from context stage
- review report can be opened from review stage
- test report can be opened from QA stage
- missing artifacts render as explicit missing state, not empty success
- truncated artifact content is labeled clearly

## Scenario Matrix

### Happy path

1. work item is created
2. context stage runs and completes
3. implement stage runs and completes
4. review passes
5. QA passes
6. PR-ready state is reached

Expected UI result:

- all stages visible in order
- active stage moves correctly
- artifacts appear under the correct stages
- final state clearly shows `PR Ready`

### Review failure path

1. implement succeeds
2. review fails
3. rework pack is generated

Expected UI result:

- review stage marked failed
- work item status indicates rework needed
- review findings visible
- rework artifact visible

### QA failure path

1. review passes
2. QA fails

Expected UI result:

- QA stage marked failed
- QA findings visible
- work item returns to rework-needed state

### Clarification path

1. context build detects non-code gap
2. clarification is opened

Expected UI result:

- stage marked waiting or blocked for clarification
- user sees clarification reason
- state is distinct from generic failure

### Context reuse path

1. work item reuses epic baseline context
2. incremental refresh runs for touched area

Expected UI result:

- UI shows that baseline context was reused
- UI shows what was refreshed
- user is not misled into thinking a full context search ran

### Windmill unavailable or local fallback path

1. runtime proceeds without Windmill linkage

Expected UI result:

- UI still shows business stages
- advanced technical detail degrades gracefully
- no broken Windmill-specific links or assumptions

## Review And Test Outputs

### Review agent output

The review agent should produce:

- findings ordered by severity
- affected surfaces
- user-facing risk summary
- API/design mismatch notes
- recommendation: approve, revise, or block

### Test agent output

The test agent should produce:

- executed scenarios
- passed/failed cases
- contract mismatches
- event-ordering issues
- UI regression notes
- untested risk areas

## Acceptance Gates

The feature should not be considered done unless:

- runtime state is understandable without reading logs
- stage and agent info stay consistent between backend and frontend
- artifacts are discoverable from the runtime UI
- event-driven updates do not produce stale or contradictory states
- failed, blocked, and waiting states are visually and semantically distinct

## Suggested Test Coverage

### Backend

- schema serialization tests for runtime projection
- task-cycle runtime aggregation tests
- event-to-runtime update tests
- artifact grouping tests

### Frontend

- component tests for work-item cards
- drawer rendering tests
- event update tests
- artifact panel tests
- empty/missing state tests

### End-to-end

- start brownfield run
- run through context -> implement -> review -> QA
- verify runtime UI transitions
- verify artifact visibility at each stage

## Non-Goals

- validating the correctness of the underlying coding agent output itself
- full load testing of SSE infrastructure
- Windmill internals beyond the UI/runtime projection contract
