#!/usr/bin/env python3
"""
Run an RQ worker to process DeksdenFlow jobs from Redis.

Environment:
  - DEKSDENFLOW_REDIS_URL (required)
  - DEKSDENFLOW_DB_PATH (for Database)
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rq import Connection, Queue, Worker  # type: ignore
import redis  # type: ignore

from deksdenflow.config import load_config  # noqa: E402
from deksdenflow.logging import setup_logging, json_logging_from_env, log_extra  # noqa: E402


def main() -> None:
    logger = setup_logging(os.environ.get("DEKSDENFLOW_LOG_LEVEL", "INFO"), json_output=json_logging_from_env())
    config = load_config()
    if not config.redis_url:
        logger.error("DEKSDENFLOW_REDIS_URL is required for RQ worker.")
        sys.exit(1)
    redis_conn = redis.from_url(config.redis_url)
    queues = [Queue("default", connection=redis_conn)]
    with Connection(redis_conn):
        worker = Worker(queues)
        logger.info("[rq-worker] Listening", extra={"redis": config.redis_url, "queues": [q.name for q in queues]})
        try:
            worker.work()
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("[rq-worker] fatal error", extra=log_extra(error=str(exc), error_type=exc.__class__.__name__))
            sys.exit(1)


if __name__ == "__main__":
    main()
