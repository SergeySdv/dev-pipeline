from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Iterable, Set


def _iter_flow_script_paths(flow_json: dict[str, Any]) -> Iterable[str]:
    stack: list[Any] = [flow_json]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            path = cur.get("path")
            if isinstance(path, str):
                yield path
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)


def _flow_files() -> list[Path]:
    root = Path("windmill/flows/devgodzilla")
    return sorted([p for p in root.rglob("*.flow.json") if p.is_file()])


def _script_file_for_path(script_path: str) -> Path | None:
    if not script_path.startswith("u/devgodzilla/"):
        return None
    name = script_path.split("/", 2)[-1]
    return Path("windmill/scripts/devgodzilla") / f"{name}.py"


def test_windmill_flows_reference_existing_scripts() -> None:
    flows = _flow_files()
    assert flows, "no windmill flows found under windmill/flows/devgodzilla"

    missing: Set[str] = set()
    for flow_path in flows:
        if "_deprecated" in flow_path.parts:
            continue

        data = json.loads(flow_path.read_text(encoding="utf-8"))
        for script_path in _iter_flow_script_paths(data):
            script_file = _script_file_for_path(script_path)
            if script_file is None:
                continue
            if not script_file.exists():
                missing.add(f"{flow_path}: {script_path} -> {script_file}")

    assert not missing, "flow references missing scripts:\n" + "\n".join(sorted(missing))


def test_windmill_api_adapter_scripts_do_not_import_devgodzilla() -> None:
    scripts_dir = Path("windmill/scripts/devgodzilla")
    adapter_files = sorted([p for p in scripts_dir.glob("*_api.py") if p.is_file()])
    assert adapter_files, "no *_api.py windmill scripts found"

    offenders: Set[str] = set()
    for file_path in adapter_files:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "devgodzilla" or alias.name.startswith("devgodzilla."):
                        offenders.add(str(file_path))
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "devgodzilla" or node.module.startswith("devgodzilla.")):
                    offenders.add(str(file_path))

    assert not offenders, "API adapter scripts must not import devgodzilla:\n" + "\n".join(sorted(offenders))

