from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    TestClient = None  # type: ignore

from devgodzilla.api.app import app
from devgodzilla.api.dependencies import get_db
from devgodzilla.config import _reset_config_for_tests
from devgodzilla.db.database import SQLiteDatabase


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_project_create_and_update_mask_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db = SQLiteDatabase(Path(tmpdir) / "test.db")
        db.init_schema()
        monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
        monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
        app.dependency_overrides[get_db] = lambda: db

        try:
            with TestClient(app) as client:  # type: ignore[arg-type]
                create_resp = client.post(
                    "/projects",
                    json={
                        "name": "private-repo",
                        "git_url": "https://github.com/example/private.git",
                        "base_branch": "main",
                        "github_token": "ghp_create_secret",
                        "auto_onboard": False,
                        "auto_discovery": False,
                    },
                )
                assert create_resp.status_code == 200
                create_payload = create_resp.json()
                assert create_payload["github_token_configured"] is True
                assert create_payload["task_cycle_autonomous"] is False
                assert "github_token" not in create_payload

                project = db.get_project(create_payload["id"])
                assert project.secrets == {"github_token": "ghp_create_secret"}

                update_resp = client.put(
                    f"/projects/{project.id}",
                    json={"github_token": "ghp_updated_secret", "task_cycle_autonomous": True},
                )
                assert update_resp.status_code == 200
                update_payload = update_resp.json()
                assert update_payload["github_token_configured"] is True
                assert update_payload["task_cycle_autonomous"] is True
                assert "github_token" not in update_payload

                project = db.get_project(project.id)
                assert project.secrets == {"github_token": "ghp_updated_secret"}

                clear_resp = client.put(
                    f"/projects/{project.id}",
                    json={"github_token": None},
                )
                assert clear_resp.status_code == 200
                clear_payload = clear_resp.json()
                assert clear_payload["github_token_configured"] is False
                assert "github_token" not in clear_payload

                project = db.get_project(project.id)
                assert project.secrets is None
        finally:
            app.dependency_overrides.clear()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_project_create_external_repo_exposes_effective_storage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db = SQLiteDatabase(tmp_path / "test.db")
    db.init_schema()
    repo_root = tmp_path / "repos" / "telegram-bot"
    (repo_root / ".git").mkdir(parents=True)
    monkeypatch.setenv("DEVGODZILLA_WORKTREES_ROOT", str(tmp_path / "worktrees-root"))
    monkeypatch.setenv("DEVGODZILLA_ARTIFACTS_ROOT", str(tmp_path / "artifacts-root"))
    _reset_config_for_tests()
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:  # type: ignore[arg-type]
            response = client.post(
                "/projects",
                json={
                    "name": "telegram-bot",
                    "repo_mode": "external_repo",
                    "local_path": str(repo_root),
                    "base_branch": "main",
                    "auto_onboard": False,
                    "auto_discovery": False,
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["repo_mode"] == "external_repo"
        assert payload["local_path"] == str(repo_root)
        assert payload["effective_repo_path"] == str(repo_root)
        assert payload["effective_worktrees_root"] == str(tmp_path / "worktrees-root" / str(payload["id"]) / "telegram-bot")
        assert payload["effective_artifacts_root"] == str(tmp_path / "artifacts-root" / str(payload["id"]) / "telegram-bot")
    finally:
        app.dependency_overrides.clear()
        _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_project_create_managed_clone_exposes_derived_storage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db = SQLiteDatabase(tmp_path / "test.db")
    db.init_schema()
    monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(tmp_path / "managed-repos"))
    monkeypatch.setenv("DEVGODZILLA_WORKTREES_ROOT", str(tmp_path / "managed-worktrees"))
    monkeypatch.setenv("DEVGODZILLA_ARTIFACTS_ROOT", str(tmp_path / "managed-artifacts"))
    _reset_config_for_tests()
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:  # type: ignore[arg-type]
            response = client.post(
                "/projects",
                json={
                    "name": "telegram-bot",
                    "git_url": "https://github.com/example/telegram-bot.git",
                    "repo_mode": "managed_clone",
                    "base_branch": "main",
                    "auto_onboard": False,
                    "auto_discovery": False,
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["repo_mode"] == "managed_clone"
        assert payload["local_path"] is None
        assert payload["effective_repo_path"] == str(tmp_path / "managed-repos" / str(payload["id"]) / "telegram-bot")
        assert payload["effective_worktrees_root"] == str(tmp_path / "managed-worktrees" / str(payload["id"]) / "telegram-bot")
        assert payload["effective_artifacts_root"] == str(tmp_path / "managed-artifacts" / str(payload["id"]) / "telegram-bot")
    finally:
        app.dependency_overrides.clear()
        _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_project_create_returns_created_project_when_onboarding_enqueue_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db = SQLiteDatabase(tmp_path / "test.db")
    db.init_schema()
    monkeypatch.setenv("DEVGODZILLA_WINDMILL_URL", "http://windmill.local")
    monkeypatch.setenv("DEVGODZILLA_WINDMILL_TOKEN", "test-token")
    _reset_config_for_tests()
    app.dependency_overrides[get_db] = lambda: db

    def fail_enqueue(*args, **kwargs):
        raise RuntimeError("401 Unauthorized")

    monkeypatch.setattr(
        "devgodzilla.services.onboarding_queue.enqueue_project_onboarding",
        fail_enqueue,
    )

    try:
        with TestClient(app) as client:  # type: ignore[arg-type]
            response = client.post(
                "/projects",
                json={
                    "name": "telegram-bot",
                    "git_url": "https://github.com/example/telegram-bot.git",
                    "repo_mode": "managed_clone",
                    "base_branch": "main",
                    "auto_onboard": True,
                    "auto_discovery": True,
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "telegram-bot"
        assert payload["onboarding_queued"] is False
        assert payload["onboarding_error"] == "401 Unauthorized"

        created = db.get_project(payload["id"])
        assert created.name == "telegram-bot"

        onboarding = client.get(f"/projects/{created.id}/onboarding")
        assert onboarding.status_code == 200
        summary = onboarding.json()
        failure_events = [event for event in summary["events"] if event["event_type"] == "onboarding_enqueue_failed"]
        assert len(failure_events) == 1
        assert failure_events[0]["metadata"] == {"error": "401 Unauthorized"}
    finally:
        app.dependency_overrides.clear()
        _reset_config_for_tests()


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_onboarding_uses_project_github_token_for_clone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db = SQLiteDatabase(tmp_path / "test.db")
    db.init_schema()
    project = db.create_project(
        name="private-repo",
        git_url="https://github.com/example/private.git",
        base_branch="main",
        secrets={"github_token": "ghp_onboard_secret"},
    )
    monkeypatch.delenv("DEVGODZILLA_DB_URL", raising=False)
    monkeypatch.delenv("DEVGODZILLA_API_TOKEN", raising=False)
    app.dependency_overrides[get_db] = lambda: db

    captured: dict[str, str | None] = {"github_token": None}

    def fake_resolve_repo_path(self, git_url, project_name, local_path, **kwargs):
        captured["github_token"] = kwargs.get("github_token")
        repo_root = tmp_path / "repo"
        repo_root.mkdir(exist_ok=True)
        return repo_root

    def fake_init_project(self, repo_root, constitution_content=None, project_id=None):
        return SimpleNamespace(
            success=True,
            spec_path=str(Path(repo_root) / ".specify"),
            constitution_hash="abc123",
            warnings=[],
            error=None,
        )

    monkeypatch.setattr("devgodzilla.services.git.GitService.resolve_repo_path", fake_resolve_repo_path)
    monkeypatch.setattr("devgodzilla.services.specification.SpecificationService.init_project", fake_init_project)

    try:
        with TestClient(app) as client:  # type: ignore[arg-type]
            resp = client.post(
                f"/projects/{project.id}/actions/onboard",
                json={"clone_if_missing": True, "run_discovery_agent": False},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["success"] is True
            assert captured["github_token"] == "ghp_onboard_secret"
    finally:
        app.dependency_overrides.clear()
