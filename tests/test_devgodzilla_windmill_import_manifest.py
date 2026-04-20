from __future__ import annotations

import json
from pathlib import Path

from windmill.import_to_windmill import (
    _normalize_flow_module_input_transforms,
    create_flow,
    load_import_manifest,
)


def test_load_import_manifest_uses_default_when_missing(tmp_path: Path) -> None:
    root = tmp_path / "windmill"
    manifest = load_import_manifest(root=root, manifest_path=root / "missing.json")

    assert manifest["scripts"]["path_prefix"] == "u/devgodzilla"
    assert manifest["flows"]["path_prefix"] == "f/devgodzilla"
    assert manifest["apps"]["path_prefix"] == "app/devgodzilla"


def test_load_import_manifest_reads_manifest_file(tmp_path: Path) -> None:
    root = tmp_path / "windmill"
    root.mkdir(parents=True)
    manifest_path = root / "import-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "scripts": {"source_dir": "custom_scripts", "path_prefix": "u/custom"},
                "flows": {"source_dir": "custom_flows", "path_prefix": "f/custom"},
                "apps": {"source_dir": "custom_apps", "path_prefix": "app/custom", "items": []},
            }
        ),
        encoding="utf-8",
    )

    manifest = load_import_manifest(root=root, manifest_path=manifest_path)
    assert manifest["scripts"]["source_dir"] == "custom_scripts"
    assert manifest["flows"]["source_dir"] == "custom_flows"
    assert manifest["apps"]["source_dir"] == "custom_apps"


def test_normalize_flow_module_input_transforms_moves_transforms_into_module_value() -> None:
    flow_def = {
        "value": {
            "modules": [
                {
                    "id": "speckit_specify",
                    "value": {"type": "script", "path": "u/devgodzilla/speckit_specify_api"},
                    "input_transforms": {"project_id": {"type": "javascript", "expr": "flow_input.project_id"}},
                },
                {
                    "id": "branch",
                    "value": {
                        "modules": [
                            {
                                "id": "nested",
                                "value": {"type": "script", "path": "u/devgodzilla/speckit_plan_api"},
                                "input_transforms": {
                                    "spec_run_id": {"type": "javascript", "expr": "results.speckit_specify.spec_run_id"}
                                },
                            }
                        ]
                    },
                },
            ]
        }
    }

    _normalize_flow_module_input_transforms(flow_def)

    top = flow_def["value"]["modules"][0]
    nested = flow_def["value"]["modules"][1]["value"]["modules"][0]

    assert "input_transforms" not in top
    assert top["value"]["input_transforms"]["project_id"]["expr"] == "flow_input.project_id"
    assert "input_transforms" not in nested
    assert nested["value"]["input_transforms"]["spec_run_id"]["expr"] == "results.speckit_specify.spec_run_id"


def test_normalize_flow_module_input_transforms_preserves_non_empty_value_transforms() -> None:
    flow_def = {
        "value": {
            "modules": [
                {
                    "id": "onboard_project",
                    "value": {
                        "type": "script",
                        "path": "u/devgodzilla/project_onboard_api",
                        "input_transforms": {
                            "project_id": {"type": "javascript", "expr": "flow_input.project_id || null"},
                            "branch": {"type": "javascript", "expr": "flow_input.branch || 'main'"},
                        },
                    },
                    "input_transforms": {},
                }
            ]
        }
    }

    _normalize_flow_module_input_transforms(flow_def)

    module = flow_def["value"]["modules"][0]
    assert "input_transforms" not in module
    assert module["value"]["input_transforms"] == {
        "project_id": {"type": "javascript", "expr": "flow_input.project_id || null"},
        "branch": {"type": "javascript", "expr": "flow_input.branch || 'main'"},
    }


def test_create_flow_recreates_existing_flow_before_create(monkeypatch) -> None:
    calls: list[tuple[str, str, str | None]] = []

    def fake_api_request(base_url, endpoint, token, method="GET", data=None):
        calls.append((endpoint, method, data.get("path") if isinstance(data, dict) else None))
        if endpoint.endswith("/flows/get/f/devgodzilla/brownfield_feature"):
            return {"path": "f/devgodzilla/brownfield_feature"}
        if endpoint.endswith("/flows/delete/f/devgodzilla/brownfield_feature"):
            return {"status": "deleted"}
        if endpoint.endswith("/flows/create"):
            return {"status": "created"}
        raise AssertionError(f"unexpected api request: {endpoint} {method}")

    monkeypatch.setattr("windmill.import_to_windmill.api_request", fake_api_request)

    ok = create_flow(
        "http://localhost:8001",
        "token",
        "demo1",
        "f/devgodzilla/brownfield_feature",
        {"summary": "Brownfield", "value": {"modules": []}, "schema": {"type": "object"}},
    )

    assert ok is True
    assert calls == [
        ("/w/demo1/flows/get/f/devgodzilla/brownfield_feature", "GET", None),
        ("/w/demo1/flows/delete/f/devgodzilla/brownfield_feature", "DELETE", None),
        ("/w/demo1/flows/create", "POST", "f/devgodzilla/brownfield_feature"),
    ]
