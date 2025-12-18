from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from devgodzilla.api import schemas
from devgodzilla.api.routes import projects, protocols, steps, agents, clarifications, speckit
from devgodzilla.api.routes import metrics, webhooks, events
from devgodzilla.api.routes import windmill as windmill_routes
from devgodzilla.api.routes import runs as runs_routes
from devgodzilla.api.routes import project_speckit as project_speckit_routes
from devgodzilla.api.dependencies import get_db, get_service_context, require_api_token, require_webhook_token
from devgodzilla.config import get_config
from devgodzilla.engines.bootstrap import bootstrap_default_engines
from devgodzilla.db.database import Database
from devgodzilla.logging import get_logger
from devgodzilla.windmill.client import WindmillClient, WindmillConfig

logger = get_logger(__name__)

app = FastAPI(
    title="DevGodzilla API",
    description="REST API for DevGodzilla AI Development Pipeline",
    version="0.1.0",
)

# CORS
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_allow_origins or [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
auth_deps = [Depends(require_api_token)]
app.include_router(projects.router, tags=["Projects"], dependencies=auth_deps)
app.include_router(protocols.router, tags=["Protocols"], dependencies=auth_deps)
app.include_router(steps.router, tags=["Steps"], dependencies=auth_deps)
app.include_router(agents.router, tags=["Agents"], dependencies=auth_deps)
app.include_router(clarifications.router, tags=["Clarifications"], dependencies=auth_deps)
app.include_router(speckit.router, tags=["SpecKit"], dependencies=auth_deps)
app.include_router(metrics.router)  # /metrics (optionally unauthenticated)
app.include_router(webhooks.router, dependencies=[Depends(require_webhook_token)])  # /webhooks/*
app.include_router(events.router, dependencies=auth_deps)  # /events
app.include_router(windmill_routes.router, dependencies=auth_deps)  # /flows, /jobs (Windmill)
app.include_router(runs_routes.router, dependencies=auth_deps)  # /runs (Job runs)
app.include_router(project_speckit_routes.router, dependencies=auth_deps)  # /projects/{id}/speckit/*


@app.on_event("startup")
def bootstrap_engines() -> None:
    """
    Register engines for API execution.

    The docker dev stack frequently runs without any real agent CLI installed.
    We always register a DummyEngine as the default so UI/flow integration can
    be tested end-to-end.
    """
    bootstrap_default_engines()


@app.on_event("startup")
def bootstrap_database() -> None:
    """
    Ensure DB schema exists.

    This is safe to run multiple times (CREATE TABLE IF NOT EXISTS).
    """
    from devgodzilla.cli.main import get_db as cli_get_db

    db = cli_get_db()
    db.init_schema()
    try:
        from devgodzilla.services.event_persistence import install_db_event_sink

        install_db_event_sink(db_provider=cli_get_db)
    except Exception:
        pass


@app.get("/health", response_model=schemas.Health)
def health_check():
    """Health check endpoint."""
    return schemas.Health()


@app.get("/health/live")
def health_live():
    """Liveness probe (process is running)."""
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(
    db: Database = Depends(get_db),
    ctx=Depends(get_service_context),
):
    """Readiness probe (dependencies reachable)."""
    components: dict[str, str] = {"database": "ok", "windmill": "skipped"}
    try:
        db.list_projects()
    except Exception:
        components["database"] = "error"

    try:
        config = ctx.config
        if getattr(config, "windmill_enabled", False):
            wm = WindmillClient(
                WindmillConfig(
                    base_url=config.windmill_url or "http://localhost:8000",
                    token=config.windmill_token or "",
                    workspace=getattr(config, "windmill_workspace", "devgodzilla"),
                )
            )
            components["windmill"] = "ok" if wm.health_check() else "error"
        else:
            components["windmill"] = "disabled"
    except Exception:
        components["windmill"] = "error"

    status = "ok" if all(v in ("ok", "disabled", "skipped") for v in components.values()) else "error"
    return {"status": status, "components": components, "version": app.version}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
