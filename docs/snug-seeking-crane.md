# DevGodzilla Frontend Comprehensive Refactoring Plan

## Overview
Comprehensive refactor of UI components for Workflows/Pipeline/Task execution visualizations and Project sections. The original proposal suggested D3.js + WebSockets; the current implementation is tracking toward a lighter-weight approach (Recharts + SSE) with the option to upgrade to D3/WebSockets later if needed.

## Current Status (implemented vs remaining)

### Implemented
- Pipeline: DAG view exists (`frontend/components/visualizations/pipeline-dag.tsx`) and is wired into `frontend/components/workflow/pipeline-visualizer.tsx`.
- Real-time: SSE “message” stream endpoint exists at `/events/stream` (`devgodzilla/api/routes/events.py`) and is consumed in `frontend/app/projects/[id]/components/workflow-tab.tsx` via `frontend/lib/api/hooks/use-events.ts`.
- Sprint charts: burndown line + velocity trend charts exist (`frontend/components/visualizations/burndown-chart.tsx`, `frontend/components/visualizations/velocity-trend-chart.tsx`) and are used in `frontend/app/projects/[id]/components/sprint-tab.tsx`.
- Quality drilldown: protocol-level quality tab exists (`frontend/app/protocols/[id]/components/quality-tab.tsx`) with hooks in `frontend/lib/api/hooks/use-quality.ts`.
- Specification file viewing: spec/plan/tasks/checklist files are viewable in `frontend/app/specifications/[id]/page.tsx` using `/specifications/{id}/content`.
- Git tab: create branch dialog + per-branch CI column are implemented in `frontend/app/projects/[id]/components/branches-tab.tsx` with backend routes in `devgodzilla/api/routes/projects.py`.
- Policy UI: Monaco JSON editor + validation + pack version selector/preview are implemented in `frontend/app/projects/[id]/components/policy-tab.tsx`.
- Tables: global search + CSV export + column filters added to `frontend/components/ui/data-table.tsx` and enabled for common tables (runs/steps/protocol runs/artifacts/queues/branches).
- Phase 4 components: `frontend/components/features/agent-health-dashboard.tsx`, `frontend/components/features/quality-gates-drilldown.tsx`, `frontend/components/features/specification-viewer.tsx`, `frontend/components/features/event-feed.tsx`, `frontend/components/features/queue-stats-panel.tsx`, and `frontend/components/visualizations/cost-analytics-chart.tsx`.

### Still remaining / optional upgrades
- DAG rendering upgrades: swimlanes for `parallel_group`, proper edge routing/arrow rendering, zoom/pan, and better layout.
- Mobile kanban: dedicated small-screen UX for the sprint board.
- Task modal decomposition: split `frontend/components/agile/task-modal.tsx` into smaller components.
- Additional ops dashboards (optional).

## Critical Files Summary

| Component | File | Issues |
|-----------|------|--------|
| Pipeline Visualizer | `/frontend/components/workflow/pipeline-visualizer.tsx` | DAG view wired; remaining gap is richer DAG layout/edges |
| Pipeline DAG | `/frontend/components/visualizations/pipeline-dag.tsx` | Basic dependency-depth layout; no swimlanes/edge routing yet |
| Sprint Tab | `/frontend/app/projects/[id]/components/sprint-tab.tsx` | Burndown/velocity charts added; remaining gap is mobile UX |
| Task Modal | `/frontend/components/agile/task-modal.tsx` | ~500 lines monolith; still needs decomposition |
| SSE Events | `/devgodzilla/api/routes/events.py` | `/events/stream` added for default `EventSource.onmessage` |
| Tables | `/frontend/components/ui/data-table.tsx` | Global search + export + column filters implemented |
| Phase 4 Components | `/frontend/components/features/*` | Feature components now exist; wiring is optional |

---

## Phase 1: Foundation (Dependencies & Infrastructure)

### 1.1 Add D3.js Dependencies
```bash
cd frontend && pnpm add d3 d3-dag @types/d3
```

Status: optional (not required for current DAG implementation).

### 1.2 Create WebSocket Infrastructure
Create `/frontend/lib/websocket/`:
- `context.tsx` - WebSocketProvider with connection state, reconnection logic
- `hooks.ts` - `useWebSocket()`, `useSubscription(channel)`, `useProtocolUpdates(id)`
- `types.ts` - Message types, channel definitions

