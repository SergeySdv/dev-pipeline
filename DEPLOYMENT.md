# DevGodzilla Deployment Guide

## Prerequisites
- Docker & Docker Compose
- 8GB+ RAM recommended (for compiling Windmill)

## Architecture
The default local development setup is **hybrid**:
- **Docker (infra)**: `nginx`, `windmill`, workers, `db`, `redis`, `lsp`
- **Host (local processes)**: DevGodzilla backend (FastAPI) + DevGodzilla frontend (Next.js)

Nginx inside Docker proxies to the host via `nginx.local.conf` (`host.docker.internal`).

## Setup & Run

1.  **Initialize Database Config**:
    Ensure `scripts/init-db.sh` is executable:
    ```bash
    chmod +x scripts/init-db.sh
    ```

2.  **Build and Run**:
    Start everything (infra + backend + frontend) via the local dev manager:
    ```bash
    scripts/run-local-dev.sh dev
    ```

    > **Note**: The first build takes a while as it compiles Windmill from source (Rust + `deno_core`/V8 for JavaScript `input_transforms`).

    If you want a faster `python`-only Windmill build (no JS `input_transforms`), set:
    ```bash
    export WINDMILL_FEATURES="static_frontend python"
    scripts/run-local-dev.sh dev
    ```

3.  **Import Windmill assets (optional)**:
    Import scripts/flows/apps into Windmill:
    - scripts from `windmill/scripts/devgodzilla/` → `u/devgodzilla/*`
    - flows from `windmill/flows/devgodzilla/` → `f/devgodzilla/*`
    - apps from `windmill/apps/devgodzilla/`

    ```bash
    scripts/run-local-dev.sh import
    ```

    Windmill token/workspace are read from `windmill/apps/devgodzilla-react-app/.env.development` by default.

3.  **Access Services**:
    - **DevGodzilla API (via nginx)**: `http://localhost:8080/docs` (or `$DEVGODZILLA_NGINX_PORT`)
    - **Windmill UI (via nginx)**: `http://localhost:8080` (or `$DEVGODZILLA_NGINX_PORT`)
    - **Readiness**: `http://localhost:8080/health/ready`

## Validating a real onboarding workflow (GitHub repo → SpecKit files)

In Windmill UI (`http://localhost:8080`), run flow `f/devgodzilla/onboard_to_tasks` with:
- `git_url`: `https://github.com/octocat/Hello-World`
- `project_name`: any unique name
- `branch`: `master` (or `main`)
- `feature_request`: a short feature request (used to generate spec/plan/tasks)

On success, generated files appear under `projects/<project_id>/<repo>/specs/<spec_id>/`.

## Development

- Backend and frontend run locally; restart them with:
  - `scripts/run-local-dev.sh backend restart`
  - `scripts/run-local-dev.sh frontend restart`

## Environment Variables (Compose)

- `DEVGODZILLA_DB_URL`: Postgres URL for DevGodzilla (Compose sets to `postgresql://devgodzilla:changeme@db:5432/devgodzilla_db`)
- `DEVGODZILLA_WINDMILL_URL`: Windmill base URL for DevGodzilla-to-Windmill API calls (Compose sets to `http://windmill:8000`)
- `DEVGODZILLA_WINDMILL_WORKSPACE`: Windmill workspace (Compose defaults to `demo1`)
- `DEVGODZILLA_WINDMILL_ENV_FILE`: Optional path to an env file containing `DEVGODZILLA_WINDMILL_TOKEN`/`WINDMILL_TOKEN`/`VITE_TOKEN`
