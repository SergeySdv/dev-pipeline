# Project Classifications (Policy Packs)

> Status: Active
> Scope: Suggested policy pack classifications and payload guidance
> Source of truth: `devgodzilla/api/schemas.py`, `devgodzilla/services/policy.py`
> Last updated: 2026-02-21

This repository supports multiple project types through policy packs selected during onboarding or project configuration.

## Related Docs

- `docs/policy-framework.md`
- `docs/DevGodzilla/API-ARCHITECTURE.md`

## Recommended Classifications

| Classification | Pack key | Intended users |
|---|---|---|
| General purpose | `default` | Most projects |
| Beginner guided | `beginner-guided` | High guidance needs |
| Startup fast | `startup-fast` | Fast iteration with low overhead |
| Team standard | `team-standard` | Teams with established CI/review |
| Enterprise compliance | `enterprise-compliance` | Regulated workflows |

## API Target

Create/update packs via:

- `POST /policy_packs`

Payloads should match policy-pack create schema in `devgodzilla/api/schemas.py`.

## Notes

- Policy defaults may include model recommendations for planning/decomposition/execution/QA.
- Not every runtime path enforces policy-derived model defaults yet; behavior continues to evolve in service layer.
