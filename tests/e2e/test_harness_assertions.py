from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.harness.assertions import (
    HarnessAssertionError,
    assert_glob_matches,
    assert_json_file_has_keys,
    assert_paths_exist,
    assert_protocol_terminal_status,
    write_diagnostic_file,
)


def test_assert_paths_exist_success(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("ok", encoding="utf-8")
    assert_paths_exist(tmp_path, ["a.txt"])


def test_assert_paths_exist_failure(tmp_path: Path) -> None:
    with pytest.raises(HarnessAssertionError):
        assert_paths_exist(tmp_path, ["missing.txt"])


def test_assert_glob_matches_and_json_keys(tmp_path: Path) -> None:
    json_path = tmp_path / "summary.json"
    json_path.write_text('{"languages": ["python"], "frameworks": []}', encoding="utf-8")
    matches = assert_glob_matches(tmp_path, "*.json", min_matches=1)
    assert matches

    data = assert_json_file_has_keys(json_path, ["languages", "frameworks"])
    assert "languages" in data


def test_assert_protocol_terminal_status_failure() -> None:
    with pytest.raises(HarnessAssertionError):
        assert_protocol_terminal_status("failed", expected="completed")


def test_write_diagnostic_file(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    output = write_diagnostic_file(run_dir, "diag", {"path": Path("x")})
    assert output.exists()
    assert output.suffix == ".json"
