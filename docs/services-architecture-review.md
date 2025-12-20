# Services Architecture Review

**Date**: 2025-12-13
**Scope**: SWE agent workflow best practices and redundancy analysis

## Executive Summary

The TasksGodzilla services layer implements a well-designed **service-oriented architecture** with 12 primary services coordinating protocol-driven SWE agent workflows. The architecture follows industry best practices with clear separation of concerns, dependency injection, and policy-driven behavior. Minor redundancies exist but are intentional (gradual migration from legacy workers).

## Service Inventory

| Service | Responsibility | Dependencies |
|---------|---------------|--------------|
| **OrchestratorService** | Protocol/step lifecycle coordination | Database, Queue, PolicyService |
| **ExecutionService** | Step execution workflow | Git, Budget, Orchestrator, Spec, Policy, Clarifications, Prompt, Quality |
| **QualityService** | QA execution and verdicts | Git, Spec, Orchestrator, Prompt, Budget, Clarifications |
| **OnboardingService** | Project setup and initialization | Policy, Clarifications |
| **SpecService** | Protocol/step specification management | Database |
| **GitService** | Git operations and worktree management | Database |
| **BudgetService** | Token budget enforcement | None (standalone) |
| **PolicyService** | Policy-pack evaluation and merging | Database |
| **ClarificationsService** | Clarification question management | Database |
| **CodeMachineService** | CodeMachine workspace import | Worker delegation |
| **DecompositionService** | Step decomposition via LLM | None (standalone) |
| **PromptService** | Prompt resolution and context building | None (standalone) |

## Architecture Patterns

### Dependency Injection
All services use dataclass fields for dependency injection:
```python
@dataclass
class ExecutionService:
    db: BaseDatabase
```

### Lazy Imports
Services import dependencies inside methods to avoid circular dependencies:
```python
def execute_step(self, step_run_id: int):
    from tasksgodzilla.services.budget import BudgetService
    budget_service = BudgetService()
```

### Policy-Driven Gating
PolicyService provides centralized policy evaluation used by ExecutionService and OnboardingService to gate operations based on blocking findings.

### Queue-Based vs Inline Execution
OrchestratorService supports both:
- Queue-based execution via Redis/RQ (production)
- Inline fallback when Redis unavailable (dev/test)

## SWE Agent Workflow Best Practices Assessment

### Strengths

| Practice | Implementation | Status |
|----------|---------------|--------|
| **Clear responsibility isolation** | Each service owns a single domain | ✅ Excellent |
| **Policy-driven behavior** | PolicyService enables runtime control | ✅ Excellent |
| **QA policies for fast feedback** | skip/light/full modes | ✅ Excellent |
| **Trigger & loop policies** | Automatic step chaining and retries | ✅ Excellent |
| **Multi-engine support** | Codex + CodeMachine via registry | ✅ Excellent |
| **Budget enforcement** | Per-step and per-protocol limits | ✅ Excellent |
| **Blocking clarifications** | User interaction during workflows | ✅ Excellent |

### Protocol Lifecycle (Industry Standard)
```
PENDING → PLANNING → PLANNED → RUNNING → COMPLETED/FAILED/BLOCKED/CANCELLED
```

### Step Lifecycle (Industry Standard)
```
PENDING → RUNNING → NEEDS_QA → COMPLETED/FAILED/BLOCKED/CANCELLED
```

### QA Policy Modes
| Mode | Use Case |
|------|----------|
| `skip` | Setup/scan steps that don't need validation |
| `light` | Quick inline QA for fast feedback loop |
| `full` | Thorough validation (default) |

## Redundancy Analysis

### No Redundancy (Well-Designed)

| Area | Components | Assessment |
|------|------------|------------|
| **Spec handling** | SpecService + spec.py | COMPLEMENTARY - service wraps pure functions |
| **Git operations** | GitService + git_utils.py | LAYERED - service adds event recording |
| **Budget tracking** | BudgetService + codex.py | LAYERED - service wraps low-level functions |
| **Policy evaluation** | PolicyService + storage | LAYERED - good separation |
| **Clarifications** | ClarificationsService + storage | LAYERED - clean |

### Intentional Overlap (Migration in Progress)

