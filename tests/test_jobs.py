import time

from deksdenflow.jobs import LocalQueue, RedisQueue


def test_job_queue_enqueue_and_list_with_fakeredis() -> None:
    queue = RedisQueue("fakeredis://")
    job = queue.enqueue("demo_job", {"value": 1})
    assert job.job_type == "demo_job"
    stats = queue.stats()
    assert stats["default"]["queued"] >= 1


def test_local_queue_claim_and_requeue() -> None:
    queue = LocalQueue()
    job = queue.enqueue("demo_job", {"value": 1})
    listed = queue.list()
    assert listed and listed[0].job_id == job.job_id

    claimed = queue.claim()
    assert claimed is not None
    assert claimed.status == "started"
    queue.requeue(claimed, delay_seconds=0.01)
    assert queue.list(status="queued")[0].job_id == job.job_id

    time.sleep(0.02)
    reclaimed = queue.claim()
    assert reclaimed and reclaimed.job_id == job.job_id
