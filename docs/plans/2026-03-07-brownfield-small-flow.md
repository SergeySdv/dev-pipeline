# Brownfield Small Flow

## Goal

Make brownfield task execution in DevGodzilla produce smaller, safer, more maintainable code changes by enforcing structure in the workflow rather than relying on post-hoc prompt QA.

This plan is based on observed behavior in the current task-cycle flow:

- stage transitions work, but maintainability is weakly enforced
- prompt QA is too soft to represent real repository health
- artifact quality is inconsistent, which weakens auditability
- successful tasks can still leave confusing stale artifacts behind
- the system is better at finishing a task than proving the task was finished well

## Problem Statement

The current brownfield flow is operationally useful, but it does not consistently optimize for good code structure.

Current strengths:

- context, implement, review, QA, and PR-ready are explicit stages
- work items map well to existing `step_runs`
- runtime visibility is improving
- agents can complete useful work and generate artifacts

Current weaknesses:

- context packs focus on file collection more than architectural constraints
- implementation can proceed without a bounded edit contract
- review is mostly result-oriented, not structure-oriented
- QA can pass without running concrete repo checks
- artifact sets can be incomplete or misleading
- PR-ready can reflect workflow completion more than evidence quality

## Design Principle

Brownfield flow should optimize for:

1. narrow scope
2. explicit constraints
3. real repository validation
4. strong artifact traceability
5. maintainability as a first-class gate

The target is not “agent completed the task”.

The target is “agent completed a small, auditable, structurally sound change that a maintainer would actually merge”.

## Target Flow

Use seven operator-visible stages for brownfield delivery:

1. `Build Context`
2. `Plan`
3. `Implement`
4. `Review`
5. `QA`
6. `Refactor` when needed
7. `PR Ready`

`Refactor` is conditional. It appears only when implementation works functionally but the resulting code quality is below threshold.

## Stage Contracts

### 1. Build Context

The context stage should produce more than a file bundle.

Required outputs:

- task goal
- acceptance criteria
- allowed files to edit
- forbidden files or high-risk modules
- existing extension points
- nearby example files that represent the preferred style
- test commands
- architectural notes
- risk notes

The main improvement is to turn context into a constrained contract.

The agent should know:

- where to work
- where not to work
- what pattern to copy
- what boundaries must remain intact

### 2. Plan

Implementation should not start directly after context for brownfield tasks.

The plan stage should declare:

- files to modify
- files to create
- public API changes
- data model changes
- migration risk
- test plan
- rollback or failure risk

Hard rules:

- if the change touches too many files, fail and split the work item
- if the plan mixes unrelated concerns, fail and split the work item
- if the plan crosses module boundaries without justification, fail review early

This stage is the main guardrail against “agent solved it by editing half the repo”.

### 3. Implement

Implementation should remain focused on execution, but artifact capture must improve.

Required implement artifacts:

- actual `git diff`
- actual `git status`
- changed file summary
- execution log
- test command output

The system should fail the implement artifact set if:

- code changed but `changes.diff` is empty
- code changed but `git-status.txt` is empty
- logs claim files changed but the captured diff does not support that

This is essential for brownfield work because auditability matters almost as much as correctness.

### 4. Review

Review should explicitly assess maintainability, not just correctness.

The review stage should check:

- scope discipline
- module boundaries
- dependency direction
- function size
- file size
- nesting depth
- duplication
- hidden side effects
- naming clarity
- test relevance

Review verdicts should be:

- `passed`
- `passed_with_debt`
- `needs_refactor`
- `failed`

`needs_refactor` is important because it distinguishes “works but ugly” from “actually broken”.

### 5. QA

Prompt QA should remain optional and supplemental.

Brownfield QA should be primarily deterministic.

For Python repos, default gates should include:

- `pytest`
- `ruff`
- unused import check
- complexity check
- file-length check
- lightweight type/import smoke if configured

QA should not say “passed with high confidence” when only a prompt gate was skipped or when no real repo gate ran.

### 6. Refactor

This stage is only triggered when:

- functionality is correct
- tests pass
- structural quality is below threshold

The refactor stage should be narrow:

- reduce file size
- reduce function complexity
- isolate side effects
- extract helpers
- align with repo patterns

This gives the workflow a place to fix maintainability issues without pretending the entire task failed.

### 7. PR Ready

PR-ready should depend on artifact integrity and quality evidence, not just stage completion.

Required conditions:

- context artifacts exist
- plan exists
- implement artifacts are internally consistent
- review is `passed` or `passed_with_debt`
- QA ran real gates and passed
- no blocking clarifications remain
- no blocking policy findings remain
- stale rework artifacts are cleared or superseded explicitly

## New Quality Policy For Brownfield Tasks

To consistently produce better structured code, brownfield tasks should adopt these limits:

- max touched files per work item
- max file size threshold
- max function complexity threshold
- max nesting threshold
- max public API surface change per task

When a task exceeds these bounds, the system should prefer decomposition instead of allowing the task to sprawl.

## Artifact Rules

Artifacts should become part of the contract, not just byproducts.

### Required Artifact Quality

- `context_pack.json` must identify allowed files, test commands, and review focus
- `review_report.json` must distinguish correctness from maintainability
- `test_report.json` must list actual gates run
- `rework_pack.json` must be removed or superseded after success
- `changes.diff` and `git-status.txt` must reflect the real workspace state at the end of implement

### Anti-Patterns To Eliminate

- empty diff artifacts after successful code edits
- QA reports claiming confidence without deterministic checks
- stale rework artifacts on successful work items
- review reports that say “passed” without discussing structure

## Recommended Backend Changes

Main implementation area:

- `devgodzilla/services/task_cycle.py`

Recommended changes:

- add `plan` stage support and storage
- extend context pack generation with architectural constraints
- tighten implement artifact validation
- expand review schema to include maintainability findings
- make QA gate selection repo-aware and deterministic by default
- add refactor verdict/state support
- clear or supersede stale rework artifacts after success

## Recommended Frontend Changes

Main implementation areas:

- `frontend/app/projects/[id]/components/task-cycle-tab.tsx`
- `frontend/app/projects/[id]/components/task-cycle-runtime-dialog.tsx`
- `frontend/app/projects/[id]/components/settings-tab.tsx`

Recommended changes:

- surface plan stage in the brownfield flow
- distinguish functional pass from structural debt
- show actual QA gates run, not just a green status
- show artifact integrity warnings when diff/status evidence is missing
- make `PR Ready` visually dependent on evidence quality

## Rollout Plan

### Phase 1

Improve evidence quality without changing the whole flow:

- require real `git diff` and `git status` artifacts
- make QA report show actual gates run
- clear stale rework artifacts on success
- distinguish skipped QA from passed QA

### Phase 2

Add structure enforcement:

- add `Plan` stage
- add maintainability review checks
- add deterministic brownfield QA defaults

### Phase 3

Add quality recovery:

- introduce `needs_refactor`
- add optional `Refactor` stage
- support automatic task splitting when change scope is too large

## Success Criteria

This plan is successful when:

- brownfield tasks touch fewer files on average
- PR-ready work items have trustworthy diff/status artifacts
- QA reports reflect real repository validation
- maintainability issues are caught before PR-ready
- successful tasks produce code that follows existing repo patterns more often
- maintainers can trust brownfield task-cycle output without manually re-auditing every artifact

## Practical Recommendation

The first high-value change is not a new agent prompt.

It is this:

1. add a `Plan` stage
2. strengthen brownfield QA with real repo gates
3. make PR-ready fail when artifact evidence is weak

That combination will improve both code structure and trust in the workflow faster than adding more model-side instructions.
