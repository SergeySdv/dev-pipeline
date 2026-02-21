from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


class HarnessAssertionError(AssertionError):
    """Raised when harness assertions fail."""


def assert_paths_exist(base_dir: Path, rel_paths: list[str]) -> None:
    missing = [rel for rel in rel_paths if not (base_dir / rel).exists()]
    if missing:
        raise HarnessAssertionError(
            f"Missing expected paths under {base_dir}: {', '.join(sorted(missing))}"
        )


def assert_glob_matches(base_dir: Path, pattern: str, min_matches: int = 1) -> list[Path]:
    matches = sorted(base_dir.glob(pattern))
    if len(matches) < min_matches:
        raise HarnessAssertionError(
            f"Expected at least {min_matches} match(es) for '{pattern}' under {base_dir}, got {len(matches)}"
        )
    return matches


def assert_json_file_has_keys(path: Path, keys: list[str]) -> dict[str, Any]:
    if not path.exists():
        raise HarnessAssertionError(f"Expected JSON file does not exist: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in keys if key not in data]
    if missing:
        raise HarnessAssertionError(f"JSON file {path} missing keys: {', '.join(missing)}")
    return data


def assert_protocol_terminal_status(actual: str, expected: str = "completed") -> None:
    if actual != expected:
        raise HarnessAssertionError(
            f"Protocol terminal status mismatch: expected '{expected}', got '{actual}'"
        )


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def write_diagnostic_file(run_dir: Path, name: str, payload: Any) -> Path:
    diagnostics_dir = run_dir / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)

    file_path = diagnostics_dir / name
    if file_path.suffix != ".json":
        file_path = file_path.with_suffix(".json")

    file_path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")
    return file_path