Status: deferred in favor of SSE (`/events/stream`) + query invalidation.

### 1.3 Create Base D3 Visualization Components
Create `/frontend/components/visualizations/`:
- `dag-graph.tsx` - Generic DAG renderer with D3.js (zoom, pan, node selection)
- `line-chart.tsx` - Reusable line chart for burndown/velocity

Status: partially implemented (charts exist via Recharts; generic DAG graph is not implemented).

---

## Phase 2: Pipeline Visualization Refactor

### 2.1 Fix `pipeline-visualizer.tsx` Bugs
- Remove undefined `fullscreen` variable reference (line 164)
- Remove hardcoded `availableAgents` array (lines 30-37)
- Import and use `useAgents()` hook to fetch real agents

Status: implemented.

### 2.2 Create Pipeline DAG Component
Create `/frontend/components/visualizations/pipeline-dag.tsx`:
- Parse `depends_on` and `parallel_group` from `StepRun[]`
- Render steps as DAG nodes (current: dependency-depth columns)
- Color nodes by status (running=blue, completed=green, failed=red)
- Show parallel groups as swimlanes (remaining)
- Display step timing (requires adding/deriving timing data; remaining)
- Click handlers for step navigation

Status: implemented (basic), with enhancements remaining.

### 2.3 Add View Mode Toggle
Modify `pipeline-visualizer.tsx`:
- Add state: `viewMode: "linear" | "dag" | "timeline"`
- Add toggle buttons in header
- Render `PipelineDAG` when `viewMode === "dag"`
- Keep existing linear view as option

Status: implemented for `"linear" | "dag"`; timeline remains optional.

### 2.4 Integrate WebSocket for Real-time Updates
- Subscribe to `protocol:{id}` channel
- Update step statuses in real-time
- Show live execution progress

Status: implemented via SSE (`/events/stream`) + query invalidation; WebSocket still optional.

---

## Phase 3: Sprint/Execution Improvements

### 3.1 Create Burndown Line Chart
Create `/frontend/components/visualizations/burndown-chart.tsx`:
- Proper line chart (not bar chart) using D3.js or recharts
- Dual lines: ideal burndown vs actual
- Area fill under lines
- Tooltip with date and points remaining
- Responsive design

Status: implemented (line chart via Recharts; area fill optional).

### 3.2 Create Velocity Trend Chart
Create `/frontend/components/visualizations/velocity-trend-chart.tsx`:
- Bar chart showing velocity per sprint
- Trend line overlay
- Average velocity indicator

Status: implemented (avg reference line included).

### 3.3 Refactor sprint-tab.tsx
- Replace bar chart (lines 233-281) with `BurndownChart` component
- Add velocity trend tab
- Integrate WebSocket for task status updates

Status: chart + tab implemented; real-time task updates remain optional (current data refresh is SWR-driven).

### 3.4 Mobile Kanban View
Create `/frontend/components/agile/mobile-kanban-view.tsx`:
- Tabbed interface showing one column at a time
- Swipe gestures for column navigation
- Responsive breakpoint in `sprint-board.tsx`

Status: not implemented yet.

---

## Phase 4: Missing API Features

### 4.1 Agent Health Dashboard
Create `/frontend/components/features/agent-health-dashboard.tsx`:
- Use `/agents/health` and `/agents/metrics` endpoints
- Grid of agent cards with health status
- Metrics: active/completed/failed steps
- Response time indicators

Create `/frontend/lib/api/hooks/use-agent-health.ts`:
- `useAgentHealth()` - fetch all agent health
- `useAgentMetrics()` - fetch agent metrics

Status: implemented (`frontend/components/features/agent-health-dashboard.tsx`, `frontend/lib/api/hooks/use-agent-health.ts`; existing `frontend/app/agents/page.tsx` also contains agent health UI).

### 4.2 Quality Gates Drilldown
Create `/frontend/components/features/quality-gates-drilldown.tsx`:
- Use `/protocols/{id}/quality/gates` endpoint
- List constitutional gates with pass/fail
- Expandable findings per gate
- Severity indicators

