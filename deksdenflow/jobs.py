import json
import threading
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import timedelta
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class Job:
    job_id: str
    job_type: str
    payload: Dict[str, Any]
    status: str = "queued"
    queue: str = "default"
    created_at: float = field(default_factory=time.time)
    attempts: int = 0
    max_attempts: int = 3
    next_run_at: float = 0.0
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseQueue(Protocol):
    def enqueue(self, job_type: str, payload: Dict[str, Any], queue: Optional[str] = None) -> Job:
        ...

    def claim(self, queue: Optional[str] = None) -> Optional[Job]:
        ...

    def list(self, status: Optional[str] = None) -> List[Job]:
        ...

    def requeue(self, job: Job, delay_seconds: float) -> None:
        ...

    def stats(self) -> Dict[str, Any]:
        ...


class RedisQueue:
    """
    Redis-backed queue using RQ.
    """

    def __init__(self, redis_url: str) -> None:
        try:
            import redis  # type: ignore
            from rq import Queue  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Redis/RQ not installed; install redis rq or omit DEKSDENFLOW_REDIS_URL") from exc

        use_fake = redis_url.startswith("fakeredis://")
        if use_fake:
            try:
                import fakeredis  # type: ignore
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("fakeredis not installed; add fakeredis or use a real Redis URL") from exc
            self._redis = fakeredis.FakeRedis.from_url("redis://localhost")
        else:
            self._redis = redis.Redis.from_url(redis_url)

        self._queue_cls = Queue
        self._queues: Dict[str, Queue] = {}
        self._is_fakeredis = use_fake

    def _get_queue(self, name: str):
        if name not in self._queues:
            self._queues[name] = self._queue_cls(name, connection=self._redis)
        return self._queues[name]

    def enqueue(self, job_type: str, payload: Dict[str, Any], queue: Optional[str] = None) -> Job:
        job = Job(
            job_id=str(uuid.uuid4()),
            job_type=job_type,
            payload=payload,
            queue=queue or "default",
        )
        q = self._get_queue(job.queue)
        # Jobs will be processed by scripts/rq_worker.py
        job.payload["job_id"] = job.job_id
        q.enqueue("deksdenflow.worker_runtime.rq_job_handler", job.job_type, job.payload)
        return job

    def claim(self, queue: Optional[str] = None) -> Optional[Job]:
        return None

    def list(self, status: Optional[str] = None) -> List[Job]:
        jobs: List[Job] = []
        # Ensure at least the default queue is visible for stats/listing
        if not self._queues:
            self._get_queue("default")

        for q in self._queues.values():
            jobs.extend(self._collect_jobs_for_queue(q, status))
        return jobs

    def _collect_jobs_for_queue(self, q, status: Optional[str]) -> List[Job]:
        import rq.job  # type: ignore

        jobs: List[Job] = []

        def _build_job(rq_job: "rq.job.Job", state: str) -> Job:
            job_type = rq_job.args[0] if rq_job.args else rq_job.func_name
            payload = rq_job.args[1] if rq_job.args and len(rq_job.args) > 1 else rq_job.kwargs or {}
            created_at = rq_job.enqueued_at.timestamp() if rq_job.enqueued_at else time.time()
            started_at = rq_job.started_at.timestamp() if rq_job.started_at else None
            ended_at = getattr(rq_job, "ended_at", None)
            ended_at_ts = ended_at.timestamp() if ended_at else None
            return Job(
                job_id=rq_job.id,
                job_type=str(job_type),
                payload=payload if isinstance(payload, dict) else {"payload": payload},
                status=state,
                queue=q.name,
                created_at=created_at,
                started_at=started_at,
                ended_at=ended_at_ts,
                result=getattr(rq_job, "result", None) if state == "finished" else None,
                error=str(getattr(rq_job, "exc_info", None)) if state == "failed" else None,
                meta=getattr(rq_job, "meta", None),
            )

        include_all = status is None
        if include_all or status == "queued":
            for rq_job in q.get_jobs():
                jobs.append(_build_job(rq_job, "queued"))
        if include_all or status == "started":
            for job_id in q.started_job_registry.get_job_ids():
                rq_job = q.fetch_job(job_id)
                if rq_job:
                    jobs.append(_build_job(rq_job, "started"))
        if include_all or status == "finished":
            for job_id in q.finished_job_registry.get_job_ids():
                rq_job = q.fetch_job(job_id)
                if rq_job:
                    jobs.append(_build_job(rq_job, "finished"))
        if include_all or status == "failed":
            for job_id in q.failed_job_registry.get_job_ids():
                rq_job = q.fetch_job(job_id)
                if rq_job:
                    jobs.append(_build_job(rq_job, "failed"))
        return jobs

    def requeue(self, job: Job, delay_seconds: float) -> None:
        q = self._get_queue(job.queue)
        q.enqueue_in(timedelta(seconds=delay_seconds), "deksdenflow.worker_runtime.rq_job_handler", job.job_type, job.payload)

    def stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {"backend": "redis-rq"}
        if not self._queues:
            self._get_queue("default")
        for name, q in self._queues.items():
            stats[name] = {
                "queued": q.count,
                "started": q.started_job_registry.count,
                "finished": q.finished_job_registry.count,
                "failed": q.failed_job_registry.count,
            }
        return stats

    @property
    def is_fakeredis(self) -> bool:
        return self._is_fakeredis

    def get_rq_queue(self, name: str = "default"):
        return self._get_queue(name)

    @property
    def redis_connection(self):
        return self._redis


class LocalQueue:
    """
    In-memory queue for local/dev use when Redis is unavailable.
    Not durable; single-process only.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def enqueue(self, job_type: str, payload: Dict[str, Any], queue: Optional[str] = None) -> Job:
        job = Job(
            job_id=str(uuid.uuid4()),
            job_type=job_type,
            payload=payload,
            queue=queue or "default",
            status="queued",
            next_run_at=time.time(),
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def claim(self, queue: Optional[str] = None) -> Optional[Job]:
        now = time.time()
        with self._lock:
            candidates = [
                job
                for job in self._jobs.values()
                if job.status == "queued" and job.next_run_at <= now and (queue is None or job.queue == queue)
            ]
            if not candidates:
                return None
            job = sorted(candidates, key=lambda j: j.next_run_at)[0]
            job.status = "started"
            job.started_at = time.time()
            return job

    def list(self, status: Optional[str] = None) -> List[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
        if status:
            jobs = [job for job in jobs if job.status == status]
        return sorted(jobs, key=lambda j: j.created_at)

    def requeue(self, job: Job, delay_seconds: float) -> None:
        with self._lock:
            job.status = "queued"
            job.next_run_at = time.time() + delay_seconds

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            counts: Dict[str, int] = {"queued": 0, "started": 0, "finished": 0, "failed": 0}
            for job in self._jobs.values():
                counts[job.status] = counts.get(job.status, 0) + 1
        return {"backend": "local", "default": counts}


def create_queue(redis_url: Optional[str], allow_inmemory: bool = False) -> BaseQueue:
    if not redis_url:
        if allow_inmemory:
            return LocalQueue()
        raise RuntimeError("Redis queue required (set DEKSDENFLOW_REDIS_URL) or enable in-memory fallback")
    return RedisQueue(redis_url)
