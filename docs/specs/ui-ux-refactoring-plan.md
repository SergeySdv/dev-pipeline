# UI/UX Refactoring Plan for DevGodzilla

## Executive Summary

This document outlines a comprehensive UI/UX refactoring plan for the DevGodzilla frontend application. The analysis identified several categories of issues ranging from minor visual inconsistencies to structural flow problems and potential backend integration gaps.

---

## Part 1: Audit Findings

### 1.1 Navigation & Information Architecture Issues

| Issue | Severity | Description | Location |
|-------|----------|-------------|----------|
| **Duplicate "Sprints" Navigation** | High | `/sprints` redirects to `/execution`, but sidebar shows "Sprints" linking to `/sprints`. Users see "Sprints" but land on "Execution Overview" | `sidebar.tsx`, `app/sprints/page.tsx` |
| **Confusing Tab Names in Project** | Medium | Project detail uses `tab=execution` for "Sprints" tab, but URL says `?tab=sprints` gets normalized to `execution` | `app/projects/[id]/page.tsx:57` |
| **Missing Breadcrumbs** | Medium | Deep pages like `/steps/[id]` lack breadcrumb navigation for orientation | All detail pages |
| **Inconsistent Back Navigation** | Low | Some pages have "Back to X" links, others don't | Various |

### 1.2 Flow Logic Issues

| Issue | Severity | Description | Location |
|-------|----------|-------------|----------|
| **Protocol → Steps Flow Gap** | High | Protocol detail page shows steps, but creating a protocol doesn't automatically create steps. User can't easily see what steps will run. | `app/protocols/[id]/page.tsx` |
| **Create Protocol Flow Missing** | High | No clear "Create Protocol" wizard from project detail. Users must go through "Workflow" tab which is confusing. | `app/projects/[id]/page.tsx` |
| **Onboarding Start Hidden** | Medium | "Start Onboarding" button only visible when status is "pending", but users don't know they need to start it. | `app/projects/[id]/page.tsx:119` |
| **Task Creation Context Loss** | Medium | Creating tasks in execution board requires selecting project first, but context is not preserved across page navigation. | `app/execution/page.tsx` |
| **No Protocol → Sprint Linking UI** | Medium | Backend has `/protocols/{id}/actions/create-sprint` but no clear UI to trigger this from protocol detail. | `app/protocols/[id]/page.tsx` |

### 1.3 Backend Integration Gaps

| Issue | Severity | Endpoint | Frontend Call | Status |
|-------|----------|----------|---------------|--------|
| **Missing Sprint List Endpoint** | High | `GET /sprints` | `useAllSprints()` calls `/sprints` | Backend only has `GET /sprints/{sprint_id}` |
| **Missing Task List Endpoint** | High | `GET /tasks` | `useAllTasks()` calls `/tasks` | Backend only has `GET /tasks/{task_id}` |
| **Missing Project Tasks Endpoint** | Medium | `GET /projects/{id}/tasks` | Expected in hooks | ✅ Exists in `projects.py` |
| **Spec Endpoint New** | Low | `GET /protocols/{id}/spec` | `useProtocolSpec()` | ✅ Added in Phase 1 |
| **Runs Endpoint New** | Low | `GET /protocols/{id}/runs` | `useProtocolRuns()` | ✅ Added in Phase 1 |

### 1.4 UI Component Consistency Issues

| Issue | Severity | Description | Affected Components |
|-------|----------|-------------|---------------------|
| **Mixed Card/List Views** | Low | Projects page has grid/list toggle, but other list pages (Protocols, Runs) don't | `projects/page.tsx` vs others |
| **Inconsistent Empty States** | Medium | Some pages have custom empty states, others use generic | Various |
| **Filter UI Inconsistency** | Medium | Projects uses search input, Protocols uses search + dropdown, Runs has no filtering | List pages |
| **Status Pill Colors Changed** | Low | Phase 3 updated status pill colors, but some pages may expect old colors | `status-pill.tsx` |

### 1.5 Missing Features / Placeholders