Extend `/frontend/lib/api/hooks/use-quality.ts`:
- Add `useProtocolQualityGates(protocolId)`

Status: implemented (protocol quality hooks + `frontend/app/protocols/[id]/components/quality-tab.tsx` + `frontend/components/features/quality-gates-drilldown.tsx`).

### 4.3 Specification Content Viewer
Create `/frontend/components/features/specification-viewer.tsx`:
- Use `/specifications/{id}/content` endpoint
- Markdown rendering for spec content
- Tabs for spec/plan/tasks/checklist files
- Syntax highlighting for code blocks

Extend `/frontend/lib/api/hooks/use-specifications.ts`:
- Add `useSpecificationContent(specId)`

Status: implemented (feature component `frontend/components/features/specification-viewer.tsx` renders Markdown with syntax highlighting; `frontend/app/specifications/[id]/page.tsx` also shows raw content).

### 4.4 Event Stream Display
Create `/frontend/components/features/event-feed.tsx`:
- Real-time event display using WebSocket
- Filter by event type
- Link to related protocols/steps

Create `/frontend/lib/api/hooks/use-events.ts`:
- `useEventStream()` - SSE subscription
- `useProtocolEvents(protocolId)`

Status: implemented via `frontend/lib/api/hooks/use-events.ts` + backend `/events/stream`; `frontend/components/features/event-feed.tsx` provides a real-time UI.

### 4.5 Queue Statistics Panel
Create `/frontend/components/features/queue-stats-panel.tsx`:
- Use `/queues` endpoint
- Queue depth visualization
- Jobs by status breakdown

Create `/frontend/lib/api/hooks/use-queues.ts`:
- `useQueueStats()`

Status: implemented (`devgodzilla/api/routes/queues.py` provides `/queues` and `/queues/stats`; hooks in `frontend/lib/api/hooks/use-queues.ts`; UI in `frontend/components/features/queue-stats-panel.tsx` and `frontend/app/ops/queues/page.tsx`).

### 4.6 Cost Analytics
Create `/frontend/components/visualizations/cost-analytics-chart.tsx`:
- Aggregate `cost_tokens` and `cost_cents` from runs
- Stacked bar chart by job type
- Cumulative cost line

Status: implemented (`frontend/components/visualizations/cost-analytics-chart.tsx`) and shown in `frontend/app/runs/page.tsx`.

---

## Phase 5: Project Section Enhancements

### 5.1 Enhance Git Tab
Modify `/frontend/app/projects/[id]/components/branches-tab.tsx`:
- Add commit history view (uses existing `useProjectCommits`)
- Add PR status widget (uses existing `useProjectPulls`)
- Create branch dialog
- Show CI status per branch

Status: implemented (including backend create/delete routes under `/projects/{id}/branches`).

### 5.2 Policy Configuration UI
Enhance `/frontend/app/projects/[id]/components/policy-tab.tsx`:
- Visual policy rule builder (tree view)
- Monaco editor for JSON editing
- Policy validation feedback
- Policy pack selector with preview

Status: implemented (tree view is a read-only JSON tree for overrides).

### 5.3 Add Search/Filter to Tables
Enhance `/frontend/components/ui/data-table.tsx`:
- Add global search input
- Add column-level filters
- Export functionality

Apply to pages:
- `/app/runs/page.tsx`
- (pages using `DataTable`, e.g. protocol steps/runs, run artifacts, ops queues, step runs)

Status: implemented (global search + column filters + export).

---

## Phase 6: Component Refactoring

### 6.1 Decompose Task Modal
Split `/frontend/components/agile/task-modal.tsx` (670+ lines) into:
- `task-form.tsx` - Form fields and validation
- `task-details-tab.tsx` - Details tab content
- `task-criteria-tab.tsx` - Acceptance criteria
- `task-activity-tab.tsx` - Activity timeline

Status: not implemented yet.

### 6.2 Create Reusable Hooks
Create `/frontend/lib/api/hooks/`:
- `use-git.ts` - Branch, commit, PR operations
- `use-queue.ts` - Queue statistics
- `use-events-stream.ts` - Real-time event streaming

