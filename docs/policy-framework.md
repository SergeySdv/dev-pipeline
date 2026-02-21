# Policy Packs Framework

> Status: Active
> Scope: Policy packs, effective policy resolution, and findings model
> Source of truth: `devgodzilla/services/policy.py`, `devgodzilla/api/routes/projects.py`, `devgodzilla/api/routes/policy_packs.py`
> Last updated: 2026-02-21

## Summary

Projects select a policy pack and can apply project overrides plus optional repo-local overrides. Findings are emitted primarily as warnings in current flows.

## Current Implementation Status

Implemented:

- Policy pack storage and management: `/policy_packs*`
- Project policy read/update: `/projects/{id}/policy`, `/projects/{id}/policy/effective`
- Findings endpoints:
  - `/projects/{id}/policy/findings`
  - `/protocols/{id}/policy/findings`
  - `/steps/{id}/policy/findings`
- Effective policy merge in service layer:
  - central pack
  - project overrides
  - optional repo-local policy file

Service reference: `devgodzilla/services/policy.py`

## Repo-Local Policy Files

Current loader supports both directories:

- `.devgodzilla/policy.json|yaml|yml`
- `.tasksgodzilla/policy.json|yaml|yml` (legacy compatibility)

## Goals

- Consistent policy defaults for onboarding/planning/execution/QA
- Structured findings with actionable messages
- Warnings-first behavior with a clean strict-mode path

## Related Docs

- `docs/project-classifications.md`
- `docs/DevGodzilla/API-ARCHITECTURE.md`
- `docs/DevGodzilla/CURRENT_STATE.md`
