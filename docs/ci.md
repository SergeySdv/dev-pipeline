# DevGodzilla CI Notes

> Status: Active
> Scope: Current CI scripts and local parity
> Source of truth: `scripts/ci/*.sh`
> Last updated: 2026-02-21

## CI Scripts

- `scripts/ci/bootstrap.sh`
  - Creates `.venv`
  - Installs `requirements.txt` + `ruff`
- `scripts/ci/lint.sh`
  - `ruff check devgodzilla windmill scripts tests --select E9,F63,F7,F82`
- `scripts/ci/typecheck.sh`
  - `compileall` over runtime directories + import smoke
- `scripts/ci/test.sh`
  - Runs unit tests (`tests/test_devgodzilla_*.py -k "not integration"`)
  - Runs real-agent E2E (`tests/e2e/test_devgodzilla_cli_real_agent.py`)
  - Requires `opencode` binary available
- `scripts/ci/build.sh`
  - Build/config validation checks for container workflows

## Local Parity

```bash
scripts/ci/bootstrap.sh
scripts/ci/lint.sh
scripts/ci/typecheck.sh
scripts/ci/test.sh
scripts/ci/build.sh
```

## Operational Notes

- CI script behavior may report status via `scripts/ci/report.sh` when present.
- `scripts/ci/test.sh` is intentionally strict and expects real agent tooling for E2E path.
- For architecture docs governance and canonical references, see `docs/DevGodzilla/CURRENT_STATE.md` and `docs/DevGodzilla/ARCHITECTURE.md`.

## Live Harness (Nightly + Manual)

Live harness entrypoint:

- `scripts/ci/test-harness-live.sh`

Default GitHub repo coverage:

- `HARNESS_GITHUB_OWNER=ilyafedotov-ops`
- `HARNESS_GITHUB_REPOS=test-glm5-demo,SimpleAdminReporter,demo-spring`

Automation workflow:

- `.github/workflows/live-harness.yml`
- Triggers:
  - Nightly scheduled run
  - Manual `workflow_dispatch`
- Uploads run diagnostics from `runs/harness/**` as workflow artifacts.
- Runtime profile:
  - long-running live operations can take up to 45 minutes per stage (`2700s` stage timeout),
  - workflow job budget is set to 300 minutes.

Manual run examples:

```bash
# default matrix (3 seeded repos)
scripts/ci/test-harness-live.sh

# single scenario
HARNESS_SCENARIO=live_onboarding_demo_spring scripts/ci/test-harness-live.sh

# one-off repo URL override
HARNESS_REPO_URL_OVERRIDE=https://github.com/ilyafedotov-ops/demo-spring.git \
scripts/ci/test-harness-live.sh

# use dummy engine (no opencode binary required)
HARNESS_STEP_ENGINE=dummy scripts/ci/test-harness-live.sh
```

Key harness env vars:

- `DEVGODZILLA_RUN_E2E_HARNESS=1`
- `DEVGODZILLA_DB_URL` or `DEVGODZILLA_DB_PATH` (must match the backend DB used by `scripts/run-local-dev.sh backend start`)
- `HARNESS_GITHUB_OWNER`
- `HARNESS_GITHUB_REPOS`
- `HARNESS_REPO_URL_OVERRIDE`
- `HARNESS_SCENARIO`
- `HARNESS_CONTINUE_ON_ERROR` (`1` or `0`)
- `HARNESS_ONBOARD_MODE` (`windmill` or `agent`)
- `HARNESS_STEP_ENGINE` (`opencode` or `dummy`)
- `HARNESS_FEATURE_CYCLES` (default `2`; number of protocol/worktree/plan/execute feature cycles per scenario)
- `HARNESS_WINDMILL_AUTO_IMPORT` (`1` default; set `0` to skip `scripts/run-local-dev.sh import` during preflight)
- `HARNESS_WINDMILL_HEARTBEAT_TIMEOUT_SECONDS` (optional; fail stage if Windmill status/log stream is silent for this many seconds)
- `WINDMILL_JOB_TIMEOUT_SECONDS` (`3600` default in local compose; increases Windmill worker instance-wide max job duration)

