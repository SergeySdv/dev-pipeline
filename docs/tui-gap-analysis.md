# TUI Gap Analysis & UX Improvements

## Overview

This document captures the gap analysis between backend services/API and TUI exposure, along with UX improvement recommendations.

**Analysis Date:** 2025-12-13
**Last Updated:** 2025-12-13
**TUI File:** `tasksgodzilla/cli/tui.py` (~1550 lines after improvements)
**API File:** `tasksgodzilla/api/app.py` (2389 lines, 50+ endpoints)

## Implementation Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 - Quick Wins | ✅ Complete | Loading spinners, confirmations, notifications, filter persistence |
| Phase 2 - Feature Gaps | ✅ Complete | Clarifications, logs viewer, budget display, QA verdict, CI status |
| Phase 3 - Advanced | ⏳ Pending | Job inspector, artifact viewer, bulk ops, policy editor |
| Phase 4 - Polish | ⏳ Pending | Dark mode, custom keybindings, themes |

---

## Critical Missing Features (High Priority)

| Feature | Backend Status | TUI Status | Impact |
|---------|---------------|------------|--------|
| ~~**Clarifications UI**~~ | `ClarificationsService` + API ready | ✅ Implemented | ~~Blocks onboarding~~ → Modal + keyboard shortcut (k) |
| ~~**Step execution logs**~~ | 10 Codex endpoints available | ✅ Implemented | ~~Can't debug~~ → Log viewer modal + keyboard shortcut (l) |
| ~~**Budget tracking**~~ | `BudgetService` complete | ✅ Implemented | ~~Hit limits unexpectedly~~ → Shown in step details |
| ~~**CI/CD status**~~ | `/protocols/{id}/ci/summary` exists | ✅ Implemented | ~~Can't see PR status~~ → CI panel in protocol detail |
| ~~**QA verdict details**~~ | `QualityService` available | ✅ Implemented | ~~Can't understand QA~~ → Verdict + summary in step details |

---

## UX Issues

| Issue | Location | Fix | Status |
|-------|----------|-----|--------|
| ~~No loading indicators~~ | `tui.py:404,517` | Show spinner during async ops | ✅ Fixed (Phase 1) |
| ~~No confirmation dialogs~~ | Actions run immediately | Add confirm for cancel/retry | ✅ Fixed (Phase 1) |
| Error details truncated | `tui.py:1077-1082` | Expandable error panel | ⏳ Pending |
| ~~Filter state lost on refresh~~ | `tui.py:1224` | Persist filter selection | ✅ Fixed (Phase 1) |
| ~~No success feedback~~ | Post-action | Toast/notification on success | ✅ Fixed (Phase 1) |

---

## API Endpoints Not Wired to TUI

### Codex Run Debugging (10 endpoints)
- `GET /codex/runs` - Full run history (⏳ Phase 3)
- `GET /codex/runs/{run_id}` - Individual run details (⏳ Phase 3)
- ~~`GET /codex/runs/{run_id}/logs`~~ - Full logs (✅ Phase 2 - via log viewer)
- `GET /codex/runs/{run_id}/logs/tail` - Incremental logs (⏳ Phase 3)
- `GET /codex/runs/{run_id}/logs/stream` - SSE log streaming (⏳ Phase 3)
- `GET /codex/runs/{run_id}/artifacts` - Artifact listing (⏳ Phase 3)
- `GET /codex/runs/{run_id}/artifacts/{id}/content` - Artifact content (⏳ Phase 3)
- `GET /protocols/{id}/runs` - Protocol runs history (⏳ Phase 3)
- ~~`GET /steps/{id}/runs`~~ - Step execution history (✅ Phase 2)

### Policy Management (4 endpoints)
- `GET /policy_packs` - List available policies (⏳ Phase 3)
- `POST /policy_packs` - Create policy pack (⏳ Phase 3)
- `GET /projects/{id}/policy` - Project policy (⏳ Phase 3)
- `PUT /projects/{id}/policy` - Update project policy (⏳ Phase 3)

### Clarifications (4 endpoints)
- ~~`GET /projects/{id}/clarifications`~~ - Project clarifications (✅ Phase 2)
- ~~`POST /projects/{id}/clarifications/{key}`~~ - Answer project clarification (✅ Phase 2)
- ~~`GET /protocols/{id}/clarifications`~~ - Protocol clarifications (✅ Phase 2)
- ~~`POST /protocols/{id}/clarifications/{key}`~~ - Answer protocol clarification (✅ Phase 2)