| Feature | Severity | Location | Notes |
|---------|----------|----------|-------|
| **Dashboard Page** | High | `app/page.tsx` | Currently minimal, needs real data widgets |
| **Quality Page** | Medium | `app/quality/page.tsx` | Needs verification of implementation |
| **Profile Page** | Low | `app/profile/page.tsx` | Has hardcoded activity items |
| **Settings Page** | Low | `app/settings/page.tsx` | Needs implementation review |

---

## Part 2: Proposed Solutions

### 2.1 Navigation Restructuring

#### Option A: Simplified Navigation (Recommended)

```
Workspace
├── Dashboard (/)
├── Projects (/projects)

Execute
├── Protocols (/protocols)
├── Runs (/runs)  
├── Tasks (/tasks)          ← NEW: Dedicated task board
└── Clarifications (/clarifications)

Plan
├── Specifications (/specifications)
├── Sprints (/sprints)      ← Direct to sprint list, not redirect
└── Backlog (/backlog)      ← NEW: Unassigned tasks

Automation
├── Agents (/agents)
├── Policy Packs (/policy-packs)
└── Quality (/quality)

Operations
├── Queues (/ops/queues)
├── Events (/ops/events)
├── Logs (/ops/logs)
└── Metrics (/ops/metrics)
```

#### Implementation Tasks:

1. **Fix Sprint Redirect** 
   - Remove redirect in `app/sprints/page.tsx`
   - Create actual sprint list page
   - Update sidebar to reflect real structure

2. **Add Breadcrumbs**
   - Create `components/layout/breadcrumbs.tsx`
   - Add to all detail pages
   - Show: Projects > {name} > {tab}

3. **Standardize Tab Names**
   - Use consistent naming: overview, protocols, runs, tasks, settings
   - Update URL params to match display names

### 2.2 Backend API Additions Required

```python
# sprints.py - Add list endpoint
@router.get("/sprints", response_model=List[schemas.SprintOut])
def list_sprints(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """List all sprints with optional filtering"""
    pass

# tasks.py - Add list endpoint  
@router.get("/tasks", response_model=List[schemas.AgileTaskOut])
def list_tasks(
    project_id: Optional[int] = None,
    sprint_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """List all tasks with optional filtering"""
    pass
```

### 2.3 Flow Improvements

#### 2.3.1 Protocol Creation Flow

```
Project Detail 
    → Click "New Protocol" button (in Workflow tab header)
    → Protocol Wizard Modal
        → Select template (optional)
        → Configure branches
        → Set policy pack
        → Preview generated steps
    → Create Protocol
    → Redirect to Protocol Detail (steps tab active)
```

**Implementation:**
- Add "New Protocol" button to `WorkflowTab` component
- Enhance `ProtocolWizard` to show step preview
- Add redirect with `?tab=steps` after creation

#### 2.3.2 Onboarding Flow

```
Project Created
    → Auto-navigate to project detail
    → Show onboarding banner: "This project needs onboarding. [Start Now]"
    → Onboarding starts
    → Show progress in sidebar
    → On complete, show success message
```

**Implementation:**
- Add prominent banner component for pending onboarding
- Auto-poll onboarding status during active onboarding
- Add celebration/confetti on completion

#### 2.3.3 Sprint/Task Flow

```
Protocol Running
    → Steps complete
    → "Create Sprint from Protocol" button becomes active
    → Click → Dialog with task preview
    → Create Sprint with linked tasks
    → Navigate to Sprint Board
```

### 2.4 UI Component Standardization

#### 2.4.1 List Page Pattern

Create a standardized list page pattern:

```tsx
// components/patterns/list-page.tsx
interface ListPageProps<T> {
  title: string;
  description: string;
  data: T[];
  isLoading: boolean;
  error?: Error;
  searchPlaceholder?: string;
  filters?: FilterConfig[];
  views?: ('grid' | 'list' | 'table')[];
  renderCard: (item: T) => React.ReactNode;
  renderRow?: (item: T) => React.ReactNode;
  emptyState?: EmptyStateConfig;
  actions?: React.ReactNode;
}
```

#### 2.4.2 Standard Filters Component