## Adding New Repo Coverage

Contracts:

- Schema: `schemas/e2e-workflow-harness.schema.json`
- Scenarios: `tests/e2e/scenarios/*.json`
- Adapters: `tests/e2e/adapters/*.adapter.json`

Steps:

1. Copy an existing scenario JSON in `tests/e2e/scenarios/`.
2. Set `scenario_id`, `repo.owner`, `repo.name`, and `adapter_id`.
3. Prefer `owner` + `name`; keep `url` omitted unless you need a non-default Git URL.
4. Ensure workflow stage list reflects the intended onboarding mode and protocol flow.
5. Copy/create adapter JSON in `tests/e2e/adapters/`.
6. Define adapter `required_paths`, optional `path_aliases`, and `worktree_branch_expectations`.
7. Validate files by running:
   - `pytest -q tests/e2e/test_harness_scenario_loader.py`
8. Run a focused live harness pass:
   - `HARNESS_SCENARIO=<scenario_id> scripts/ci/test-harness-live.sh`
9. Cached checkout branch handling:
   - harness auto-falls back from configured `repo.default_branch` to `origin/HEAD` when they diverge (for example `main` vs `master`).
10. Feature implementation cycles:
   - `protocol_feature_cycles` runs repeated `protocol_create -> protocol_worktree -> protocol_plan -> step_execute` loops.
   - Control loop count with `HARNESS_FEATURE_CYCLES` (default `2`).

Failure outputs:

- Local diagnostics: `runs/harness/<timestamp>-<scenario_id>/diagnostics/`
- CI diagnostics: uploaded artifact from `runs/harness/**`
- Structured event stream: `runs/harness/<timestamp>-<scenario_id>/diagnostics/events.jsonl`
  - Event types: `run_started`, `stage_started`, `stage_retry`, `stage_succeeded`, `stage_failed`, `run_finished`
- Per-command live CLI logs: `runs/harness/<timestamp>-<scenario_id>/diagnostics/cli-<stage>-attempt-<n>-*.log`
- Windmill job payload snapshots: `runs/harness/<timestamp>-<scenario_id>/diagnostics/windmill-job-<job_id>.json`

DB alignment note:

- Windmill onboarding uses the backend API DB, while harness CLI commands use the local process DB config.
- If these differ, onboarding can enqueue successfully but return payload errors like `Project not found`.
- Fix by exporting the same `DEVGODZILLA_DB_URL` (or `DEVGODZILLA_DB_PATH`) for both harness and backend startup.
- `project_onboard_api` now uses `api_timeout_seconds` (default `2700`) for the `/actions/onboard` API call, so long discovery runs do not fail at the previous 30s HTTP timeout.
- Windmill server/workers now set `JOB_DEFAULT_TIMEOUT_SECS=${WINDMILL_JOB_TIMEOUT_SECONDS:-3600}` and workers set `TIMEOUT=${WINDMILL_JOB_TIMEOUT_SECONDS:-3600}` in compose to avoid killing long onboarding jobs after short default limits.
- `scripts/run-local-dev.sh import` now also updates Windmill `global_settings.job_default_timeout` to `WINDMILL_JOB_TIMEOUT_SECONDS` so DB-stored default timeout matches container env limits.

### Live Monitoring Commands

```bash
# watch structured harness lifecycle events
RUN_DIR="$(ls -td runs/harness/* | head -n1)"
tail -F "$RUN_DIR/diagnostics/events.jsonl" | jq -c

# watch all streamed CLI/opencode stage logs
tail -F "$RUN_DIR"/diagnostics/cli-*.log

# watch live Windmill job stream logs captured by harness polling
tail -F "$RUN_DIR"/diagnostics/windmill-job-*.log

# watch backend structured logs (includes opencode_output events)
tail -F /tmp/devgodzilla-harness-backend.log | rg --line-buffered "opencode_output|execute_step_started|execute_step_failed"
```
