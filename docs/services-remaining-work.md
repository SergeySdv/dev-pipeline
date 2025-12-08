# Services Refactor - Remaining Work Analysis

## Current State Summary

### ✅ Completed
1. **Service stubs created** - All 9 services exist with basic functionality
2. **Worker integration** - All 5 main job types delegate to services
3. **API integration** - Core protocol lifecycle uses OrchestratorService
4. **Tests** - 31 service-level tests across 6 files
5. **Documentation** - Comprehensive docs and migration guide

### 🔄 Remaining Work

## 1. CLI/TUI Migration (Low Priority)

**Current State**: CLI uses `APIClient` to call the API
**Analysis**: This is actually a good pattern - CLI is already decoupled
**Recommendation**: **SKIP** - No migration needed. CLI → API → Services is the correct architecture.

**Rationale**:
- CLI is a thin client that should use the API
- Direct service usage would bypass API auth/validation
- Current pattern follows microservices best practices

## 2. Worker Logic Migration (Medium Priority - Ongoing)

**Current State**: Services delegate to `codex_worker` functions
**What's in codex_worker.py** (1728 lines):
- `handle_plan_protocol` - Planning logic
- `handle_execute_step` - Execution logic  
- `handle_quality` - QA logic
- `handle_open_pr` - PR creation logic
- Helper functions for git, worktrees, budgets, triggers

**Migration Strategy**:
```
Phase 1 (Current): Services wrap worker functions ✅
Phase 2 (Next): Extract pure logic into service methods
Phase 3 (Future): Minimize worker to thin adapters
```

**Specific Opportunities**:

### A. Extract Git/Worktree Logic
Move from `codex_worker.py` to new `GitService`:
- `_worktree_path`, `_worktree_branch_name`
- `_remote_branch_exists`
- `git_push_and_open_pr`
- `trigger_ci_pipeline`

### B. Extract Budget/Token Logic
Move to `TelemetryService` or new `BudgetService`:
- `_budget_and_tokens`
- Token counting and enforcement

### C. Extract Trigger/Policy Logic
Move to `OrchestratorService` or new `PolicyService`:
- `_enqueue_trigger_target`
- Loop policy handling
- Trigger depth tracking

### D. Extract Path Resolution Logic
Move to `SpecService` or `PromptService`:
- `_protocol_and_workspace_paths`
- `_resolve_qa_prompt_path`
- `_resolve_step_path_for_qa`

## 3. API Routes Migration (Low Priority)

**Current State**: Most routes use services
**Remaining direct worker calls**:

### In `api/app.py`:
1. Line 25-26: `from tasksgodzilla.workers.state import maybe_complete_protocol`
2. Line 26: `from tasksgodzilla.workers import codemachine_worker`
3. Line 778: `codemachine_worker.import_codemachine_workspace(...)`

**Migration Plan**:

#### A. Move `maybe_complete_protocol` to OrchestratorService
```python
# New method in OrchestratorService
def check_and_complete_protocol(self, protocol_run_id: int) -> bool:
    """Check if protocol is complete and update status if so."""
    # Logic from workers.state.maybe_complete_protocol
```

#### B. Create CodeMachineService
```python
# New service: tasksgodzilla/services/codemachine.py
@dataclass
class CodeMachineService:
    db: BaseDatabase
    
    def import_workspace(self, project_id: int, protocol_run_id: int, workspace_path: str):
        """Import CodeMachine workspace and create protocol spec."""
        # Logic from codemachine_worker.import_codemachine_workspace
```

## 4. Recommended Implementation Order

### Phase 1: Quick Wins (1-2 hours)
1. ✅ Create `CodeMachineService` wrapper
2. ✅ Move `maybe_complete_protocol` to `OrchestratorService`
3. ✅ Update API to use new service methods

### Phase 2: Structural Improvements (3-4 hours)
4. Extract Git/Worktree logic to `GitService`
5. Add tests for new services
6. Update documentation

### Phase 3: Deep Refactoring (Future)
7. Extract budget/token logic
8. Extract trigger/policy logic
9. Gradually slim down `codex_worker.py`

## 5. Success Metrics

### After Phase 1:
- ✅ Zero direct worker imports in `api/app.py`
- ✅ All API routes use services
- ✅ CodeMachine operations service-backed

### After Phase 2:
- ✅ Git operations abstracted in `GitService`
- ✅ 40+ service tests
- ✅ Clear service boundaries documented

### After Phase 3:
- ✅ `codex_worker.py` < 500 lines
- ✅ All business logic in services
- ✅ Workers are thin job adapters

## 6. Non-Goals

- ❌ Rewriting working code for its own sake
- ❌ Breaking backward compatibility unnecessarily
- ❌ Migrating CLI to use services directly (API is correct layer)
- ❌ Achieving 100% service coverage immediately

## 7. Recommendation

**Start with Phase 1** - Quick wins that complete the API migration:
1. Create `CodeMachineService`
2. Add `check_and_complete_protocol` to `OrchestratorService`
3. Update API routes
4. Add tests
5. Update docs

This provides immediate value with minimal risk.