| Area | Components | Status |
|------|------------|--------|
| **OrchestratorService + Workers** | Service delegates to codex_worker | Gradual migration - workers being eliminated |
| **ExecutionService + pipeline.py** | Service uses pipeline utilities | Acceptable - clear separation |
| **QualityService + qa.py** | Service uses qa utilities | Acceptable - clear separation |

## Service Dependency Matrix

```
OrchestratorService (core hub)
 ├─ Database
 ├─ Queue
 └─ PolicyService

ExecutionService (step execution)
 ├─ GitService
 ├─ BudgetService
 ├─ OrchestratorService
 ├─ SpecService
 ├─ PolicyService
 ├─ ClarificationsService
 ├─ PromptService
 └─ QualityService

QualityService (QA execution)
 ├─ GitService
 ├─ SpecService
 ├─ OrchestratorService
 ├─ PromptService
 ├─ BudgetService
 └─ ClarificationsService

OnboardingService (project setup)
 ├─ PolicyService
 └─ ClarificationsService

SpecService, GitService, PolicyService, ClarificationsService
 └─ Database

BudgetService, DecompositionService, PromptService
 └─ [STANDALONE]
```

## Inter-Service Communication Patterns

| From | To | Pattern |
|------|----|---------|
| ExecutionService | OrchestratorService | Completion handling, trigger policies |
| QualityService | OrchestratorService | QA verdict reporting |
| ExecutionService | QualityService | Prompt QA auto-run after execution |
| SpecService | OrchestratorService | Spec syncing |
| ExecutionService | PolicyService | Blocking findings check |
| OnboardingService | PolicyService | Policy-driven setup |

## Recommendations

### High Priority

1. **Eliminate Worker Wrappers**
   - OrchestratorService.plan_protocol() and .execute_step() are thin wrappers over workers
   - Migrate worker logic directly into service methods
   - Impact: Reduces indirection, improves testability

2. **Standardize Service Construction**
   - Some services use lazy imports; others use constructor injection
   - Pick one pattern consistently across all services
   - Impact: Improved consistency and predictability

### Medium Priority

3. **Extract Execution Phases**
   - ExecutionService.execute_step() is 600+ lines with multiple phases
   - Consider breaking into sub-services:
     - RepositorySetupPhase
     - PromptResolutionPhase
     - ExecutionPhase
     - PostExecutionPhase
   - Impact: Better testability, clearer boundaries

4. **Event Recording Abstraction**
   - Multiple services call `db.append_event()` directly
   - Consider EventRecordingService to centralize event logic
   - Impact: Consistent event schemas, easier auditing

### Low Priority

5. **Consolidate Spec Modules**
   - Consider moving pure spec functions into SpecService
   - Reduces module scatter
   - Impact: Slightly cleaner structure

## File Reference

| File | Purpose |
|------|---------|
| `tasksgodzilla/services/orchestrator.py` | Protocol/step coordination |
| `tasksgodzilla/services/execution.py` | Step execution workflow |
| `tasksgodzilla/services/quality.py` | QA validation |
| `tasksgodzilla/services/onboarding.py` | Project setup |
| `tasksgodzilla/services/spec.py` | Specification management |
| `tasksgodzilla/services/git.py` | Git operations |
| `tasksgodzilla/services/budget.py` | Token budgets |
| `tasksgodzilla/services/policy.py` | Policy evaluation |
| `tasksgodzilla/services/clarifications.py` | Clarifications |
| `tasksgodzilla/services/codemachine.py` | CodeMachine import |
| `tasksgodzilla/services/decomposition.py` | Step decomposition |
| `tasksgodzilla/services/prompts.py` | Prompt resolution |
| `tasksgodzilla/services/platform/queue.py` | Job queue |
| `tasksgodzilla/services/platform/artifacts.py` | Artifact tracking |

## Conclusion

The services architecture follows SWE agent workflow best practices:
- Single responsibility per service
- Policy-driven gating and behavior
- Flexible QA modes for fast feedback
- Budget enforcement to prevent runaway costs
- Multi-engine support for different execution models

Redundancy is minimal and intentional where it exists (gradual worker migration). The recommended improvements focus on consistency and testability rather than architectural changes.