```tsx
// components/ui/list-toolbar.tsx (already created, enhance)
// Add: date range picker, multi-select, saved filters
```

#### 2.4.3 Empty State Standardization

```tsx
// components/ui/empty-state.tsx (enhance)
// Add: illustrations, suggested actions, documentation links
```

### 2.5 Dashboard Improvements

```tsx
// app/page.tsx - Dashboard
// Add widgets:
// - Active protocols (running/paused)
// - Recent runs with status
// - Tasks in progress
// - Blocking clarifications
// - Agent health summary
// - Sprint progress
```

---

## Part 3: Implementation Roadmap

### Phase 4: Critical Fixes (Week 1)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Add `GET /sprints` endpoint | P0 | 2h | None |
| Add `GET /tasks` endpoint | P0 | 2h | None |
| Fix sprint redirect | P0 | 1h | None |
| Add breadcrumbs component | P1 | 3h | None |
| Add "New Protocol" button to Workflow tab | P1 | 2h | None |

### Phase 5: Flow Improvements (Week 2)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Enhance onboarding banner/flow | P1 | 4h | None |
| Add step preview to ProtocolWizard | P1 | 4h | None |
| Create sprint list page | P1 | 3h | Phase 4 endpoints |
| Add protocol→sprint linking UI | P2 | 3h | None |
| Standardize list page pattern | P2 | 6h | None |

### Phase 6: Polish & Consistency (Week 3)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Dashboard widgets implementation | P2 | 8h | None |
| Filter UI standardization | P2 | 4h | None |
| Empty state enhancements | P3 | 3h | None |
| Loading state improvements | P3 | 2h | None |
| Mobile responsiveness audit | P3 | 4h | None |

---

## Part 4: Wireframes / Mockups

### 4.1 Project Detail Page (Revised)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ← Back to Projects                                                       │
├─────────────────────────────────────────────────────────────────────────┤
│ Project Name                                    [Start Onboarding]      │
│ status: onboarding • branch: main • github: owner/repo                  │
│ policy: default • mode: warn • updated: 2h ago                          │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌──────────────────────────────────────────────────────┐│
│ │ Overview    │ │  Onboarding in Progress                              ││
│ │ Specs       │ │  ┌─────────────────────────────────────────────────┐ ││
│ │ Branches    │ │  │ ████████████░░░░░░░░ 60% - Cloning repository   │ ││
│ │ ───────────│ │  │ ✓ Clone • ✓ Analyze • ○ Plan • ○ Generate        │ ││
│ │ Protocols   │ │  └─────────────────────────────────────────────────┘ ││
│ │ Workflow    │ │                                                      ││
│ │ ───────────│ │  [View Details]                                       ││
│ │ Policy      │ │                                                      ││
│ │ Clarific.①  │ │  Quick Actions                                        ││
│ │ Settings    │ │  [New Protocol] [Generate Specs] [View Runs]         ││
│ └─────────────┘ └──────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Sprints Page (New)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Sprints                                                    [+ New Sprint]│
│ Manage execution cycles and track progress                              │
├─────────────────────────────────────────────────────────────────────────┤
│ [All] [Active (3)] [Planning (2)] [Completed (12)]                      │
│ Filter: [Project ▼] [Date Range ▼] [Search...]              [List|Board]│
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐            │
│ │ Sprint 24-W07   │ │ Sprint 24-W08   │ │ Sprint 24-W06   │            │
│ │ ● Active        │ │ ○ Planning      │ │ ✓ Completed     │            │
│ │                 │ │                 │ │                 │            │
│ │ 32/40 points    │ │ 0/24 points     │ │ 45/45 points    │            │
│ │ ████████░░ 80%  │ │ ░░░░░░░░░░ 0%   │ │ ██████████ 100% │            │
│ │                 │ │                 │ │                 │            │
│ │ Feb 12 - Feb 26 │ │ Feb 26 - Mar 11 │ │ Jan 29 - Feb 12 │            │
│ │ 3 protocols     │ │ 1 protocol      │ │ 2 protocols     │            │
│ │ [View Board]    │ │ [Start Sprint]  │ │ [View Report]   │            │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Dashboard (Enhanced)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Dashboard                                          Last updated: 2m ago │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐│
│ │ Active Protocols    │ │ Tasks in Progress   │ │ Blocking Clarifs    ││
│ │        5            │ │        12           │ │        3            ││
│ │ 2 running, 3 paused │ │ across 2 sprints    │ │ need attention      ││
│ └─────────────────────┘ └─────────────────────┘ └─────────────────────┘│
├─────────────────────────────────────────────────────────────────────────┤
│ Recent Activity                                                         │
│ ┌───────────────────────────────────────────────────────────────────────┤
│ │ ● Protocol "feature-auth" started on demo-spring (2m ago)            │
│ │ ✓ Step "Write tests" completed on feature-auth (15m ago)             │
│ │ ⚠ Clarification needed: "Should we use OAuth2 or JWT?" (1h ago)      │
│ │ ● Agent "cursor-1" picked up task #142 (2h ago)                      │
│ └───────────────────────────────────────────────────────────────────────┤
├─────────────────────────────────────────────────────────────────────────┤
│ Sprint Progress                        │ Agent Health                   │
│ ████████████████░░░░ Sprint 24-W07     │ cursor-1  ██████████ Excellent │
│ ████████░░░░░░░░░░░░ Sprint 24-W08     │ cursor-2  ████████░░ Good       │
│ ████████████████████ Sprint 24-W06     │ copilot-1 ██████████ Excellent  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 5: Testing Checklist

