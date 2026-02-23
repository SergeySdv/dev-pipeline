# UI/UX Refactoring Plan for DevGodzilla

## Implementation Status

**Last Updated:** 2026-02-23

### Completed
- [x] Phase 1.1: Type mismatches fixed (`needs_qa`, `timeout`, `action` field)
- [x] Phase 1.2: API hooks updated for type fixes
- [x] Phase 2.1: Shared `StepIndicator` component created
- [x] Phase 2.2: Shared `ClarificationDialog` component created
- [x] Phase 2.3: All wizards updated to use shared components
  - generate-specs-wizard: Uses StepIndicator with useStepNavigation
  - design-solution-wizard: Uses StepIndicator and ClarificationDialog
  - implement-feature-wizard: Uses StepIndicator and ClarificationDialog
- [x] Phase 3: Workflow state machine (`lib/workflow/`) created
- [x] Phase 4.1: Inline error display added to wizards with dismiss buttons

### In Progress
- [ ] Phase 4: Add comprehensive error handling & loading states
- [ ] Phase 5: Add accessibility improvements

---

## Executive Summary

This plan addresses **47 identified issues** across frontend UI/UX, backend-frontend wiring, and workflow logic. The issues are categorized by severity and grouped into actionable implementation phases.

---

## Phase 1: Critical Fixes (P0)

### 1.1 Backend-Frontend Type Mismatches

| Issue | Location | Impact | Fix |
|-------|----------|--------|-----|
| Missing `needs_qa` in ProtocolStatus | `frontend/lib/api/types.ts` | Frontend cannot display QA-required protocols | Add `"needs_qa"` to `ProtocolStatus` type |
| Missing `timeout` in StepStatus | `frontend/lib/api/types.ts` | Step timeouts not handled | Add `"timeout"` to `StepStatus` type |
| Spec hash fields missing | `ProtocolRun` interface | Frontend tries to access non-existent fields | Update to read from `speckit_metadata` or update backend `ProtocolOut` |
| Feedback field mismatch | `FeedbackCreate.action` vs `feedback_type` | API calls fail | Rename `feedback_type` to `action` in frontend |

**Files to modify:**
```
frontend/lib/api/types.ts
frontend/lib/api/hooks/use-steps.ts
frontend/lib/api/hooks/use-protocols.ts
devgodzilla/schemas.py (if needed)
```

### 1.2 API Endpoint Path Fixes

| Issue | Current | Expected | Fix |
|-------|---------|----------|-----|
| Agent override path | `/agents/projects/{id}/agents/{agentId}` | `/projects/{id}/agents/{agentId}` | Update backend routes |
| Missing project-scoped assignments | N/A | `/projects/{id}/agents/assignments` | Add backend endpoint |
| SpecKit route inconsistency | Mixed global/project-scoped | Consistent project-scoped | Standardize to `/projects/{id}/speckit/*` |

**Files to modify:**
```
devgodzilla/routes/agents.py
devgodzilla/routes/project_speckit.py
frontend/lib/api/hooks/use-speckit.ts
```

---

## Phase 2: Wizard Component Consolidation (P0)

### 2.1 Duplicate Clarification Dialog

**Problem:** Clarification dialog UI duplicated in 4+ files with identical functionality.

**Solution:** Extract to single reusable component.

**New file:** `frontend/components/shared/clarification-dialog.tsx`

```typescript
// Consolidate from:
// - generate-specs-wizard.tsx (L247-280)
// - design-solution-wizard.tsx (L194-225)
// - implement-feature-wizard.tsx (L184-215)
// - spec-tab.tsx (L218-244)
```

**Implementation:**
1. Create `ClarificationDialog` component with controlled state
2. Add `useClarification` hook for state management
3. Replace all 4 usages with new component
4. Add unit tests for new component

### 2.2 Step Indicator Component

**Problem:** 3 different step indicator implementations across wizards.

**Solution:** Create unified `StepIndicator` component.

**New file:** `frontend/components/ui/step-indicator.tsx`

```typescript
interface StepIndicatorProps {
  steps: Array<{ id: string; label: string; description?: string }>;
  currentStep: string;
  completedSteps?: Set<string>;
  onStepClick?: (stepId: string) => void;
  variant?: "horizontal" | "vertical" | "compact";
}
```

**Files to update:**
```
frontend/components/wizards/generate-specs-wizard.tsx
frontend/components/wizards/design-solution-wizard.tsx
frontend/components/wizards/implement-feature-wizard.tsx
frontend/components/wizards/protocol-wizard.tsx
frontend/components/wizards/project-wizard.tsx
```

---

## Phase 3: Workflow Step Alignment (P1)

### 3.1 SpecWorkflow vs Wizard Step Mismatch

