from __future__ import annotations

import json
from pathlib import Path

from windmill.import_to_windmill import load_import_manifest


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