### CI/CD (1 endpoint)
- ~~`GET /protocols/{id}/ci/summary`~~ - CI/CD status summary (✅ Phase 2)

---

## Services Not Surfaced in TUI

| Service | Key Methods | Why It Matters |
|---------|-------------|----------------|
| `BudgetService` | `check_protocol_budget()`, `check_step_budget()` | Show token usage before hitting limits |
| `PolicyService` | `evaluate_protocol()`, `evaluate_step()` | Display what policies are blocking actions |
| `PromptService` | `resolve()`, `build_qa_context()` | Debug what's being sent to engines |
| `ClarificationsService` | `set_clarification_answer()` | Answer questions from TUI |
| `DecompositionService` | `decompose_protocol()` | Visibility into step breakdown |

---

## Implementation Phases

### Phase 1 - Quick Wins (UX Polish)

1. **Add loading spinners** for async operations (spec audit, import, refresh)
2. **Add confirmation dialogs** for destructive actions (cancel protocol, retry)
3. **Persist step filter** across refresh cycles
4. **Show success notifications** after successful actions
5. **Auto-scroll events** to follow latest in real-time

### Phase 2 - Feature Gaps (High Value)

1. **Clarifications modal** - Answer project/protocol questions from TUI
2. **Step logs viewer** - Browse Codex run logs for failed steps
3. **Budget display panel** - Show token usage per step/protocol
4. **QA verdict panel** - Explain why QA passed/failed
5. **CI status display** - Show PR URL and pipeline checks

### Phase 3 - Advanced Features

1. **Job inspector** - Full-page Codex run browser
2. **Artifact viewer** - Browse step artifacts
3. **Bulk operations** - Retry all, approve all, cancel all
4. **Policy editor** - Create/edit policies in TUI
5. **Performance dashboard** - Token usage, step timings, cost breakdown

### Phase 4 - Polish

1. Dark mode toggle
2. Custom keybindings config
3. Theme/color scheme customization
4. Workspace switching for multi-project setups
5. Session persistence across restarts

---

## Feature Parity Comparison

| Feature | CLI | TUI | API | Status |
|---------|-----|-----|-----|--------|
| List projects | ✓ | ✓ | ✓ | Complete |
| Create project | ✓ | ✓ | ✓ | Complete |
| List protocols | ✓ | ✓ | ✓ | Complete |
| Create protocol | ✓ | ✓ | ✓ | Complete |
| Start protocol | ✓ | ✓ | ✓ | Complete |
| Pause/resume | ✓ | ✓ | ✓ | Complete |
| Cancel protocol | ✓ | ✓ | ✓ | Complete |
| List steps | ✓ | ✓ | ✓ | Complete |
| Run step | ✓ | ✓ | ✓ | Complete |
| Run QA | ✓ | ✓ | ✓ | Complete |
| Approve step | ✓ | ✓ | ✓ | Complete |
| Open PR | ✓ | ✓ | ✓ | Complete |
| Answer clarifications | ✓ | ✓ | ✓ | Complete (Phase 2) |
| View budgets | ✗ | ✓ | ✗ | Complete (Phase 2) |
| View CI status | ✗ | ✓ | ✓ | Complete (Phase 2) |
| View execution logs | Partial | ✓ | ✓ | Complete (Phase 2) |
| View QA verdicts | Partial | ✓ | ✓ | Complete (Phase 2) |
| View policy findings | ✗ | ✗ | Partial | **Gap** |
| Browse artifacts | ✗ | ✗ | ✓ | **Phase 3** |

---

## Data Fields Not Displayed

### Projects View
- `ci_provider` - Available but not shown
- `project_classification` - Available but not shown
- `default_models` - Available but not shown

### Protocols View
- `worktree_path` - Available but not shown
- `pr_number`, `pr_url` - Available from CI summary but not shown

### Steps View
- Detailed `runtime_state` - Shown as raw JSON, not formatted

### Codex Runs (Not Accessible)
- All 10+ codex run endpoints inaccessible from TUI
- Run history, artifacts, logs unavailable
