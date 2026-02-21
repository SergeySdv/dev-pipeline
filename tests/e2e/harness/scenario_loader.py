from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas" / "e2e-workflow-harness.schema.json"
DEFAULT_SCENARIOS_DIR = REPO_ROOT / "tests" / "e2e" / "scenarios"
DEFAULT_ADAPTERS_DIR = REPO_ROOT / "tests" / "e2e" / "adapters"


@dataclass(frozen=True)
class RepoConfig:
    owner: str
    name: str
    url: str
    default_branch: str
    pin_ref: str | None = None


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int
    backoff_seconds: float
    max_backoff_seconds: float


@dataclass(frozen=True)
class TimeoutConfig:
    onboard_seconds: int
    planning_seconds: int
    execution_seconds: int


@dataclass(frozen=True)
class ScenarioConfig:
    scenario_id: str
    source: str
    repo: RepoConfig
    adapter_id: str
    workflow_stages: list[str]
    discovery_outputs: list[str]
    min_protocol_steps: int
    terminal_protocol_status: str
    artifact_patterns: list[str]
    retries: RetryConfig
    timeouts: TimeoutConfig
    raw: dict[str, Any]


@dataclass(frozen=True)
class AdapterConfig:
    adapter_id: str
    required_paths: list[str]
    path_aliases: dict[str, str]
    discovery_expectations: dict[str, Any]
    artifact_patterns: list[str]
    branch_prefix: str
    require_worktree_registration: bool
    raw: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_repo_url(owner: str, name: str) -> str:
    return f"https://github.com/{owner}/{name}.git"


def _parse_repo_allowlist(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {name.strip().lower() for name in raw.split(",") if name.strip()}


def _apply_repo_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(data)
    repo = updated.setdefault("repo", {})

    owner_override = os.environ.get("HARNESS_GITHUB_OWNER")
    if owner_override:
        repo["owner"] = owner_override

    url_override = os.environ.get("HARNESS_REPO_URL_OVERRIDE")
    if url_override:
        repo["url"] = url_override

    if repo.get("owner") and repo.get("name") and not repo.get("url"):
        repo["url"] = _default_repo_url(repo["owner"], repo["name"])

    return updated


def _validate_instance(data: dict[str, Any], schema: dict[str, Any], ref: str) -> None:
    effective_schema = copy.deepcopy(schema)
    effective_schema["$ref"] = ref

    validator = Draft202012Validator(effective_schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda err: err.json_path)
    if not errors:
        return

    rendered = "; ".join(f"{err.json_path}: {err.message}" for err in errors)
    raise ValueError(f"Schema validation failed: {rendered}")


def _load_schema(schema_path: Path | None = None) -> dict[str, Any]:
    path = schema_path or DEFAULT_SCHEMA_PATH
    if not path.exists():
        raise FileNotFoundError(f"Harness schema file not found: {path}")
    return _read_json(path)


def load_scenario(path: Path, schema_path: Path | None = None) -> ScenarioConfig:
    schema = _load_schema(schema_path)
    raw = _apply_repo_env_overrides(_read_json(path))
    _validate_instance(raw, schema, "#/$defs/scenario")

    repo = raw["repo"]
    expectations = raw["expectations"]

    return ScenarioConfig(
        scenario_id=raw["scenario_id"],
        source=raw.get("source", "github_user_allowlist"),
        repo=RepoConfig(
            owner=repo["owner"],
            name=repo["name"],
            url=repo["url"],
            default_branch=repo["default_branch"],
            pin_ref=repo.get("pin_ref"),
        ),
        adapter_id=raw["adapter_id"],
        workflow_stages=list(raw["workflow"]["stages"]),
        discovery_outputs=list(expectations["discovery_outputs"]),
        min_protocol_steps=int(expectations["min_protocol_steps"]),
        terminal_protocol_status=expectations["terminal_protocol_status"],
        artifact_patterns=list(expectations.get("artifact_patterns", [])),
        retries=RetryConfig(
            max_attempts=int(raw["retries"]["max_attempts"]),
            backoff_seconds=float(raw["retries"]["backoff_seconds"]),
            max_backoff_seconds=float(raw["retries"]["max_backoff_seconds"]),
        ),
        timeouts=TimeoutConfig(
            onboard_seconds=int(raw["timeouts"]["onboard_seconds"]),
            planning_seconds=int(raw["timeouts"]["planning_seconds"]),
            execution_seconds=int(raw["timeouts"]["execution_seconds"]),
        ),
        raw=raw,
    )


def load_adapter(path: Path, schema_path: Path | None = None) -> AdapterConfig:
    schema = _load_schema(schema_path)
    raw = _read_json(path)
    _validate_instance(raw, schema, "#/$defs/adapter")

    worktree = raw["worktree_branch_expectations"]
    return AdapterConfig(
        adapter_id=raw["adapter_id"],
        required_paths=list(raw["required_paths"]),
        path_aliases=dict(raw.get("path_aliases", {})),
        discovery_expectations=dict(raw.get("discovery_expectations", {})),
        artifact_patterns=list(raw.get("artifact_patterns", [])),
        branch_prefix=worktree["branch_prefix"],
        require_worktree_registration=bool(worktree["require_worktree_registration"]),
        raw=raw,
    )


def load_scenarios(scenarios_dir: Path | None = None, schema_path: Path | None = None) -> list[ScenarioConfig]:
    directory = scenarios_dir or DEFAULT_SCENARIOS_DIR
    if not directory.exists():
        return []
    scenarios = [load_scenario(path, schema_path=schema_path) for path in sorted(directory.glob("*.json"))]

    allowlist = _parse_repo_allowlist(os.environ.get("HARNESS_GITHUB_REPOS"))
    if not allowlist:
        return scenarios

    return [scenario for scenario in scenarios if scenario.repo.name.lower() in allowlist]


def resolve_adapter_path(adapter_id: str, adapters_dir: Path | None = None) -> Path:
    directory = adapters_dir or DEFAULT_ADAPTERS_DIR
    return directory / f"{adapter_id}.adapter.json"
