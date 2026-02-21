#!/usr/bin/env python3
"""
Run an RQ worker to process Redis jobs.

Environment:
  - DEVGODZILLA_REDIS_URL
  - DEVGODZILLA_RQ_QUEUES (comma-separated queue names, default: "default")
"""

import os
import sys
from pathlib import Path
import logging

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rq import Queue, Worker  # type: ignore
import redis  # type: ignore


def _env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name) or default


def main() -> None:
    log_level = (_env("DEVGODZILLA_LOG_LEVEL", "INFO") or "INFO").upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
    logger = logging.getLogger("devgodzilla.rq_worker")

    redis_url = _env("DEVGODZILLA_REDIS_URL")
    if not redis_url:
        logger.error("Missing DEVGODZILLA_REDIS_URL.")
        sys.exit(1)

    queues_env = _env("DEVGODZILLA_RQ_QUEUES", "default") or "default"
    queue_names = [q.strip() for q in queues_env.split(",") if q.strip()]

    redis_conn = redis.from_url(redis_url)
    queues = [Queue(name, connection=redis_conn) for name in queue_names]
    worker = Worker(queues, connection=redis_conn)
    logger.info("[rq-worker] Listening redis=%s queues=%s", redis_url, ",".join(q.name for q in queues))
    try:
        worker.work()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[rq-worker] fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
