# Repository Guidelines

## Project Structure & Module Organization
- `devgodzilla/` is the primary backend: FastAPI API, services layer, engines, Windmill integration.
- `windmill/` contains Windmill scripts/flows/apps exported from this repo (DevGodzilla workspace).
- `Origins/` contains vendored upstream sources (Windmill, spec-kit, etc); avoid editing unless explicitly required.
- `scripts/` holds operational CLIs and `scripts/ci/*.sh` hooks for lint/typecheck/tests/build.
- `tests/` uses `pytest` for DevGodzilla API/service/workflow coverage (`tests/test_devgodzilla_*.py`).
- `docs/` and `prompts/` contain process guidance and reusable agent prompts; `schemas/` stores JSON Schemas.

## Build, Test, and Development Commands
- Bootstrap env: `scripts/ci/bootstrap.sh` (creates `.venv`, installs `requirements.txt` + `ruff`).
- Lint: `scripts/ci/lint.sh` (`ruff check devgodzilla windmill scripts tests --select E9,F63,F7,F82`).
- Typecheck: `scripts/ci/typecheck.sh` (compileall + import smoke for key modules).
- Tests: `scripts/ci/test.sh` (`pytest -q tests/test_devgodzilla_*.py`).
- Full stack (default): `docker compose up --build -d` starts everything — nginx, windmill, workers, db, devgodzilla-api, and frontend. Access the app at `http://localhost:8080/console`, Windmill at `http://localhost:8080`.
- Local dev manager: `scripts/run-local-dev.sh` — `up` builds and starts the full Docker stack; `backend`/`frontend` subcommands still available for host-side iteration.
  - Full stack: `scripts/run-local-dev.sh up`
  - Backend on host: `scripts/run-local-dev.sh backend start|stop|restart|status`
  - Frontend on host: `scripts/run-local-dev.sh frontend start|stop|restart|status`
  - Host dev mode: `scripts/run-local-dev.sh dev` (runs backend + frontend on host against Docker infra)
- Default Docker routing uses `nginx.devgodzilla.conf` (all services resolved by Docker's internal DNS; no `host.docker.internal` needed).
- Windmill bootstrap import (one-shot): `scripts/run-local-dev.sh import` (or `docker compose -f docker-compose.devgodzilla.yml up --build -d windmill_import`).
- Windmill JS transforms: `WINDMILL_FEATURES` defaults to `static_frontend python deno_core` (set `WINDMILL_FEATURES="static_frontend python"` to skip `deno_core`, but flows that use JavaScript `input_transforms` will not work).

## Coding Style & Naming Conventions
- Python 3.12, PEP8/black-like formatting with 4-space indents; prefer explicit imports and type hints.
- Module/files: `snake_case.py`; classes: `CamelCase`; functions/vars: `snake_case`; constants/env keys: `UPPER_SNAKE`.
- Centralize config via `devgodzilla.config.load_config()` and log through `devgodzilla.logging.get_logger()` for structured output.
- When touching Windmill scripts/flows/apps, mirror existing naming and paths under `windmill/`.

## Testing Guidelines
- Add/extend `pytest` cases next to existing patterns (e.g., `tests/test_devgodzilla_windmill_workflows.py`).
- Prefer small, isolated units; use temp SQLite DBs for API tests and override Windmill via dependency injection for deterministic behavior.
- Keep golden path + error path assertions; only hit real Windmill in local/manual tests (not CI).

## Commit & Pull Request Guidelines
- Follow the repo’s short, typed subject style: `feat:`, `chore:`, `fix:`, `docs:` (see `git log`).
- Scope commits narrowly and keep messages imperative (`feat: add worker retry backoff`). For protocol work, include the protocol tag (`[protocol-NNNN/YY]`) when relevant.
- PRs should summarize changes, list test commands run, call out config/env impacts (e.g., new `DEVGODZILLA_*` vars), and include console/API screenshots when UI behavior changes.

## Security & Configuration Tips
- Never commit real tokens or DB URLs; rely on env vars (`DEVGODZILLA_DB_URL`, `DEVGODZILLA_DB_PATH`, `DEVGODZILLA_WINDMILL_TOKEN`).
- For local Windmill tokens, use `DEVGODZILLA_WINDMILL_ENV_FILE` (defaults to `windmill/apps/devgodzilla-react-app/.env.development`), which is expected to be local-only.
- Default agent/engine: `opencode` with model `zai-coding-plan/glm-4.6` (override via `DEVGODZILLA_OPENCODE_MODEL` or agent config YAML).
