# DevGodzilla (main stack)

DevGodzilla is the primary backend in this repo: a FastAPI API (`devgodzilla/api/app.py`) integrated with a Windmill-based UI (served via nginx).

## Quick start (local dev)

```bash
scripts/run-local-dev.sh dev
```

- UI: `http://localhost:8080` (or `$DEVGODZILLA_NGINX_PORT`)
- API docs: `http://localhost:8080/docs`

Notes:
- `docker compose up --build -d` starts infra only (nginx + windmill + workers + db + redis + lsp). The API + frontend run locally on the host.
- Import Windmill assets (optional): `scripts/run-local-dev.sh import`.

## Legacy backend (TasksGodzilla orchestrator)

The older TasksGodzilla orchestrator API is archived under `archive/` and is not part of the main stack.

```bash
docker compose -f archive/docker-compose.tasksgodzilla.yml up --build -d
```

- UI/console: `http://localhost:8011/console` (or `$TASKSGODZILLA_NGINX_PORT`)

## Docs

- DevGodzilla overview: `devgodzilla/README.md`
- DevGodzilla deployment: `DEPLOYMENT.md`
- DevGodzilla architecture docs: `docs/DevGodzilla/`
