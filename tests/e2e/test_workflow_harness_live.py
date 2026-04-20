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

    if not os.environ.get("DEVGODZILLA_DB_URL") and not os.environ.get("DEVGODZILLA_DB_PATH"):
        os.environ["DEVGODZILLA_DB_URL"] = "postgresql://devgodzilla:changeme@localhost:5432/devgodzilla_db"

    scenarios = load_scenarios()
    scenario_filter = os.environ.get("HARNESS_SCENARIO")
    if scenario_filter:
        scenarios = [scenario for scenario in scenarios if scenario.scenario_id == scenario_filter]

    assert scenarios, "No harness scenarios loaded"

    step_engine = (os.environ.get("HARNESS_STEP_ENGINE", "opencode").strip() or "opencode").lower()
    onboard_mode = (os.environ.get("HARNESS_ONBOARD_MODE", "windmill").strip() or "windmill").lower()
    selected_stages = {stage for scenario in scenarios for stage in scenario.workflow_stages}
    require_windmill = onboard_mode == "windmill" and (
        "project_onboard" in selected_stages or "project_onboard_windmill" in selected_stages
    )
    require_opencode = step_engine == "opencode" or any(stage.startswith("speckit_") for stage in selected_stages)
    report = run_preflight(
        auto_start=True,
        require_opencode=require_opencode,
        require_windmill=require_windmill,
    )
    assert report.ok, f"Preflight failed: errors={report.errors} warnings={report.warnings} details={report.details}"

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
        stage_by_name = {stage.stage: stage for stage in result.stages}

        repo_root_raw = ""
        for stage in result.stages:
            if stage.stage == "project_create":
                repo_root_raw = str(stage.details.get("repo_root") or "")
                break

        if repo_root_raw:
            assert_paths_exist(Path(repo_root_raw), adapter.required_paths)

        missing_stages = [stage_name for stage_name in scenario.workflow_stages if stage_name not in stage_by_name]
        if missing_stages:
            failures.append(
                "scenario="
                f"{scenario.scenario_id} missing_stages={missing_stages} "
                f"run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
            )

        protocol_cycles_stage = stage_by_name.get("protocol_feature_cycles")
        if protocol_cycles_stage and protocol_cycles_stage.status == "passed":
            details = protocol_cycles_stage.details or {}
            cycles = details.get("cycles")
            if not isinstance(cycles, list) or not cycles:
                failures.append(
                    "scenario="
                    f"{scenario.scenario_id} protocol_feature_cycles missing cycle details "
                    f"run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
                )
            else:
                min_steps = int(scenario.min_protocol_steps)
                for cycle in cycles:
                    cycle_num = cycle.get("cycle")
                    protocol_id = cycle.get("protocol_run_id")
                    steps_created = int(cycle.get("steps_created") or 0)
                    executed_steps = int(cycle.get("executed_steps") or 0)
                    if not protocol_id or steps_created < min_steps or executed_steps < 1:
                        failures.append(
                            "scenario="
                            f"{scenario.scenario_id} invalid protocol cycle details "
                            f"cycle={cycle_num} protocol_run_id={protocol_id} "
                            f"steps_created={steps_created} executed_steps={executed_steps} "
                            f"run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
                        )

        speckit_init_stage = stage_by_name.get("speckit_init")
        if speckit_init_stage and speckit_init_stage.status == "passed":
            init_path = str(speckit_init_stage.details.get("path") or "")
            if not init_path or not Path(init_path).exists():
                failures.append(
                    "scenario="
                    f"{scenario.scenario_id} speckit_init missing valid path "
                    f"path={init_path} run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
                )

        speckit_specify_stage = stage_by_name.get("speckit_specify")
        if speckit_specify_stage and speckit_specify_stage.status == "passed":
            details = speckit_specify_stage.details or {}
            spec_run_id = int(details.get("spec_run_id") or 0)
            worktree_path = str(details.get("worktree_path") or "")
            spec_path = str(details.get("spec_path") or "")
            if spec_run_id <= 0 or not worktree_path or not spec_path:
                failures.append(
                    "scenario="
                    f"{scenario.scenario_id} speckit_specify missing linkage details "
                    f"spec_run_id={spec_run_id} worktree_path={worktree_path} spec_path={spec_path} "
                    f"run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
                )
            elif not Path(spec_path).exists() or not Path(worktree_path).exists():
                failures.append(
                    "scenario="
                    f"{scenario.scenario_id} speckit_specify paths missing "
                    f"worktree_path={worktree_path} spec_path={spec_path} "
                    f"run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
                )
            else:
                for stage_name in (
                    "speckit_clarify",
                    "speckit_plan",
                    "speckit_tasks",
                    "speckit_checklist",
                    "speckit_analyze",
                    "speckit_implement",
                ):
                    stage_result = stage_by_name.get(stage_name)
                    if not stage_result or stage_result.status != "passed":
                        continue
                    stage_details = stage_result.details or {}
                    if int(stage_details.get("spec_run_id") or 0) != spec_run_id:
                        failures.append(
                            "scenario="
                            f"{scenario.scenario_id} {stage_name} spec_run_id drift "
                            f"expected={spec_run_id} got={stage_details.get('spec_run_id')} "
                            f"run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
                        )
                    if str(stage_details.get("worktree_path") or "") != worktree_path:
                        failures.append(
                            "scenario="
                            f"{scenario.scenario_id} {stage_name} worktree drift "
                            f"expected={worktree_path} got={stage_details.get('worktree_path')} "
                            f"run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
                        )

                implement_stage = stage_by_name.get("speckit_implement")
                if implement_stage and implement_stage.status == "passed":
                    impl = implement_stage.details or {}
                    protocol_id = int(impl.get("protocol_id") or 0)
                    step_count = int(impl.get("step_count") or 0)
                    protocol_root = str(impl.get("protocol_root") or "")
                    metadata_path = str(impl.get("metadata_path") or "")
                    if protocol_id <= 0 or step_count < 1 or not protocol_root or not metadata_path:
                        failures.append(
                            "scenario="
                            f"{scenario.scenario_id} speckit_implement missing protocol linkage "
                            f"protocol_id={protocol_id} step_count={step_count} "
                            f"protocol_root={protocol_root} metadata_path={metadata_path} "
                            f"run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
                        )
                    elif not Path(protocol_root).exists() or not Path(metadata_path).exists():
                        failures.append(
                            "scenario="
                            f"{scenario.scenario_id} speckit_implement protocol artifacts missing "
                            f"protocol_root={protocol_root} metadata_path={metadata_path} "
                            f"run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
                        )

        if not result.success:
            failures.append(
                "scenario="
                f"{scenario.scenario_id} failed_stages="
                f"{[stage.stage for stage in result.stages if stage.status != 'passed']} "
                f"run_dir={result.run_dir} diagnostics={result.diagnostics_dir}"
            )

    assert not failures, "Harness run failures:\n" + "\n".join(failures)
