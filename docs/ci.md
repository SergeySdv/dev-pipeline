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
