# DevGodzilla (main stack)

DevGodzilla is the primary backend in this repo: a FastAPI API (`devgodzilla/api/app.py`) integrated with a Windmill-based UI (served via nginx).

## Quick start (Docker)

```bash
docker compose up --build -d
```

- UI: `http://localhost:8080` (or `$DEVGODZILLA_NGINX_PORT`)
- API docs: `http://localhost:8080/docs`

Notes:
- Windmill scripts/flows/apps are imported on startup by the one-shot `windmill_import` service (check `docker compose logs windmill_import`).
- DevGodzilla calls Windmill via `DEVGODZILLA_WINDMILL_URL`/`DEVGODZILLA_WINDMILL_TOKEN`/`DEVGODZILLA_WINDMILL_WORKSPACE` (Compose defaults workspace to `demo1`).

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
