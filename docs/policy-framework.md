# Policy Packs Framework (Project Classifications & Rules)

This document proposes a policy framework where each Project selects a **Policy Pack** (a classification-driven ruleset) that guides onboarding and protocol execution. The default enforcement mode is **warnings** (non-blocking), with the option to escalate selected rules to blocking later.

## Current implementation status (alpha)

The policy pack framework is partially implemented in code:
- Storage and API exist: policy packs are stored in the DB and managed via `GET/POST /policy_packs`; projects can select packs via `GET/PUT /projects/{id}/policy` (`tasksgodzilla/api/app.py`).
- Effective policy resolution exists: central pack + project overrides + optional repo-local override file `.tasksgodzilla/policy.json|yml|yaml` (`tasksgodzilla/services/policy.py`).
- Findings exist and are exposed: `GET /projects/{id}/policy/findings`, `GET /protocols/{id}/policy/findings`, `GET /steps/{id}/policy/findings`.
- Enforcement is warnings-first in most flows today: findings are primarily surfaced to the user; onboarding can optionally block based on enforcement mode, but execution/QA is not yet consistently gated by unanswered clarifications and/or blocking findings.

The largest missing piece is **first-class clarifications**: policy packs can define `clarifications`, but the system does not yet persist user answers or provide a dedicated API/UX flow for answering and unblocking runs. See “Gaps” and “Rollout strategy” below.

## Goals
- Allow a user to select a policy pack per project in the console/UI.
- Central management by default (stored in the orchestrator DB), with optional repo-local overrides.
- Apply policies consistently across onboarding, planning, execution, and QA with a single evaluation mechanism.
- Default to **warnings** (do not block protocols/steps), while keeping a clean path to “strict mode”.

## Non-goals (initially)
- Fine-grained per-protocol policy overrides (per-project only, per current requirement).
- Complex sandbox enforcement or “capabilities” execution constraints at the runner level.
- Full RBAC and multi-tenant org/roles (keep project-level tokens and optional per-project token).

## Terms
- **Policy Pack**: A versioned policy document with defaults, required artifacts, gates, and clarifications.
- **Project Policy**: The selected policy pack + project overrides + optional repo-local override file.
- **Finding**: The output of policy evaluation (warning/error/block), shown in the UI and stored as events.
- **Clarifications**: Structured questions that may be required for onboarding or execution. In warnings mode, unanswered clarifications do not block, but still produce findings.

## Project classifications (recommended default packs)

Treat “project type” selection during onboarding as the choice of policy pack key/version. Recommended baseline set:
- `default@1.0` — general purpose baseline.
- `beginner-guided@1.0` — extra structure and safer defaults for inexperienced users.
- `startup-fast@1.0` — minimal overhead, fast iteration.
- `team-standard@1.0` — balanced defaults and stronger step hygiene.
- `enterprise-compliance@1.0` — regulated/audited workflows intended for `policy_enforcement_mode=block`.

See `docs/project-classifications.md` for the exact pack payloads ready to `POST /policy_packs`.

## High-level design
1. Admin or user creates/selects a central Policy Pack in the orchestrator.
2. The Project selects a Policy Pack (by key/version) in the UI and optionally sets per-project overrides.
3. If enabled, the Project can also load a repo-local override file (e.g. `.tasksgodzilla/policy.yml`).
4. The orchestrator computes an **effective policy** for the project and uses it to:
   - generate onboarding clarification questions and defaults,
   - validate protocol plans/specs,
   - validate step artifacts and required sections,
   - influence model selection and QA policies,
   - emit Findings as warnings by default.

## Storage & configuration

### Central-first with optional repo-local
- **Central pack** is always available (source of truth).
- **Repo-local** is optional and can be disabled per project.
- The orchestrator should record the effective policy hash/version used for a ProtocolRun for audit and reproducibility.

### Recommended repo-local file
- Path: `.tasksgodzilla/policy.yml` (or `.json`)
- Scope: per-repo, applied only when:
  - the project enables repo-local policies, and
  - the repo is available locally (or fetched by worker).

## Data model changes (recommended)

### New table: `policy_packs`
- `id` (int)
- `key` (string, stable; e.g., `startup-fast`, `enterprise-compliance`)
- `name` (string)
- `description` (string)
- `version` (string; semver-like recommended)
- `status` (`active|deprecated|disabled`)
- `pack_json` (json)
- `created_at`, `updated_at`

### Project fields (choose one approach)
**Option A (simple, recommended)**: extend `projects` table:
- `policy_pack_key` (string)
- `policy_pack_version` (string, nullable; default latest active)
- `policy_overrides_json` (json, nullable)
- `policy_repo_local_enabled` (bool)
- `policy_effective_hash` (string, nullable; for caching/visibility)

**Option B (more flexible)**: new `project_policies` table:
- `project_id`, `policy_pack_id`, `overrides_json`, `repo_local_enabled`, `effective_hash`, timestamps

### ProtocolRun audit fields (recommended)
On `protocol_runs`:
- `policy_pack_key`, `policy_pack_version`, `policy_effective_hash`
- (Optional) snapshot of `policy_effective_json` for full reproducibility.

