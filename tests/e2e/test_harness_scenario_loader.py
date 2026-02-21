from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.harness.scenario_loader import (
    DEFAULT_ADAPTERS_DIR,
    DEFAULT_SCENARIOS_DIR,
    load_adapter,
    load_scenario,
    load_scenarios,
)


def test_load_seeded_scenarios(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HARNESS_GITHUB_REPOS", raising=False)
    scenarios = load_scenarios()
    ids = {scenario.scenario_id for scenario in scenarios}
    assert "live_onboarding_test_glm5_demo" in ids
    assert "live_onboarding_simple_admin_reporter" in ids
    assert "live_onboarding_demo_spring" in ids


def test_load_scenario_applies_repo_url_override(monkeypatch: pytest.MonkeyPatch) -> None:
    path = DEFAULT_SCENARIOS_DIR / "live_onboarding_test_glm5_demo.json"
    monkeypatch.setenv("HARNESS_REPO_URL_OVERRIDE", "https://github.com/ilyafedotov-ops/override.git")

    scenario = load_scenario(path)
    assert scenario.repo.url == "https://github.com/ilyafedotov-ops/override.git"


def test_load_adapter_seeded_files() -> None:
    path = DEFAULT_ADAPTERS_DIR / "demo_spring.adapter.json"
    adapter = load_adapter(path)
    assert adapter.adapter_id == "demo_spring"
    assert adapter.require_worktree_registration is True


def test_load_scenario_rejects_invalid_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad-scenario.json"
    bad.write_text(
        json.dumps(
            {
                "scenario_id": "bad",
                "repo": {
                    "owner": "ilyafedotov-ops",
                    "name": "x",
                    "default_branch": "main"
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_scenario(bad)


def test_load_scenarios_filters_by_repo_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HARNESS_GITHUB_REPOS", "SimpleAdminReporter")
    scenarios = load_scenarios()
    assert len(scenarios) == 1
    assert scenarios[0].repo.name == "SimpleAdminReporter"
