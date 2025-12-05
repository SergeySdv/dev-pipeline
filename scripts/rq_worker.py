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


def main() -> None:
    config = load_config()
    if not config.redis_url:
        print("DEKSDENFLOW_REDIS_URL is required for RQ worker.", file=sys.stderr)
        sys.exit(1)
    redis_conn = redis.from_url(config.redis_url)
    queues = [Queue("default", connection=redis_conn)]
    with Connection(redis_conn):
        worker = Worker(queues)
        print(f"[rq-worker] Listening on Redis {config.redis_url} queues {[q.name for q in queues]}")
        worker.work()


if __name__ == "__main__":
    main()