## Policy Pack schema (conceptual)
Policy packs should be expressive but stable. Start with JSON stored in DB; add YAML support at the repo-local layer.

### Suggested top-level shape
- `meta`: `{ key, name, version, description }`
- `defaults`:
  - `models`: `{ planning, decompose, exec, qa }`
  - `qa`: `{ policy: skip|light|full, auto_after_exec, auto_on_ci }`
  - `git`: `{ prefer_ssh, branch_pattern, draft_pr_default }`
  - `ci`: `{ provider, required_checks[] }`
- `requirements`:
  - `protocol_files`: required files under `.protocols/<run>/` (e.g., `plan.md`, `context.md`, `log.md`)
  - `step_sections`: required headings inside step files (e.g., `Sub-tasks`, `Verification`, `Rollback`, `Definition of Done`)
  - `artifacts`: required outputs (optional; can map to StepSpec outputs)
- `clarifications`:
  - list of questions with `key`, `question`, `recommended`, `options`, `blocking` (default false), `applies_to` (`onboarding|planning|execution|qa`)
- `enforcement`:
  - per-rule severity defaulting to `warning` (e.g., `missing_step_section: warning`)
  - ability to “escalate” for strict mode later (e.g., `mode: warn|block`)
- `constraints` (future-friendly):
  - flags like `forbid_stub_execution`, `require_ci_green_before_qa`, etc.

## Evaluation model (Findings)

### Findings structure
Each evaluation produces a list of Findings:
- `code`: stable identifier (e.g., `missing_step_section.verification`)
- `severity`: `info|warning|error|block` (initially treat everything as warning by default)
- `message`: human-readable description
- `scope`: `project|protocol|step`
- `suggested_fix`: short action guidance
- `metadata`: optional details (missing section name, file path, etc.)

### Where findings are emitted
- DB: append as Events (`event_type="policy_finding"`, metadata includes finding)
- UI: show in “Policy Findings” panel on project/protocol/step pages.

### Blocking vs warnings
Default behavior: only **warnings** are produced and nothing blocks.
Path to strict mode: allow project setting `policy_enforcement_mode = warn|block`, or per-rule override.

## Application points (where policy influences behavior)

### Onboarding (Project setup)
- Generate clarifications from policy pack (CI provider, models, git identity, required checks, etc.).
- Populate recommended defaults when user has no experience (e.g., smaller steps, `qa: light`, “manual approval” workflow).
- Emit findings for missing/unknown answers; optionally block when strict mode is enabled.

### Planning (protocol creation)
- Planning prompt should include “required step sections” and “required checks” from effective policy.
- If planning output is missing required fields, emit findings (and optionally re-plan).

### Execution and QA
- Check required files/sections exist before executing a step; emit findings if missing.
- Influence default model selection and engine choice from policy `defaults.models`.
- Influence QA policy default (`skip|light|full`) per project.

## Gaps (what still needs to land)

To make policy packs and “project classification” fully effective end-to-end, the system needs:
- **Clarifications as first-class state**: persisted questions + answers, with API + UI to answer, and clear gating rules when `blocking=true` and/or enforcement is `block`.
- **Prompt injection**: planning and decomposition prompts should include policy-required step sections and required checks so protocol artifacts are generated correctly on the first pass.
- **Optional gates**: consistent behavior in execution/QA to block (not fail) when required checks/sections/clarifications are missing in strict mode.

## API surface (recommended minimal set)

### Policy packs
- `GET /policy_packs` (list available packs)
- `GET /policy_packs/{key}` (get pack details + versions)
- `POST /policy_packs` (create; optional admin-only later)
- `POST /policy_packs/{key}/deprecate` (optional)

### Project policy selection
- `GET /projects/{project_id}/policy` (selection + overrides + repo-local toggle)
- `PUT /projects/{project_id}/policy` (set pack key/version, overrides, repo-local enabled)
- `GET /projects/{project_id}/policy/effective` (effective merged policy + hash)

### Findings and clarifications
- `GET /projects/{project_id}/policy/findings`
- `GET /protocols/{protocol_run_id}/policy/findings`
- `GET /steps/{step_run_id}/policy/findings`
- `GET /projects/{project_id}/clarifications` (answered/unanswered)
- `POST /projects/{project_id}/clarifications/{key}` (set answer)

## UI/Console requirements
- Project settings: select policy pack, show description, preview effective policy, configure overrides, toggle repo-local.
- Protocol detail view: show policy findings (warnings) and clarifications.
- Step detail view: highlight missing required sections/artifacts and show suggested fixes.

## Security considerations
- Treat repo-local policy as untrusted input; validate schema and cap size.
- Do not allow repo-local policy to inject secrets. Only reference env keys by name, never values.
- If later enabling “block”, ensure the caller identity is recorded for policy changes (audit trail).

## Migration and rollout
1. Add DB tables/fields, backfill existing projects with a default pack (e.g., `default@1.0`).
2. Ship UI selection and effective policy preview.
3. Implement evaluation hooks that emit warnings only (no behavior changes).
4. Iterate rules based on observed findings.
5. Add strict mode (optional), gated behind a per-project toggle.
