from __future__ import annotations

from types import SimpleNamespace

from devgodzilla.windmill.client import JobStatus, WindmillClient, WindmillConfig


def _client() -> WindmillClient:
    return WindmillClient(
        WindmillConfig(
            base_url="http://localhost:8001",
            token="test-token",
            workspace="demo1",
            max_retries=0,
        )
    )


def test_get_job_maps_started_queue_job_to_running(monkeypatch) -> None:
    client = _client()

    payload = {
        "type": "QueueJob",
        "success": None,
        "created_at": "2026-02-22T07:00:00Z",
        "started_at": "2026-02-22T07:00:01Z",
        "completed_at": None,
        "result": None,
        "error": None,
        "err": None,
        "canceled": False,
    }

    monkeypatch.setattr(client, "_request", lambda *args, **kwargs: SimpleNamespace(json=lambda: payload))

    job = client.get_job("job-123")

    assert job.status == JobStatus.RUNNING
    assert job.started_at == payload["started_at"]


def test_get_job_maps_canceled_flag_to_canceled(monkeypatch) -> None:
    client = _client()

    payload = {
        "type": "QueueJob",
        "success": None,
        "created_at": "2026-02-22T07:00:00Z",
        "started_at": "2026-02-22T07:00:01Z",
        "completed_at": None,
        "result": None,
        "error": None,
        "err": None,
        "canceled": True,
    }

    monkeypatch.setattr(client, "_request", lambda *args, **kwargs: SimpleNamespace(json=lambda: payload))

    job = client.get_job("job-456")

    assert job.status == JobStatus.CANCELED
