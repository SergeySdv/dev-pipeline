from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.e2e.harness.assertions import assert_paths_exist
from tests.e2e.harness.live_cli import build_live_cli_stage_handlers
from tests.e2e.harness.preflight import run_preflight
from tests.e2e.harness.runner import run_scenario
from tests.e2e.harness.scenario_loader import load_adapter, load_scenarios, resolve_adapter_path


@pytest.mark.integration
def test_workflow_harness_live() -> None:
    if os.environ.get("DEVGODZILLA_RUN_E2E_HARNESS") != "1":
        pytest.skip("Set DEVGODZILLA_RUN_E2E_HARNESS=1 to enable live harness E2E.")

    step_engine = (os.environ.get("HARNESS_STEP_ENGINE", "opencode").strip() or "opencode").lower()
    report = run_preflight(
        auto_start=True,
        require_opencode=(step_engine == "opencode"),
        require_windmill=True,
    )
    assert report.ok, f"Preflight failed: errors={report.errors} warnings={report.warnings} details={report.details}"

    scenarios = load_scenarios()
    scenario_filter = os.environ.get("HARNESS_SCENARIO")
    if scenario_filter:
        scenarios = [scenario for scenario in scenarios if scenario.scenario_id == scenario_filter]

    assert scenarios, "No harness scenarios loaded"

    stage_handlers = build_live_cli_stage_handlers()
    run_root = Path("runs") / "harness"
    continue_on_error = os.environ.get("HARNESS_CONTINUE_ON_ERROR", "1") == "1"

    failures: list[str] = []
    for scenario in scenarios:
        adapter_path = resolve_adapter_path(scenario.adapter_id)
        assert adapter_path.exists(), f"Adapter file missing: {adapter_path}"
        adapter = load_adapter(adapter_path)
        assert adapter.adapter_id == scenario.adapter_id

        result = run_scenario(
            scenario,
            stage_handlers,
            run_root=run_root,
            continue_on_error=continue_on_error,
        )

        repo_root_raw = ""
        for stage in result.stages:
            if stage.stage == "project_create":
                repo_root_raw = str(stage.details.get("repo_root") or "")
                break

        if repo_root_raw:
            assert_paths_exist(Path(repo_root_raw), adapter.required_paths)

        if not result.success:
            failures.append(
                f"scenario={scenario.scenario_id} run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
            )

    assert not failures, "Harness run failures:\n" + "\n".join(failures)
