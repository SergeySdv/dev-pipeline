#!/usr/bin/env python3
"""
Minimal in-process worker loop for the placeholder JobQueue.

This is a stub: in a real deployment, replace with Redis/RQ/Celery/etc. and
hook into Codex/Git/CI workers. For now it simply drains the queue and prints.
"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from deksdenflow.config import load_config  # noqa: E402
from deksdenflow.storage import Database  # noqa: E402
from deksdenflow.jobs import create_queue  # noqa: E402
from deksdenflow.worker_runtime import drain_once  # noqa: E402


def main(poll_interval: float = 1.0) -> None:
    config = load_config()
    db = Database(config.db_path)
    db.init_schema()
    queue = create_queue(config.redis_url)

    print(f"[worker] Starting loop against DB {config.db_path} (in-memory queue)")
    try:
        while True:
            job = drain_once(queue, db)
            if job:
                print(f"[worker] Processed job {job.job_type} {job.job_id} payload={job.payload}")
            else:
                time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("[worker] Stopping.")


if __name__ == "__main__":
    main(float(os.environ.get("DEKSDENFLOW_WORKER_POLL", "1.0")))
