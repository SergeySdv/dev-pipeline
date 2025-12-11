You are a senior engineering agent. Perform a *repository inventory* and produce durable discovery artifacts.

Deliverables (write files under `tasksgodzilla/`; do not rely on terminal output):
- `tasksgodzilla/DISCOVERY.md`: languages/frameworks, build/test tools, entrypoints/CLI targets, dependencies, data/config requirements, env vars/secrets, test fixtures, third-party services.
- `tasksgodzilla/DISCOVERY_SUMMARY.json`: a machine-readable summary used by follow-up prompts.

Rules:
- Work from repo root (CWD is the repo root).
- Do not remove existing code/configs; do not alter `.protocols/` contracts.
- Keep scope to inventory only; do NOT write ARCHITECTURE.md, API_REFERENCE.md, or CI_NOTES.md in this pass.

What to include:
1) Inventory: detect languages/build tools (`package.json`, `pyproject.toml`, `pom.xml`, `go.mod`, Make/Cargo/etc.), data/fixtures, env vars/secrets, external services.
2) Entry points: CLIs, servers, scripts, jobs, workers.
3) CI touchpoints: list existing workflows/pipelines and hook scripts, but do not edit yet.

`DISCOVERY_SUMMARY.json` format (top-level keys; keep values concise):
```json
{
  "languages": [],
  "frameworks": [],
  "build_tools": [],
  "lint_tools": [],
  "typecheck_tools": [],
  "test_tools": [],
  "package_managers": [],
  "entrypoints": {
    "clis": [],
    "servers": [],
    "workers": [],
    "scripts": []
  },
  "ci": {
    "github_workflows": [],
    "gitlab_pipelines": [],
    "ci_scripts": []
  },
  "env_vars": [],
  "data_stores": [],
  "external_services": [],
  "notes": []
}
```

