# RQ Worker Setup (Durable Queue)

1. Set `DEKSDENFLOW_REDIS_URL` (e.g., `redis://localhost:6379/0`).
2. Run API server (it will not start an in-process worker when Redis is set):
   ```bash
   .venv/bin/python scripts/api_server.py
   ```
3. Start an RQ worker in a separate process:
   ```bash
   .venv/bin/python scripts/rq_worker.py
   ```
4. Jobs enqueued via API actions/webhooks will be processed by the RQ worker using `deksdenflow.worker_runtime.rq_job_handler`.

Env used by RQ worker:
- `DEKSDENFLOW_DB_PATH`
- `DEKSDENFLOW_REDIS_URL`
- `DEKSDENFLOW_LOG_LEVEL`

Note: Queue listing/claim APIs are not exposed yet; monitor Redis/RQ via `rq info` or the RQ dashboard.
