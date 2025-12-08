from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tasksgodzilla.jobs import BaseQueue, Job, RedisQueue


@dataclass
class QueueService:
    """High-level queue facade that wraps `BaseQueue`.

    This provides semantic enqueue helpers around the job types currently used
    by `tasksgodzilla.worker_runtime.process_job`.
    """

    queue: BaseQueue

    @classmethod
    def from_redis_url(cls, redis_url: str) -> "QueueService":
        """Construct a QueueService backed by a Redis/RQ queue."""
        return cls(queue=RedisQueue(redis_url))

    def enqueue_plan_protocol(self, protocol_run_id: int) -> Job:
        return self.queue.enqueue("plan_protocol_job", {"protocol_run_id": protocol_run_id})

    def enqueue_execute_step(self, step_run_id: int) -> Job:
        return self.queue.enqueue("execute_step_job", {"step_run_id": step_run_id})

    def enqueue_run_quality(self, step_run_id: int) -> Job:
        return self.queue.enqueue("run_quality_job", {"step_run_id": step_run_id})

    def enqueue_project_setup(self, project_id: int, protocol_run_id: Optional[int] = None) -> Job:
        payload = {"project_id": project_id}
        if protocol_run_id is not None:
            payload["protocol_run_id"] = protocol_run_id
        return self.queue.enqueue("project_setup_job", payload)

    def enqueue_open_pr(self, protocol_run_id: int) -> Job:
        return self.queue.enqueue("open_pr_job", {"protocol_run_id": protocol_run_id})