### 5.1 Critical User Journeys

- [ ] Create project → see onboarding → complete onboarding
- [ ] Create protocol from project → see steps → run protocol
- [ ] View running protocol → pause → resume → complete
- [ ] Create sprint from completed protocol → view board → move tasks
- [ ] Answer clarification → see protocol unblock
- [ ] View all sprints → filter by project → filter by status
- [ ] View all tasks → filter by sprint → move to different column

### 5.2 Error Scenarios

- [ ] API unavailable → show error state with retry
- [ ] No data → show empty state with action
- [ ] Permission denied → show login prompt
- [ ] Validation error → show form errors inline

### 5.3 Accessibility

- [ ] All interactive elements keyboard accessible
- [ ] Focus states visible
- [ ] ARIA labels on icons
- [ ] Color contrast meets WCAG AA
- [ ] Screen reader navigation logical

---

## Appendix A: File Changes Summary

### Backend Files to Modify

| File | Change |
|------|--------|
| `devgodzilla/api/routes/sprints.py` | Add `GET /sprints` list endpoint |
| `devgodzilla/api/routes/tasks.py` | Add `GET /tasks` list endpoint |

### Frontend Files to Create

| File | Purpose |
|------|---------|
| `app/sprints/page.tsx` | New sprint list page (replace redirect) |
| `components/layout/breadcrumbs.tsx` | Breadcrumb navigation |
| `components/patterns/list-page.tsx` | Reusable list page pattern |
| `components/dashboard/activity-feed.tsx` | Dashboard activity widget |
| `components/dashboard/stat-cards.tsx` | Dashboard stat cards |
| `components/dashboard/sprint-progress.tsx` | Sprint progress widget |
| `components/dashboard/agent-health.tsx` | Agent health widget |

### Frontend Files to Modify

| File | Change |
|------|--------|
| `components/layout/sidebar.tsx` | Update navigation structure |
| `app/page.tsx` | Add dashboard widgets |
| `app/projects/[id]/page.tsx` | Add onboarding banner, breadcrumbs |
| `app/projects/[id]/components/workflow-tab.tsx` | Add "New Protocol" button |
| `lib/api/hooks/use-sprints.ts` | Update to use new list endpoint |
| `lib/api/hooks/use-tasks.ts` | Update to use new list endpoint |

---

## Appendix B: Related Documents

- [Frontend-Backend Refactoring Spec](./frontend-backend-refactoring-spec.md)
- [API Documentation](../api/README.md)
- [Component Library Storybook](../storybook/)

---

*Document Version: 1.0*  
*Created: 2026-02-23*  
*Author: Claude (AI Assistant)*
