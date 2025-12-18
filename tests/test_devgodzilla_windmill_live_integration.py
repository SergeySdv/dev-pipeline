import os

import httpx
import pytest

from devgodzilla.config import load_config
from devgodzilla.windmill.client import JobStatus, WindmillClient, WindmillConfig


pytestmark = pytest.mark.integration


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def test_live_windmill_stack_end_to_end() -> None:
    """
    Opt-in integration test that hits a *real* running Windmill + DevGodzilla stack.

    Enable with:
      - DEVGODZILLA_RUN_LIVE_WINDMILL_TESTS=1

    Assumptions (typical Docker Compose setup):
      - nginx is reachable at http://localhost:8080
      - Windmill assets have been imported (windmill_import)
      - Windmill has a worker running (jobs can execute)
    """
    if not _flag("DEVGODZILLA_RUN_LIVE_WINDMILL_TESTS"):
        pytest.skip("set DEVGODZILLA_RUN_LIVE_WINDMILL_TESTS=1 to enable live integration test")

    public_base_url = os.environ.get("DEVGODZILLA_LIVE_BASE_URL", "http://localhost:8080").rstrip("/")
    config = load_config()

    assert config.windmill_url, "DEVGODZILLA_WINDMILL_URL must be set (or provided via DEVGODZILLA_WINDMILL_ENV_FILE)"
    assert config.windmill_token, "DEVGODZILLA_WINDMILL_TOKEN must be set (or provided via DEVGODZILLA_WINDMILL_ENV_FILE)"
    assert config.windmill_workspace, "DEVGODZILLA_WINDMILL_WORKSPACE must be set"

    # Stack health via nginx -> DevGodzilla API.
    ready = httpx.get(f"{public_base_url}/health/ready", timeout=10)
    assert ready.status_code == 200, f"stack not ready at {public_base_url}/health/ready: {ready.text}"

    # DevGodzilla -> Windmill integration (API proxies).
    flows = httpx.get(f"{public_base_url}/flows", timeout=20)
    assert flows.status_code == 200, f"/flows failed: {flows.text}"
    assert isinstance(flows.json(), list)

    jobs = httpx.get(f"{public_base_url}/jobs", timeout=20)
    assert jobs.status_code == 200, f"/jobs failed: {jobs.text}"
    assert isinstance(jobs.json(), list)

    # Windmill -> DevGodzilla integration (run an imported script that calls /projects).
    client = WindmillClient(
        WindmillConfig(
            base_url=config.windmill_url,
            token=config.windmill_token,
            workspace=config.windmill_workspace,
            timeout=30,
        )
    )
    try:
        job_id = client.run_script("u/devgodzilla/list_projects", {})
        job = client.wait_for_job(job_id, timeout=120, poll_interval=1.0)
        if job.status != JobStatus.COMPLETED:
            logs = client.get_job_logs(job_id)
            raise AssertionError(f"windmill job did not complete (status={job.status}). logs:\n{logs}")
        assert isinstance(job.result, dict)
        assert "projects" in job.result
    finally:
        client.close()

