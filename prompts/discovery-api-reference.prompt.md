You are a senior engineering agent. Produce a callable-surface reference for this repo.

Inputs:
- Read `tasksgodzilla/DISCOVERY.md` and `tasksgodzilla/DISCOVERY_SUMMARY.json` if present.

Deliverable:
- `tasksgodzilla/API_REFERENCE.md`: callable surfaces in this repo (HTTP endpoints, CLIs, scripts, functions); include paths/verbs/flags, sample requests/responses or usage examples, auth/permissions, expected inputs/outputs.

Rules:
- Work from repo root.
- Do not modify other discovery files in this pass.
- Prefer concrete, grep-able names/paths; add TODOs if unsure.

Checklist:
1) Enumerate HTTP APIs (routes, verbs, auth).
2) Enumerate CLIs/scripts (entrypoints, flags, examples).
3) Enumerate notable library surfaces if this is a library.

