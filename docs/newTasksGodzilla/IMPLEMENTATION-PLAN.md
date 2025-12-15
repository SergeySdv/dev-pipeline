# DevGodzilla Implementation Plan (Refactor & Migrate)

> Detailed implementation plan for transitioning `tasksgodzilla` into the unified `devgodzilla` platform

---

## Overview

This plan outlines the **migration and refactoring** of the existing `tasksgodzilla` codebase into the new `devgodzilla` architecture, followed by the implementation of missing components (Windmill integration, UI).

**Strategy:** Refactor & Migrate
**Estimated Effort:** 12-16 weeks

```mermaid
gantt
    title DevGodzilla Implementation Timeline
    dateFormat  YYYY-MM-DD
    section Phase 1: Foundation
    Migrate Core Utils    :p1, 2024-01-01, 1w
    Setup DB & Events     :p1, 1w
    section Phase 2: Specification
    Refactor Spec Engine  :p2, after p1, 2w
    section Phase 3: Orchestration
    Windmill Integration  :p3, after p2, 2w
    section Phase 4: Execution
    Refactor Agents       :p4, after p3, 2w
    section Phase 5: Quality
    Refactor QA           :p5, after p4, 2w
    section Phase 6: UI
    Windmill Frontend     :p6, after p5, 2w
    section Phase 7: Integration
    System Testing        :p7, after p6, 2w
```

---

## Phase 1: Foundation & Core Migration (Weeks 1-2)

> **Goal**: Establish `devgodzilla` package structure and migrate core core utilities from `tasksgodzilla`.

### 1.1 Package Structure & Core Utils

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T1.1.1 | Initialize `devgodzilla` package structure | N/A |
| T1.1.2 | specific `ConfigService` implementation | `config.py` |
| T1.1.3 | Migrate structured logging setup | `logging.py` |
| T1.1.4 | Define `Service` base class | New (Architecture Requirement) |
| T1.1.5 | Migrate Error hierarchy | `errors.py` |

**Files to create/modify:**
- `devgodzilla/__init__.py`
- `devgodzilla/config.py` - derived from `tasksgodzilla/config.py`
- `devgodzilla/logging.py` - derived from `tasksgodzilla/logging.py`
- `devgodzilla/services/base.py`

### 1.2 Database & Storage

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T1.2.1 | Migrate SQLAlchemy models to `db/models.py` | `storage.py`.DB models |
| T1.2.2 | Setup Alembic migrations | `alembic/` |
| T1.2.3 | Implement `DatabaseService` | `storage.py` logic |

**Files to create/modify:**
- `devgodzilla/db/models.py` - Port `Project`, `ProtocolRun` models
- `devgodzilla/db/database.py` - Port session management

### 1.3 Events & Git

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T1.3.1 | Implement `EventBus` | `services/events.py` (if exists) or new |
| T1.3.2 | Migrate Git operations | `services/git.py` / `git_utils.py` |

**Files to create/modify:**
- `devgodzilla/services/events.py`
- `devgodzilla/services/git.py` - Refactor `tasksgodzilla/git_utils.py`

---

## Phase 2: Specification Engine (Weeks 3-4)

> **Goal**: Refactor `PlanningService` and SpecKit integration.

### 2.1 Planning & SpecKit

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T2.1.1 | Refactor `PlanningService` | `services/planning.py` |
| T2.1.2 | Port SpecKit models | `services/spec.py`, `domain.py` |
| T2.1.3 | Port `prompt_utils.py` | `prompt_utils.py`, `services/prompts.py` |

**Files to create/modify:**
- `devgodzilla/services/planning.py` - Clean up dependencies
- `devgodzilla/models/speckit.py`

### 2.2 Clarifications & Policies

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T2.2.1 | Refactor `ClarifierService` | `services/clarifications.py` |
| T2.2.2 | Refactor `PolicyService` | `services/policy.py` |
| T2.2.3 | Port constitution logic | `services/policy.py` |

**Files to create/modify:**
- `devgodzilla/services/clarifier.py`
- `devgodzilla/services/policy.py`

---

## Phase 3: Orchestration Core (Weeks 5-6)

> **Goal**: Replace current `OrchestratorService` with Windmill-based orchestration.

### 3.1 Windmill Integration (New)

