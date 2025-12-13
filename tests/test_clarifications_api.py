import tempfile
from pathlib import Path

import pytest
import os
import subprocess

try:
    from fastapi.testclient import TestClient  # type: ignore
    from tasksgodzilla.api.app import app
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore
    app = None  # type: ignore


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True)
    (path / "README.md").write_text("demo", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "tester",
            "GIT_AUTHOR_EMAIL": "tester@example.com",
            "GIT_COMMITTER_NAME": "tester",
            "GIT_COMMITTER_EMAIL": "tester@example.com",
        },
    )


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_project_clarifications_are_persisted_and_answerable(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "clarifications.sqlite"
        repo = Path(tmpdir) / "repo"
        _init_repo(repo)
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)
        monkeypatch.setenv("TASKSGODZILLA_AUTO_CLONE", "false")

        with TestClient(app) as client:  # type: ignore[arg-type]
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": str(repo),
                    "base_branch": "main",
                    "project_classification": "enterprise-compliance",
                },
            ).json()
            project_id = proj["id"]

            # Run onboarding inline to materialize policy clarifications.
            resp = client.post(f"/projects/{project_id}/onboarding/actions/start", json={"inline": True}).json()
            assert "message" in resp

            items = client.get(f"/projects/{project_id}/clarifications?status=open").json()
            assert isinstance(items, list)
            assert any(c["key"] == "data_classification" for c in items)

            answered = client.post(
                f"/projects/{project_id}/clarifications/data_classification",
                json={"answer": {"value": "internal"}, "answered_by": "tester"},
            ).json()
            assert answered["key"] == "data_classification"
            assert answered["status"] == "answered"
            assert answered["answered_by"] == "tester"

            items_after = client.get(f"/projects/{project_id}/clarifications?status=open").json()
            assert not any(c["key"] == "data_classification" for c in items_after)
