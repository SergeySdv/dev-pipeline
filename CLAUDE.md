# CLAUDE.md (DevGodzilla)

This file provides guidance for agentic coding tools when working in this repository.

## Default stack: DevGodzilla

DevGodzilla is the primary backend in this repo:
- API: `devgodzilla/api/app.py` (FastAPI)
- UI: Windmill (served via `nginx.devgodzilla.conf` in `docker-compose.yml`)
- Windmill assets: `windmill/flows/devgodzilla/`, `windmill/scripts/devgodzilla/`

Legacy TasksGodzilla guidance is archived at `docs/legacy/tasksgodzilla/CLAUDE.md`.

## Common commands

### Run (Docker Compose)

- Start stack: `docker compose up --build -d`
- UI: `http://localhost:8080` (or `$DEVGODZILLA_NGINX_PORT`)
- API docs: `http://localhost:8080/docs`

### Lint / tests

- Lint: `scripts/ci/lint.sh`
- Tests: `scripts/ci/test.sh`

## DevGodzilla docs

- Overview: `devgodzilla/README.md`
- Deployment: `DEPLOYMENT.md`
- Architecture: `docs/DevGodzilla/`

