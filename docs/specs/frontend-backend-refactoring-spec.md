# Frontend-Backend Refactoring Specification

**Version:** 1.0  
**Date:** 2026-02-23  
**Status:** Draft  
**Author:** Droid Analysis

## Executive Summary

This specification documents the identified mismatches, wiring issues, and UI/UX gaps between the DevGodzilla frontend (Next.js/React) and backend (FastAPI) systems. It provides a comprehensive refactoring plan with prioritized implementation phases.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Critical Wiring Issues](#2-critical-wiring-issues)
3. [Data Structure Mismatches](#3-data-structure-mismatches)
4. [Navigation & Routing Issues](#4-navigation--routing-issues)
5. [UI/UX Usability Gaps](#5-uiux-usability-gaps)
6. [Refactoring Plan](#6-refactoring-plan)
7. [Implementation Details](#7-implementation-details)
8. [Testing Strategy](#8-testing-strategy)
9. [Migration Guide](#9-migration-guide)

---

## 1. Current State Analysis

### 1.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js 14)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Pages     │  │ Components  │  │    Hooks    │              │
│  │  (app/*)    │──│ (components)│──│ (lib/api)   │              │
│  └─────────────┘  └─────────────┘  └──────┬──────┘              │
│                                            │                     │
│  ┌─────────────────────────────────────────┴──────────────────┐ │
│  │                    API Client (apiClient)                   │ │
│  │              fetch() → /api/* (relative paths)             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/JSON
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Routes    │  │  Services   │  │   Database  │              │
│  │ (api/routes)│──│ (services)  │──│  (db/*.py)  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  Schemas: devgodzilla/api/schemas.py                            │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Files

| Component | Frontend | Backend |
|-----------|----------|---------|
| API Types | `lib/api/types.ts` | `api/schemas.py` |
| API Client | `lib/api/client.ts` | N/A |
| API Routes | `lib/api/hooks/*.ts` | `api/routes/*.py` |
| Query Keys | `lib/api/query-keys.ts` | N/A |

---

## 2. Critical Wiring Issues

### 2.1 Missing Backend Endpoints

#### Issue #1: Protocol Spec Endpoint

**Location:** Frontend `lib/api/hooks/use-protocols.ts:67`

```typescript
// Frontend call
export function useProtocolSpec(protocolId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.protocols.spec(protocolId!),
    queryFn: () => apiClient.get<ProtocolSpec>(`/protocols/${protocolId}/spec`),
    enabled: !!protocolId,
  })
}
```

**Backend Status:** ❌ Missing - No `/protocols/{id}/spec` endpoint exists

**Impact:** 
- Protocol detail page "Spec" tab fails silently
- 404 error in console
- Users cannot view protocol specifications

**Fix Required:**
```python
# Add to devgodzilla/api/routes/protocols.py

@router.get("/protocols/{protocol_id}/spec")
def get_protocol_spec(
    protocol_id: int,
    db: Database = Depends(get_db),
):
    """Get spec associated with a protocol run."""
    run = db.get_protocol_run(protocol_id)
    
    # Extract spec from speckit_metadata
    spec_data = run.speckit_metadata or {}
    
    return {
        "spec_hash": spec_data.get("spec_hash"),
        "validation_status": spec_data.get("validation_status"),
        "validated_at": spec_data.get("validated_at"),
        "spec": spec_data.get("spec", {}),
    }
```

---

#### Issue #2: Protocol Runs Endpoint

**Location:** Frontend `lib/api/hooks/use-protocols.ts:78`

```typescript
// Frontend call
export function useProtocolRuns(protocolId: number | undefined, filters?: RunFilters) {
  return useQuery({
    queryKey: queryKeys.protocols.runs(protocolId!, filters),
    queryFn: () => apiClient.get<CodexRun[]>(`/protocols/${protocolId}/runs${queryString}`),
    enabled: !!protocolId,
  })
}
```

**Backend Status:** ❌ Missing - Only `/runs` exists, not `/protocols/{id}/runs`

**Impact:**
- "Runs" tab on protocol detail page shows no data
- Users cannot see execution history for a specific protocol

**Fix Required:**
```python
# Add to devgodzilla/api/routes/protocols.py

@router.get("/protocols/{protocol_id}/runs", response_model=List[schemas.JobRunOut])
def list_protocol_runs(
    protocol_id: int,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 200,
    db: Database = Depends(get_db),
):
    """List job runs for a specific protocol."""
    try:
        db.get_protocol_run(protocol_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    return db.list_job_runs(
        protocol_run_id=protocol_id,
        status=status,
        job_type=job_type,
        limit=limit,
    )
```

---

#### Issue #3: Open PR Action

**Location:** Frontend `app/protocols/[id]/page.tsx:54`

```typescript
// Frontend action handler
const canOpenPR = protocol.status === "completed" || protocol.status === "running"

// Button in UI
{canOpenPR && (
  <Button variant="outline" onClick={() => handleAction("open_pr")} disabled={protocolAction.isPending}>
    <GitPullRequest className="mr-2 h-4 w-4" />
    Open PR
  </Button>
)}
```

**Backend Status:** ❌ Missing - Only these actions exist:
- `start`
- `pause`
- `resume`
- `cancel`
- `retry_latest`
- `run_next_step`
- `sync-to-sprint`

**Impact:**
- "Open PR" button does nothing when clicked
- Users cannot create PRs from completed protocols

**Fix Required:**
```python
# Add to devgodzilla/api/routes/protocols.py

class OpenPRRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    draft: bool = False

@router.post("/protocols/{protocol_id}/actions/open_pr")
def open_protocol_pr(
    protocol_id: int,
    request: OpenPRRequest = OpenPRRequest(),
    ctx: ServiceContext = Depends(get_service_context),
    db: Database = Depends(get_db),
):
    """Open a pull request for a completed protocol."""
    run = db.get_protocol_run(protocol_id)
    
    if run.status not in ["completed", "running"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot open PR for protocol in {run.status} state"
        )
    
    project = db.get_project(run.project_id)
    
    # Use git service to create PR
    # ... implementation details ...
    
    return {
        "pr_url": pr_url,
        "pr_number": pr_number,
        "message": "Pull request created successfully",
    }
```

---

### 2.2 Status Enum Mismatches

#### Issue #4: Protocol Status Mismatch

**Backend Enum** (`api/schemas.py`):
```python
class ProtocolStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

**Frontend Type** (`lib/api/types.ts`):
```typescript
export type ProtocolStatus =
  | "pending"
  | "planning"
  | "planned"      // ❌ NOT IN BACKEND
  | "running"
  | "paused"
  | "blocked"      // ❌ NOT IN BACKEND
  | "failed"
  | "cancelled"
  | "completed"
```

**Impact:**
- Status pills may display incorrect colors for `planned`/`blocked`
- Conditional logic in UI may not work correctly
- Type safety is compromised

**Fix Options:**

Option A - Add to Backend (Recommended):
```python
class ProtocolStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    PLANNED = "planned"      # NEW
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"      # NEW
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

Option B - Remove from Frontend:
```typescript
export type ProtocolStatus =
  | "pending"
  | "planning"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled"
```

**Recommendation:** Option A - Add to backend for better state granularity

---

#### Issue #5: Step Status Mismatch

**Backend Enum** (`api/schemas.py`):
```python
class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
```

**Frontend Type** (`lib/api/types.ts`):
```typescript
export type StepStatus = 
  | "pending" 
  | "running" 
  | "needs_qa"    // ❌ NOT IN BACKEND
  | "completed" 
  | "failed" 
  | "cancelled"   // ❌ NOT IN BACKEND
  | "blocked"
```

**Fix Required:**
```python
# Add to backend
class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    NEEDS_QA = "needs_qa"    # NEW
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"  # NEW
```

---

## 3. Data Structure Mismatches

### 3.1 ProtocolRun Type Mismatch

| Field | Frontend Type | Backend Schema | Issue |
|-------|--------------|----------------|-------|
| `flow_path` | `string \| null` | Not returned | Flow info empty |
| `flow_status` | `string \| null` | Not returned | Flow status unknown |
| `spec_hash` | Direct field | Nested in `speckit_metadata` | Wrong access path |
| `spec_validation_status` | Direct field | Nested in `speckit_metadata` | Wrong access path |
| `template_source` | Direct field | Not in schema | Always null |
| `template_config` | `Record<string, unknown>` | Not in schema | Always null |
| `protocol_root` | `string \| null` | Not returned | Path unknown |

**Frontend Code** (`lib/api/types.ts:55-80`):
```typescript
export interface ProtocolRun {
  id: number
  project_id: number
  protocol_name: string
  status: ProtocolStatus
  base_branch: string
  worktree_path: string | null
  protocol_root: string | null        // ❌ Not in backend
  description: string | null
  template_config: Record<string, unknown> | null  // ❌ Not in backend
  template_source: string | null      // ❌ Not in backend
  spec_hash: string | null            // ❌ Should be from speckit_metadata
  spec_validation_status: string | null  // ❌ Should be from speckit_metadata
  // ...
}
```

**Backend Schema** (`api/schemas.py:ProtocolOut`):
```python
class ProtocolOut(APIModel):
    id: int
    project_id: int
    protocol_name: str
    status: str
    base_branch: str
    worktree_path: Optional[str]
    summary: Optional[str] = None
    windmill_flow_id: Optional[str]    # ✓ Different name
    speckit_metadata: Optional[Dict[str, Any]]  # ✓ Nested structure
    created_at: Any
    updated_at: Any
```

**Fix Required - Option A (Backend adapter):**
```python
# Update ProtocolOut to flatten fields
class ProtocolOut(APIModel):
    # ... existing fields ...
    
    # Flattened speckit fields
    spec_hash: Optional[str] = None
    spec_validation_status: Optional[str] = None
    spec_validated_at: Optional[str] = None
    
    # Flow info
    flow_path: Optional[str] = None
    flow_status: Optional[str] = None
    
    # Template info
    template_source: Optional[str] = None
    template_config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_orm(cls, run):
        data = {
            'id': run.id,
            'protocol_name': run.protocol_name,
            # ... map other fields ...
        }
        
        # Flatten speckit_metadata
        meta = run.speckit_metadata or {}
        data['spec_hash'] = meta.get('spec_hash')
        data['spec_validation_status'] = meta.get('validation_status')
        data['spec_validated_at'] = meta.get('validated_at')
        
        # Add flow info from windmill_flow_id
        if run.windmill_flow_id:
            data['flow_path'] = f"flows/{run.windmill_flow_id}"
            # flow_status would need to be fetched from windmill
        
        return cls(**data)
```

**Fix Required - Option B (Frontend adapter):**
```typescript
// lib/api/adapters/protocol.ts

export function adaptProtocolRun(data: any): ProtocolRun {
  return {
    ...data,
    // Flatten speckit_metadata
    spec_hash: data.speckit_metadata?.spec_hash ?? null,
    spec_validation_status: data.speckit_metadata?.validation_status ?? null,
    spec_validated_at: data.speckit_metadata?.validated_at ?? null,
    // Map windmill_flow_id to flow info
    flow_path: data.windmill_flow_id ? `flows/${data.windmill_flow_id}` : null,
    flow_status: null, // Would need separate API call
  }
}
```

**Recommendation:** Option B - Keep backend simple, adapt in frontend

---

### 3.2 Protocol Artifact Mismatch

**Frontend Type** (`lib/api/types.ts:189-205`):
```typescript
export interface ProtocolArtifact {
  id: number
  protocol_run_id: number
  step_run_id: number | null
  run_id: string | null
  name: string
  kind: string          // ❌ Backend has 'type'
  path: string          // ❌ Not in backend
  sha256: string | null // ❌ Not in backend
  bytes: number | null  // ❌ Backend has 'size'
  created_at: string
}
```

**Backend Schema** (`api/schemas.py:ProtocolArtifactOut`):
```python
class ProtocolArtifactOut(ArtifactOut):
    step_run_id: int
    step_name: Optional[str] = None

class ArtifactOut(BaseModel):
    id: str
    type: str  # log|diff|file|report|json|text|unknown
    name: str
    size: int
    created_at: Optional[str] = None
```

**Fix Required:**
```typescript
// Update frontend type to match backend
export interface ProtocolArtifact {
  id: string
  step_run_id: number
  step_name: string | null
  type: string  // log|diff|file|report|json|text|unknown
  name: string
  size: number
  created_at: string | null
}

// Add adapter if needed for backwards compatibility
export function adaptProtocolArtifact(data: any): ProtocolArtifact {
  return {
    id: data.id,
    step_run_id: data.step_run_id,
    step_name: data.step_name,
    type: data.type,
    name: data.name,
    size: data.size,
    created_at: data.created_at,
  }
}
```

---

## 4. Navigation & Routing Issues

### 4.1 Broken Sidebar Links

**File:** `components/layout/sidebar.tsx:47`

```typescript
const navigationGroups: NavGroup[] = [
  {
    title: "Execute",
    icon: Zap,
    items: [
      { name: "Runs", href: "/runs", icon: PlayCircle },
      { name: "Protocols", href: "/protocols", icon: GitBranch },
      { name: "Sprints", href: "/execution", icon: Kanban },  // ❌ Wrong URL
      // ...
    ],
  },
  // ...
]
```

**Issue:** Sidebar links Sprints to `/execution` but the actual route is `/sprints`

**Fix:**
```typescript
{ name: "Sprints", href: "/sprints", icon: Kanban },
```

---

### 4.2 Missing Route Pages

| Route | Status | Required Page |
|-------|--------|---------------|
| `/projects` | ❌ Missing | List all projects |
| `/projects/new` | ❌ Missing | Create project wizard |
| `/sprints` | ✓ Exists | Sprint list |
| `/execution` | ❌ Broken redirect | Should not exist |

**Fix:** Create `/app/projects/page.tsx`:

```typescript
// app/projects/page.tsx
"use client"

import { useProjects } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { DataTable } from "@/components/ui/data-table"
import { Plus, FolderGit2 } from "lucide-react"
import Link from "next/link"

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects()

  if (isLoading) return <LoadingState message="Loading projects..." />

  return (
    <div className="container py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <Link href="/projects/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Project
          </Button>
        </Link>
      </div>
      
      {/* Project list implementation */}
    </div>
  )
}
```

---

## 5. UI/UX Usability Gaps

### 5.1 Missing Loading States

**Current State:** Most pages show text "Loading..." without proper skeleton

**Fix Required:** Add skeleton components for all data displays

```typescript
// components/skeletons/protocol-skeleton.tsx
export function ProtocolDetailSkeleton() {
  return (
    <div className="container py-8">
      <div className="mb-6">
        <Skeleton className="h-4 w-32 mb-4" />
        <Skeleton className="h-8 w-64 mb-2" />
        <Skeleton className="h-4 w-48" />
      </div>
      
      <div className="grid gap-4 md:grid-cols-5 mb-8">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-3 w-20" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-6 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
      
      <Skeleton className="h-96 w-full" />
    </div>
  )
}
```

### 5.2 Missing Error Boundaries

**Current State:** API errors crash entire pages

**Fix Required:** Add error boundaries

```typescript
// components/error-boundary.tsx
"use client"

import { Component, ReactNode } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertCircle, RefreshCw } from "lucide-react"

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      
      return (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Something went wrong
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {this.state.error?.message || "An unexpected error occurred"}
            </p>
            <Button onClick={() => this.setState({ hasError: false, error: null })}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
          </CardContent>
        </Card>
      )
    }

    return this.props.children
  }
}
```

### 5.3 Missing Confirmation Dialogs

**Current State:** Destructive actions execute immediately

**Fix Required:** Add confirmation for:
- Delete project
- Delete branch
- Cancel protocol
- Delete task

```typescript
// components/ui/confirm-dialog.tsx
interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: string
  confirmText?: string
  cancelText?: string
  variant?: "default" | "destructive"
  onConfirm: () => void
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "default",
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{cancelText}</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className={variant === "destructive" ? "bg-destructive text-destructive-foreground" : ""}
          >
            {confirmText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
```

### 5.4 Missing Search/Filter

**Current State:** Lists show all items without search capability

**Fix Required:** Add search and filter components

```typescript
// components/ui/data-table-toolbar.tsx
interface DataTableToolbarProps {
  searchKey?: string
  searchPlaceholder?: string
  filters?: FilterConfig[]
  onSearchChange: (value: string) => void
  onFilterChange: (key: string, value: string) => void
}

export function DataTableToolbar({
  searchPlaceholder = "Search...",
  filters = [],
  onSearchChange,
  onFilterChange,
}: DataTableToolbarProps) {
  return (
    <div className="flex items-center gap-4 py-4">
      <div className="relative flex-1 max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={searchPlaceholder}
          className="pl-8"
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>
      
      {filters.map((filter) => (
        <Select
          key={filter.key}
          onValueChange={(value) => onFilterChange(filter.key, value)}
        >
          <SelectTrigger className="w-32">
            <SelectValue placeholder={filter.label} />
          </SelectTrigger>
          <SelectContent>
            {filter.options.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ))}
    </div>
  )
}
```

---

## 6. Refactoring Plan

### Phase 1: Critical Fixes (Week 1)

| Task | Priority | Effort | Files |
|------|----------|--------|-------|
| Add `/protocols/{id}/spec` endpoint | P0 | 2h | `api/routes/protocols.py` |
| Add `/protocols/{id}/runs` endpoint | P0 | 2h | `api/routes/protocols.py` |
| Add `open_pr` action endpoint | P0 | 4h | `api/routes/protocols.py` |
| Fix status enums | P0 | 2h | `api/schemas.py`, `lib/api/types.ts` |
| Fix sidebar navigation URL | P0 | 0.5h | `components/layout/sidebar.tsx` |
| Add type adapters | P0 | 3h | `lib/api/adapters/*.ts` |

### Phase 2: Data Layer (Week 2)

| Task | Priority | Effort | Files |
|------|----------|--------|-------|
| Add error boundaries | P1 | 4h | `components/error-boundary.tsx` |
| Add loading skeletons | P1 | 6h | `components/skeletons/*.tsx` |
| Add toast notifications | P1 | 2h | All mutation hooks |
| Add optimistic updates | P1 | 4h | All mutation hooks |
| Add query retry logic | P1 | 2h | `lib/api/client.ts` |
| Align data types | P1 | 4h | `lib/api/types.ts` |

### Phase 3: UX Enhancements (Week 3-4)

| Task | Priority | Effort | Files |
|------|----------|--------|-------|
| Add confirmation dialogs | P2 | 4h | All destructive actions |
| Add search/filter to lists | P2 | 8h | All list pages |
| Add pagination | P2 | 6h | Server + client |
| Add keyboard shortcuts | P2 | 4h | Command palette |
| Improve status pills | P2 | 2h | `components/ui/status-pill.tsx` |
| Add refresh buttons | P2 | 2h | All data pages |

---

## 7. Implementation Details

### 7.1 New Backend Endpoints

```python
# File: devgodzilla/api/routes/protocols.py

# 1. Protocol Spec Endpoint
@router.get("/protocols/{protocol_id}/spec")
def get_protocol_spec(
    protocol_id: int,
    db: Database = Depends(get_db),
):
    """Get spec associated with a protocol run."""
    run = db.get_protocol_run(protocol_id)
    meta = run.speckit_metadata or {}
    
    return {
        "spec_hash": meta.get("spec_hash"),
        "validation_status": meta.get("validation_status"),
        "validated_at": meta.get("validated_at"),
        "spec": meta.get("spec", {}),
    }


# 2. Protocol Runs Endpoint  
@router.get("/protocols/{protocol_id}/runs", response_model=List[schemas.JobRunOut])
def list_protocol_runs(
    protocol_id: int,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 200,
    db: Database = Depends(get_db),
):
    """List job runs for a specific protocol."""
    try:
        db.get_protocol_run(protocol_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    runs = db.list_job_runs(
        protocol_run_id=protocol_id,
        status=status,
        job_type=job_type,
        limit=limit,
    )
    return [schemas.JobRunOut.model_validate(r) for r in runs]


# 3. Open PR Action Endpoint
class OpenPRRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    draft: bool = False

class OpenPRResponse(BaseModel):
    pr_url: str
    pr_number: int
    message: str

@router.post("/protocols/{protocol_id}/actions/open_pr", response_model=OpenPRResponse)
def open_protocol_pr(
    protocol_id: int,
    request: OpenPRRequest = OpenPRRequest(),
    ctx: ServiceContext = Depends(get_service_context),
    db: Database = Depends(get_db),
):
    """Open a pull request for a completed protocol."""
    run = db.get_protocol_run(protocol_id)
    
    if run.status not in ["completed", "running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot open PR for protocol in {run.status} state"
        )
    
    project = db.get_project(run.project_id)
    
    # Get branch name from worktree
    branch_name = None
    if run.worktree_path:
        # Extract branch from worktree
        # Implementation depends on git service
        pass
    
    # Create PR using git service
    # This would integrate with the git_provider service
    # ... implementation ...
    
    return OpenPRResponse(
        pr_url=f"https://github.com/owner/repo/pull/{pr_number}",
        pr_number=pr_number,
        message="Pull request created successfully",
    )
```

### 7.2 Frontend Type Adapters

```typescript
// File: lib/api/adapters/protocol.ts

import type { ProtocolRun, ProtocolArtifact } from "../types"

interface RawProtocolRun {
  id: number
  project_id: number
  protocol_name: string
  status: string
  base_branch: string
  worktree_path: string | null
  windmill_flow_id: string | null
  speckit_metadata: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export function adaptProtocol(data: RawProtocolRun): ProtocolRun {
  const meta = data.speckit_metadata || {}
  
  return {
    ...data,
    // Flatten speckit_metadata
    spec_hash: meta.spec_hash as string | null ?? null,
    spec_validation_status: meta.validation_status as string | null ?? null,
    spec_validated_at: meta.validated_at as string | null ?? null,
    // Map windmill_flow_id
    windmill_flow_id: data.windmill_flow_id,
    // Template fields (from metadata if available)
    template_source: meta.template_source as string | null ?? null,
    template_config: meta.template_config as Record<string, unknown> | null ?? null,
    // Protocol root
    protocol_root: meta.protocol_root as string | null ?? null,
    // Description
    description: meta.description as string | null ?? null,
  }
}

interface RawProtocolArtifact {
  id: string
  step_run_id: number
  step_name: string | null
  type: string
  name: string
  size: number
  created_at: string | null
}

export function adaptProtocolArtifact(data: RawProtocolArtifact): ProtocolArtifact {
  return {
    id: data.id,
    protocol_run_id: 0, // Would need to be passed in
    step_run_id: data.step_run_id,
    run_id: null,
    name: data.name,
    type: data.type,
    kind: data.type,
    path: "",
    sha256: null,
    bytes: data.size,
    size: data.size,
    created_at: data.created_at || new Date().toISOString(),
  }
}
```

### 7.3 Error Handling Setup

```typescript
// File: lib/api/hooks/use-query-with-error.ts

import { useQuery, UseQueryOptions } from "@tanstack/react-query"
import { toast } from "sonner"

export function useQueryWithError<TData, TError>(
  options: UseQueryOptions<TData, TError> & {
    errorMessage?: string
  }
) {
  return useQuery({
    ...options,
    onError: (error) => {
      const message = options.errorMessage || "An error occurred while fetching data"
      toast.error(message, {
        description: error instanceof Error ? error.message : "Unknown error",
      })
      options.onError?.(error)
    },
  })
}
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```typescript
// __tests__/api/adapters/protocol.test.ts
import { describe, it, expect } from "vitest"
import { adaptProtocol } from "@/lib/api/adapters/protocol"

describe("adaptProtocol", () => {
  it("should flatten speckit_metadata fields", () => {
    const raw = {
      id: 1,
      project_id: 1,
      protocol_name: "test",
      status: "running",
      base_branch: "main",
      worktree_path: null,
      windmill_flow_id: "flow-123",
      speckit_metadata: {
        spec_hash: "abc123",
        validation_status: "valid",
      },
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    }

    const result = adaptProtocol(raw)

    expect(result.spec_hash).toBe("abc123")
    expect(result.spec_validation_status).toBe("valid")
  })

  it("should handle null speckit_metadata", () => {
    const raw = {
      // ... same as above but speckit_metadata: null
      speckit_metadata: null,
    }

    const result = adaptProtocol(raw)

    expect(result.spec_hash).toBeNull()
    expect(result.spec_validation_status).toBeNull()
  })
})
```

### 8.2 Integration Tests

```python
# tests/test_devgodzilla_protocol_endpoints.py

def test_get_protocol_spec(client, db):
    """Test GET /protocols/{id}/spec endpoint"""
    # Create protocol with speckit_metadata
    protocol = db.create_protocol_run(
        project_id=1,
        protocol_name="test",
        status="running",
        speckit_metadata={
            "spec_hash": "abc123",
            "validation_status": "valid",
        }
    )
    
    response = client.get(f"/protocols/{protocol.id}/spec")
    assert response.status_code == 200
    data = response.json()
    assert data["spec_hash"] == "abc123"
    assert data["validation_status"] == "valid"


def test_list_protocol_runs(client, db):
    """Test GET /protocols/{id}/runs endpoint"""
    # Create protocol and runs
    protocol = db.create_protocol_run(...)
    run = db.create_job_run(protocol_run_id=protocol.id, ...)
    
    response = client.get(f"/protocols/{protocol.id}/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["run_id"] == run.run_id
```

---

## 9. Migration Guide

### 9.1 Breaking Changes

| Change | Impact | Migration |
|--------|--------|-----------|
| `ProtocolArtifact.kind` → `type` | Frontend | Update type and usages |
| Status enums extended | Backend | Add migrations for existing data |
| `ProtocolRun` fields flattened | Both | Use adapters |

### 9.2 Deployment Order

1. Deploy backend changes (add endpoints, extend enums)
2. Deploy frontend adapters
3. Remove old frontend code
4. Monitor for errors

### 9.3 Rollback Plan

1. Keep old endpoints with deprecation warnings
2. Feature flags for new UI components
3. Database migrations should be reversible

---

## Appendix A: Complete Endpoint Mapping

| Frontend Hook | Endpoint | Status |
|--------------|----------|--------|
| `useProtocols` | `GET /protocols` | ✅ |
| `useProtocol` | `GET /protocols/{id}` | ✅ |
| `useProtocolSteps` | `GET /protocols/{id}/steps` | ✅ |
| `useProtocolEvents` | `GET /protocols/{id}/events` | ✅ |
| `useProtocolSpec` | `GET /protocols/{id}/spec` | ❌ Missing |
| `useProtocolRuns` | `GET /protocols/{id}/runs` | ❌ Missing |
| `useProtocolArtifacts` | `GET /protocols/{id}/artifacts` | ✅ |
| `useProtocolQuality` | `GET /protocols/{id}/quality` | ✅ |
| `useProtocolPolicyFindings` | `GET /protocols/{id}/policy/findings` | ✅ |
| `useProtocolPolicySnapshot` | `GET /protocols/{id}/policy/snapshot` | ✅ |
| `useProtocolClarifications` | `GET /protocols/{id}/clarifications` | ✅ |
| `useProtocolFeedback` | `GET /protocols/{id}/feedback` | ✅ |
| `useProtocolFlow` | `GET /protocols/{id}/flow` | ✅ |
| `useProtocolSprint` | `GET /protocols/{id}/sprint` | ✅ |
| `open_pr` action | `POST /protocols/{id}/actions/open_pr` | ❌ Missing |

---

## Appendix B: Status Color Mapping

```typescript
// Recommended status pill colors

const statusColors: Record<string, { bg: string; text: string; icon: string }> = {
  // Protocol Status
  pending: { bg: "bg-gray-100", text: "text-gray-700", icon: "text-gray-500" },
  planning: { bg: "bg-blue-100", text: "text-blue-700", icon: "text-blue-500" },
  planned: { bg: "bg-indigo-100", text: "text-indigo-700", icon: "text-indigo-500" },
  running: { bg: "bg-green-100", text: "text-green-700", icon: "text-green-500" },
  paused: { bg: "bg-yellow-100", text: "text-yellow-700", icon: "text-yellow-500" },
  blocked: { bg: "bg-orange-100", text: "text-orange-700", icon: "text-orange-500" },
  completed: { bg: "bg-emerald-100", text: "text-emerald-700", icon: "text-emerald-500" },
  failed: { bg: "bg-red-100", text: "text-red-700", icon: "text-red-500" },
  cancelled: { bg: "bg-gray-100", text: "text-gray-500", icon: "text-gray-400" },
  
  // Step Status
  needs_qa: { bg: "bg-purple-100", text: "text-purple-700", icon: "text-purple-500" },
  skipped: { bg: "bg-gray-50", text: "text-gray-500", icon: "text-gray-400" },
}
```

---

**End of Specification**
