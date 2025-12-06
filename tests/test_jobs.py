import pytest

from deksdenflow.jobs import RedisQueue, create_queue


def test_job_queue_enqueue_and_list_with_fakeredis() -> None:
    queue = RedisQueue("fakeredis://")
    job = queue.enqueue("demo_job", {"value": 1})
    assert job.job_type == "demo_job"
    stats = queue.stats()
    assert stats["default"]["queued"] >= 1


def test_create_queue_without_redis_errors() -> None:
    with pytest.raises(RuntimeError):
        create_queue(None)
