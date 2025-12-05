import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    db_path: Path
    environment: str = "local"
    api_token: Optional[str] = None
    redis_url: Optional[str] = None
    log_level: str = "INFO"
    webhook_token: Optional[str] = None


def load_config() -> Config:
    """
    Load orchestrator configuration from environment.
    """
    db_path = Path(os.environ.get("DEKSDENFLOW_DB_PATH", ".deksdenflow.sqlite")).expanduser()
    environment = os.environ.get("DEKSDENFLOW_ENV", "local")
    api_token = os.environ.get("DEKSDENFLOW_API_TOKEN")
    redis_url = os.environ.get("DEKSDENFLOW_REDIS_URL")
    log_level = os.environ.get("DEKSDENFLOW_LOG_LEVEL", "INFO")
    webhook_token = os.environ.get("DEKSDENFLOW_WEBHOOK_TOKEN")
    return Config(
        db_path=db_path,
        environment=environment,
        api_token=api_token,
        redis_url=redis_url,
        log_level=log_level,
        webhook_token=webhook_token,
    )