Status: partially implemented via domain hooks (`frontend/lib/api/hooks/use-agent-health.ts`, `frontend/lib/api/hooks/use-queues.ts`, `frontend/lib/api/hooks/use-events.ts`). A dedicated `use-git.ts` wrapper is optional.

---

## Backend Changes (Optional for WebSocket)

### WebSocket Endpoint
Add to `/devgodzilla/api/app.py`:
- WebSocket route `/ws/events`
- Channel subscriptions: `protocol:{id}`, `step:{id}`, `events`
- Broadcast on status changes

Status: deferred in favor of SSE (`/events/stream`).

---

## Remaining Work Plan (gaps)

1. **Pipeline DAG upgrades** (`frontend/components/visualizations/pipeline-dag.tsx`)
   - Add swimlanes for `parallel_group` and improve node packing/spacing
   - Render routed edges with arrows (avoid “implied” edges)
   - Add zoom/pan and node focus/selection UX

2. **Mobile Kanban** (`frontend/components/agile/mobile-kanban-view.tsx`, `frontend/components/agile/sprint-board.tsx`)
   - Add responsive breakpoint + single-column/tabbed view
   - (Optional) swipe gestures

3. **Task modal decomposition** (`frontend/components/agile/task-modal.tsx`)
   - Split into smaller components + keep existing API surface
   - Add minimal unit tests where existing patterns exist

## Implementation Order

1. **Phase 1**: Dependencies + WebSocket infrastructure
2. **Phase 2**: Pipeline DAG visualization (most impactful)
3. **Phase 3**: Sprint/burndown improvements
4. **Phase 4**: Missing API features (agent health, quality gates)
5. **Phase 5**: Project section enhancements
6. **Phase 6**: Component refactoring (task modal)

---

## Files to Create

| Path | Purpose |
|------|---------|
| `/frontend/lib/websocket/context.tsx` | WebSocket provider |
| `/frontend/lib/websocket/hooks.ts` | WebSocket hooks |
| `/frontend/lib/websocket/types.ts` | Message types |
| `/frontend/components/visualizations/dag-graph.tsx` | Generic DAG |
| `/frontend/components/visualizations/pipeline-dag.tsx` | Step DAG |
| `/frontend/components/visualizations/burndown-chart.tsx` | Burndown line |
| `/frontend/components/visualizations/velocity-trend-chart.tsx` | Velocity bars |
| `/frontend/components/visualizations/cost-analytics-chart.tsx` | Cost charts |
| `/frontend/components/features/agent-health-dashboard.tsx` | Agent health |
| `/frontend/components/features/quality-gates-drilldown.tsx` | QA gates |
| `/frontend/components/features/specification-viewer.tsx` | Spec viewer |
| `/frontend/components/features/event-feed.tsx` | Event stream |
| `/frontend/components/features/queue-stats-panel.tsx` | Queue stats |
| `/frontend/components/agile/mobile-kanban-view.tsx` | Mobile kanban |
| `/frontend/lib/api/hooks/use-agent-health.ts` | Agent health hook |
| `/frontend/lib/api/hooks/use-events.ts` | Events hook |
| `/frontend/lib/api/hooks/use-queues.ts` | Queue stats hook |

## Files to Modify

| Path | Changes |
|------|---------|
| `/frontend/package.json` | Add d3, d3-dag, @types/d3 |
| `/frontend/components/workflow/pipeline-visualizer.tsx` | Fix bugs, add DAG view mode, use real agents |
| `/frontend/app/projects/[id]/components/sprint-tab.tsx` | Replace burndown, add velocity |
| `/frontend/components/agile/sprint-board.tsx` | Add mobile breakpoint |
| `/frontend/components/agile/task-modal.tsx` | Decompose into smaller files |
| `/frontend/components/ui/data-table.tsx` | Add search/filter |
| `/frontend/app/projects/[id]/components/branches-tab.tsx` | Add commits, PRs |
| `/frontend/app/projects/[id]/components/policy-tab.tsx` | Add policy editor |
| `/frontend/lib/api/hooks/use-quality.ts` | Add quality gates hook |
| `/frontend/lib/api/hooks/use-specifications.ts` | Add content hook |
| `/frontend/components/providers.tsx` | Wrap with WebSocketProvider |
| `/devgodzilla/api/app.py` | Add WebSocket endpoint |
