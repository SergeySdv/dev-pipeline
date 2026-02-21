#!/usr/bin/env python3
"""
Run the DevGodzilla API (FastAPI).

Install dependencies first:
  pip install fastapi uvicorn
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn  # noqa: E402
from devgodzilla.logging import setup_logging, json_logging_from_env, log_extra  # noqa: E402


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


def main() -> None:
    log_level = _env("DEVGODZILLA_LOG_LEVEL", "INFO")
    logger = setup_logging(log_level, json_output=json_logging_from_env())
    host = _env("DEVGODZILLA_API_HOST", "0.0.0.0")
    port = int(_env("DEVGODZILLA_API_PORT", "8000"))
    try:
        # Allow our central logging config to drive output (structured/JSON) instead of uvicorn defaults.
        uvicorn.run("devgodzilla.api.app:app", host=host, port=port, reload=False, log_config=None)
    except Exception as exc:  # pragma: no cover - best effort
        logger.error("API server failed", extra=log_extra(error=str(exc), error_type=exc.__class__.__name__))
        sys.exit(1)


if __name__ == "__main__":
    main()
