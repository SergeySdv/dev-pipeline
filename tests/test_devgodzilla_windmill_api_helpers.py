from __future__ import annotations

import sys
import types

from windmill.scripts.devgodzilla import _api
from windmill.scripts.devgodzilla import sprint_from_protocol_api


def test_get_devgodzilla_api_base_url_prefers_windmill_variable(monkeypatch) -> None:
    monkeypatch.setenv("DEVGODZILLA_API_URL", "http://devgodzilla-api:8000")
    fake_wmill = types.SimpleNamespace(get_variable=lambda _name: "http://host.docker.internal:8000")
    monkeypatch.setitem(sys.modules, "wmill", fake_wmill)

    assert _api.get_devgodzilla_api_base_url() == "http://host.docker.internal:8000"


def test_get_devgodzilla_api_base_url_falls_back_to_env(monkeypatch) -> None:
    monkeypatch.delenv("DEVGODZILLA_API_URL", raising=False)
    monkeypatch.delitem(sys.modules, "wmill", raising=False)
    monkeypatch.setenv("DEVGODZILLA_API_URL", "http://devgodzilla-api:8000")

    assert _api.get_devgodzilla_api_base_url() == "http://devgodzilla-api:8000"


def test_sprint_from_protocol_api_uses_shared_api_helper(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_api_json(method: str, path: str, *, body=None, timeout_seconds: int = 30):
        captured["method"] = method
        captured["path"] = path
        captured["body"] = body
        captured["timeout_seconds"] = timeout_seconds
        return {"id": 7, "name": "Sprint 7"}

    monkeypatch.setattr(sprint_from_protocol_api, "api_json", fake_api_json)

    result = sprint_from_protocol_api.main(
        12,
        sprint_name="Sprint 7",
        auto_sync=False,
        start_date="2026-03-09",
        end_date="2026-03-23",
    )

    assert result == {"id": 7, "name": "Sprint 7"}
    assert captured == {
        "method": "POST",
        "path": "/protocols/12/actions/create-sprint",
        "body": {
            "sprint_name": "Sprint 7",
            "auto_sync": False,
            "start_date": "2026-03-09",
            "end_date": "2026-03-23",
        },
        "timeout_seconds": 30,
    }
