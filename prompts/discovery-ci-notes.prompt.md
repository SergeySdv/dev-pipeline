You are a senior engineering agent. Produce CI notes and minimally align CI scripts with this repo.

Inputs:
- Read `tasksgodzilla/DISCOVERY.md` and `tasksgodzilla/DISCOVERY_SUMMARY.json` if present.
- Read existing CI config (`.github/workflows/*`, `.gitlab-ci.yml`, etc.) and `scripts/ci/*.sh` if they exist.

Deliverables:
- `tasksgodzilla/CI_NOTES.md`: how CI is wired here (workflows/pipelines), the concrete commands to run (lint/typecheck/test/build), required tools, caches/artifacts, and TODOs/gaps.
- Update `scripts/ci/*.sh` minimally to fit the detected stack; add TODO comments if unsure.

Rules:
- Work from repo root.
- Do not modify DISCOVERY.md/ARCHITECTURE.md/API_REFERENCE.md in this pass.
- If a command is uncertain, add a concise TODO in the relevant CI script.

Checklist:
1) Map CI workflows to concrete commands.
2) Ensure hook scripts match actual stack (minimal edits).
3) Record caches/artifacts and gaps.