**Problem:** `SpecWorkflow` shows 8 steps, but individual wizards show 3-4 steps.

**Current state:**
- `SpecWorkflow`: spec → clarify → plan → checklist → tasks → analyze → implement → sprint (8 steps)
- `GenerateSpecsWizard`: Feature Info → Details → Generate (3 steps)
- `DesignSolutionWizard`: Spec → Plan → Tasks → Execution (4 steps)

**Solution:** Create unified workflow state machine.

**Implementation:**

1. **Create workflow state machine:**
```typescript
// frontend/lib/workflow/types.ts
export const WORKFLOW_STEPS = {
  SPEC: { order: 1, wizards: ['generate-specs'], tab: 'spec' },
  CLARIFY: { order: 2, wizards: [], tab: 'spec' },
  PLAN: { order: 3, wizards: ['design-solution'], tab: 'spec' },
  CHECKLIST: { order: 4, wizards: [], tab: 'spec' },
  TASKS: { order: 5, wizards: ['implement-feature'], tab: 'spec' },
  ANALYZE: { order: 6, wizards: [], tab: 'spec' },
  IMPLEMENT: { order: 7, wizards: [], tab: 'spec' },
  SPRINT: { order: 8, wizards: [], tab: 'execution' },
} as const;
```

2. **Update wizard completion handlers** to advance workflow state

3. **Add workflow context provider:**
```typescript
// frontend/lib/workflow/workflow-context.tsx
export function WorkflowProvider({ children, projectId }) {
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('spec');
  const [stepStatus, setStepStatus] = useState<Record<WorkflowStep, StepStatus>>({});
  // ...
}
```

### 3.2 Navigation Pattern Consistency

**Problem:** Inconsistent `getStepHref` patterns - some use `?wizard=`, some use `?tab=`.

**Solution:** Standardize navigation:
- Wizard steps: `?wizard={wizard-name}&step={step-id}`
- Tab navigation: `?tab={tab-name}`
- Add `useWorkflowNavigation` hook

**Files to modify:**
```
frontend/components/speckit/spec-workflow.tsx
frontend/app/projects/[id]/page.tsx
```

---

## Phase 4: Error Handling & Loading States (P1)

### 4.1 Missing Error Recovery in Wizards

**Problem:** Wizards show toast errors but no inline recovery.

**Solution:** Add inline error states with retry capability.

**Implementation per wizard:**
```typescript
// Add to each wizard component
const [error, setError] = useState<Error | null>(null);

// In render:
{error && (
  <Alert variant="destructive" className="mb-4">
    <AlertTitle>Error</AlertTitle>
    <AlertDescription>{error.message}</AlertDescription>
    <Button variant="outline" size="sm" onClick={handleRetry}>
      Retry
    </Button>
  </Alert>
)}
```

### 4.2 Missing Loading States

**Problem:** No loading indicators during API calls in several places.

**Solution:** Add skeleton loaders and loading overlays.

**New component:** `frontend/components/ui/wizard-loading.tsx`

**Files to update:**
- All wizard components
- `frontend/app/projects/[id]/components/spec-tab.tsx`
- `frontend/app/projects/[id]/components/workflow-tab.tsx`

### 4.3 State Reset on Dialog Close

**Problem:** Wizard state not reset when dialog closes.

**Solution:** Add cleanup in `onOpenChange` callback.

```typescript
const handleOpenChange = (open: boolean) => {
  if (!open) {
    // Reset all wizard state
    setStep(1);
    setFormData(initialFormData);
    setError(null);
    setLastSpecPath(null);
    // ...
  }
  onOpenChange(open);
};
```

---

## Phase 5: Accessibility & UX Polish (P2)

### 5.1 ARIA Attributes

**Problem:** Missing ARIA attributes in progress and loading components.

**Solution:** Add proper ARIA labels.

| Component | Fix |
|-----------|-----|
| `Progress` | Add `aria-label`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| `LoadingState` | Add `role="status"`, `aria-live="polite"` |
| `StepIndicator` | Add `aria-current="step"` for current step |
| Wizards | Add `role="dialog"`, `aria-modal="true"`, `aria-labelledby` |

### 5.2 Keyboard Navigation

**Problem:** Wizards don't support keyboard shortcuts.

**Solution:** Add keyboard handlers.

```typescript
// Add to wizard components
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !isSubmitting) handleNext();
    if (e.key === 'Escape') onOpenChange(false);
  };
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [handleNext, isSubmitting, onOpenChange]);
```

### 5.3 Color Contrast Issues

**Problem:** Some badge colors don't meet WCAG AA standards.

**Solution:** Audit and fix color values.

**Files to audit:**
```
frontend/components/ui/badge.tsx
frontend/components/speckit/spec-workflow.tsx (status colors)
tailwind.config.ts
```

