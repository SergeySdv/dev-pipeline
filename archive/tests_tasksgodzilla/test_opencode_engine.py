import os

import httpx
import pytest

from tasksgodzilla.engines import EngineRequest, registry
from tasksgodzilla.errors import ConfigError
import tasksgodzilla.engines_opencode  # noqa: F401


class _DummyResponse:
    def __init__(self, status_code: int = 200, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.invalid")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self):
        return self._payload


def test_opencode_engine_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("TASKSGODZILLA_OPENCODE_API_KEY", raising=False)
    engine = registry.get("opencode")
    req = EngineRequest(
        project_id=0,
        protocol_run_id=0,
        step_run_id=0,
        model="zai/glm-4.6",
        prompt_files=[],
        working_dir=".",
        extra={"prompt_text": "hello"},
    )
    # Without an API key, the engine falls back to OpenCode CLI; if it's not available,
    # we expect a ConfigError.
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(ConfigError):
        engine.execute(req)


def test_opencode_engine_posts_openai_compatible_payload(monkeypatch) -> None:
    monkeypatch.setenv("TASKSGODZILLA_OPENCODE_API_KEY", "k-test")
    monkeypatch.setenv("TASKSGODZILLA_OPENCODE_BASE_URL", "https://opencode.ai/zen/v1")

    captured = {}

    class _DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return _DummyResponse(
                200,
                payload={
                    "choices": [{"message": {"content": "OK"}}],
                    "usage": {"total_tokens": 123},
                },
            )

    monkeypatch.setattr(httpx, "Client", _DummyClient)

    engine = registry.get("opencode")
    req = EngineRequest(
        project_id=1,
        protocol_run_id=2,
        step_run_id=3,
        model="zai/glm-4.6",
        prompt_files=[],
        working_dir=".",
        extra={"prompt_text": "hi", "temperature": 0.0},
    )
    result = engine.execute(req)

    assert result.stdout.strip() == "OK"
    assert result.tokens_used == 123
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer k-test"
    # The engine normalizes the common alias `zai/*` to an OpenCode-known provider.
    assert captured["json"]["model"] == "zai-coding-plan/glm-4.6"
    assert captured["json"]["messages"][0]["role"] == "user"
    assert captured["json"]["messages"][0]["content"] == "hi"


def test_opencode_engine_cli_fallback(monkeypatch) -> None:
    monkeypatch.delenv("TASKSGODZILLA_OPENCODE_API_KEY", raising=False)
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/opencode")

    class _Proc:
        def __init__(self):
            self.returncode = 0
            self.stdout = "PONG\n"
            self.stderr = ""

    def fake_run(cmd, cwd=None, capture_output=None, text=None, check=None, timeout=None):
        assert cmd[:2] == ["opencode", "run"]
        assert "--model" in cmd
        assert "--file" in cmd
        return _Proc()

    monkeypatch.setattr("subprocess.run", fake_run)

    engine = registry.get("opencode")
    req = EngineRequest(
        project_id=0,
        protocol_run_id=0,
        step_run_id=0,
        model="zai/glm-4.6",
        prompt_files=[],
        working_dir=".",
        extra={"prompt_text": "Reply with exactly: PONG"},
    )
    res = engine.execute(req)
    assert res.stdout.strip() == "PONG"

