import tempfile
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
    from tasksgodzilla.api.app import app
except ImportError:  # pragma: no cover - fastapi not installed in minimal envs
    TestClient = None  # type: ignore
    app = None  # type: ignore


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_auth_rejects_missing_token_when_enabled(
    redis_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api-auth.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("TASKSGODZILLA_API_TOKEN", "secret-token")

        with TestClient(app) as client:  # type: ignore[arg-type]
            resp = client.get("/projects")
            assert resp.status_code == 401

            resp = client.get("/projects", headers={"Authorization": "Bearer secret-token"})
            assert resp.status_code in (200, 204, 404)  # list may be empty, but auth should pass


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_auth_requires_session_when_oidc_enabled(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api-oidc-auth.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("TASKSGODZILLA_OIDC_ISSUER", "https://issuer.example.com")
        monkeypatch.setenv("TASKSGODZILLA_OIDC_CLIENT_ID", "client-id")
        monkeypatch.setenv("TASKSGODZILLA_OIDC_CLIENT_SECRET", "client-secret")
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            resp = client.get("/projects")
            assert resp.status_code == 401


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_auth_allows_token_session_login_when_token_enabled(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api-token-session.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.setenv("TASKSGODZILLA_API_TOKEN", "secret-token")
        monkeypatch.delenv("TASKSGODZILLA_OIDC_ISSUER", raising=False)
        monkeypatch.delenv("TASKSGODZILLA_OIDC_CLIENT_ID", raising=False)
        monkeypatch.delenv("TASKSGODZILLA_OIDC_CLIENT_SECRET", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            # Initially unauthorized.
            resp = client.get("/projects")
            assert resp.status_code == 401

            status = client.get("/auth/status").json()
            assert status["oidc_enabled"] is False
            assert status["token_required"] is True
            assert status["token_authenticated"] is False

            # Wrong token rejected.
            resp = client.post("/auth/token", json={"token": "wrong"})
            assert resp.status_code == 401

            # Correct token sets session.
            resp = client.post("/auth/token", json={"token": "secret-token"})
            assert resp.status_code == 200
            assert resp.json().get("ok") is True

            status = client.get("/auth/status").json()
            assert status["token_authenticated"] is True

            # Now should pass auth without Authorization header (cookie session).
            resp = client.get("/projects")
            assert resp.status_code in (200, 204, 404)
