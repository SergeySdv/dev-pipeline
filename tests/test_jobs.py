from deksdenflow.jobs import InMemoryQueue


def test_job_queue_enqueue_and_claim() -> None:
    queue = InMemoryQueue()
    job = queue.enqueue("demo_job", {"value": 1})
    assert job.job_type == "demo_job"
    claimed = queue.claim()
    assert claimed is not None
    assert claimed.job_id == job.job_id