| Task | Description | Status |
|------|-------------|--------|
| T3.1.1 | Create Windmill Client | New |
| T3.1.2 | Implement Flow Generator | New |
| T3.1.3 | Create `devgodzilla-worker` script for Windmill | New |

**Files to create/modify:**
- `devgodzilla/windmill/client.py`
- `devgodzilla/windmill/flows.py`

### 3.2 Logic Migration from Orchestrator

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T3.2.1 | Extract State Machine logic | `services/orchestrator.py` |
| T3.2.2 | Extract Dependency/DAG logic | `pipeline.py` / `services/orchestrator.py` |
| T3.2.3 | Implement new `OrchestratorService` (facade for Windmill) | `services/orchestrator.py` (complete rewrite) |

**Files to create/modify:**
- `devgodzilla/orchestration/dag.py`
- `devgodzilla/services/orchestrator.py` - Rewritten to use Windmill

---

## Phase 4: Execution Layer (Weeks 7-8)

> **Goal**: Normalize agent engines into a unified Registry.

### 4.1 Engine Registry

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T4.1.1 | Define `EngineInterface` | New |
| T4.1.2 | Implement `EngineRegistry` | `run_registry.py` / `engine_resolver.py` |
| T4.1.3 | Refactor `CodexEngine` | `engines_codex.py` / `engines/` |
| T4.1.4 | Refactor `OpenCodeEngine` | `engines_opencode.py` |

**Files to create/modify:**
- `devgodzilla/engines/interface.py`
- `devgodzilla/engines/registry.py` - Port `tasksgodzilla/engine_resolver.py`
- `devgodzilla/engines/adapters/` - Port existing engine implementations

### 4.2 Execution Service

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T4.2.1 | Refactor `ExecutionService` | `services/execution.py` |
| T4.2.2 | Port Sandbox logic | `worker_runtime.py` |
| T4.2.3 | Port ArtifactWriter | `services/execution.py` |

**Files to create/modify:**
- `devgodzilla/services/execution.py`
- `devgodzilla/execution/sandbox.py`

---

## Phase 5: Quality Assurance (Weeks 9-10)

> **Goal**: Refactor QA logic into composable Gates.

### 5.1 QA Service Refactoring

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T5.1.1 | Refactor `QualityService` | `services/quality.py` |
| T5.1.2 | Split monolithic QA logic into `Gates` | `qa.py` |
| T5.1.3 | Port Feedback Loop logic | `services/quality.py` |

**Files to create/modify:**
- `devgodzilla/services/quality.py`
- `devgodzilla/qa/gates/` - Extract logic from `qa.py`

### 5.2 Checklist Validation

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T5.2.1 | Port Checklist Validator | `qa.py` (if present) |

---

## Phase 6: User Interface (Weeks 11-12)

> **Goal**: New Development (Windmill Extensions & CLI).

### 6.1 CLI

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T6.1.1 | Implement new `click` CLI | `cli/` (migrate existing commands) |
| T6.1.2 | Add new orchestration commands | New |

### 6.2 Windmill UI

| Task | Description | Status |
|------|-------------|--------|
| T6.2.1 | Develop Svelte Components | New |

---

## Phase 7: Integration (Weeks 13-14)

### 7.1 API & Tests

| Task | Description | Source in `tasksgodzilla` |
|------|-------------|---------------------------|
| T7.1.1 | Refactor API endpoints | `api/` |
| T7.1.2 | Migrate Tests | `tests/` |

---

## Critical Path Migration Steps

1.  **Codebase Freeze**: Stop development on `tasksgodzilla` root.
2.  **Namespace Creation**: Create `devgodzilla/` and start moving core services.
3.  **Database Migration**: Adjust Alembic scripts to point to new models.
4.  **Service Migration**: Move services one by one (Database -> Git -> Config -> Planning...).
5.  **Orchestration Swap**: Implement Windmill integration, effectively retiring the old `orchestrator.py` loop.

## Dependencies

| New Component | Preceded By (Legacy/New) |
|---------------|--------------------------|
| `devgodzilla.db` | `tasksgodzilla.storage` |
| `devgodzilla.services.planning` | `tasksgodzilla.services.planning` |
| `devgodzilla.services.execution` | `tasksgodzilla.services.execution` |
| `devgodzilla.orchestration` | **NEW** (replaces `tasksgodzilla.orchestrator`) |