---

## Phase 6: Code Organization (P2)

### 6.1 Duplicate CSS Files

**Problem:** Multiple `globals.css` files causing inconsistency.

**Files found:**
```
frontend/app/globals.css
frontend/src/globals.css (possibly unused)
```

**Solution:** Consolidate to single `globals.css` in `app/`.

### 6.2 API Hook Organization

**Problem:** Some hooks are large and could be split.

**Solution:** Split hooks by concern.

| Current | Split Into |
|---------|------------|
| `use-speckit.ts` | `use-spec-generation.ts`, `use-workflow.ts`, `use-clarification.ts` |
| `use-protocols.ts` | `use-protocol-crud.ts`, `use-protocol-actions.ts`, `use-protocol-artifacts.ts` |

---

## Phase 7: Backend Schema Alignment (P1)

### 7.1 ProtocolRun Schema Extension

**Backend changes needed:**

```python
# devgodzilla/schemas.py - ProtocolOut
class ProtocolOut(APIModel):
    # Add these fields from speckit_metadata to top level
    spec_hash: Optional[str] = None
    spec_validation_status: Optional[str] = None
    spec_validated_at: Optional[datetime] = None

    # Add linked_sprint_id
    linked_sprint_id: Optional[int] = None
```

### 7.2 Database Schema Extension

```sql
-- Add to protocol_runs table
ALTER TABLE protocol_runs ADD COLUMN linked_sprint_id INTEGER REFERENCES sprints(id);
```

### 7.3 Policy Fields Exposure

**Problem:** Policy fields in database but not in API.

**Solution:** Add to `ProtocolOut`:
```python
policy_pack_key: Optional[str] = None
policy_pack_version: Optional[str] = None
policy_effective_hash: Optional[str] = None
```

---

## Implementation Timeline

| Phase | Duration | Priority | Dependencies |
|-------|----------|----------|--------------|
| Phase 1 | 2 days | P0 | None |
| Phase 2 | 3 days | P0 | Phase 1 |
| Phase 3 | 3 days | P1 | Phase 2 |
| Phase 4 | 2 days | P1 | Phase 2 |
| Phase 5 | 2 days | P2 | Phase 4 |
| Phase 6 | 1 day | P2 | None |
| Phase 7 | 2 days | P1 | Phase 1 |

**Total estimated effort:** ~15 days

---

## Testing Strategy

### Unit Tests
- New `StepIndicator` component
- New `ClarificationDialog` component
- Workflow state machine
- API hooks

### Integration Tests
- Wizard flow completion (each wizard)
- Workflow step progression
- Error recovery flows
- Keyboard navigation

### E2E Tests (Critical Paths)
1. Create project → Generate spec → Complete wizard
2. Create protocol from spec → Run protocol
3. Submit feedback → Verify step state update

---

## Rollback Plan

Each phase should be merged as a separate PR with:
1. Feature flag for new components
2. Backward compatibility for API changes
3. Database migrations in separate PR

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Wizard completion rate | Unknown | > 90% |
| Error recovery success | Manual retry only | One-click retry |
| Accessibility score | Unknown | WCAG AA compliant |
| Code duplication | 4+ clarification dialogs | 1 shared component |
| Type safety | Partial | 100% frontend-backend alignment |

---

## Appendix: File Change Summary

### Frontend Files to Create
```
frontend/components/shared/clarification-dialog.tsx
frontend/components/ui/step-indicator.tsx
frontend/components/ui/wizard-loading.tsx
frontend/lib/workflow/types.ts
frontend/lib/workflow/workflow-context.tsx
frontend/lib/hooks/use-clarification.ts
```

### Frontend Files to Modify
```
frontend/lib/api/types.ts
frontend/lib/api/hooks/use-speckit.ts
frontend/lib/api/hooks/use-steps.ts
frontend/lib/api/hooks/use-protocols.ts
frontend/components/wizards/generate-specs-wizard.tsx
frontend/components/wizards/design-solution-wizard.tsx
frontend/components/wizards/implement-feature-wizard.tsx
frontend/components/wizards/protocol-wizard.tsx
frontend/components/wizards/project-wizard.tsx
frontend/components/speckit/spec-workflow.tsx
frontend/app/projects/[id]/page.tsx
frontend/app/projects/[id]/components/spec-tab.tsx
frontend/app/projects/[id]/components/workflow-tab.tsx
```

### Backend Files to Modify
```
devgodzilla/schemas.py
devgodzilla/routes/agents.py
devgodzilla/routes/project_speckit.py
devgodzilla/routes/protocols.py
```

### Database Migrations
```
alembic/versions/xxx_add_linked_sprint_to_protocol_runs.py
```
