from dataclasses import dataclass
from typing import Optional


class ProtocolStatus:
    PENDING = "pending"
    PLANNING = "planning"
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class StepStatus:
    PENDING = "pending"
    RUNNING = "running"
    NEEDS_QA = "needs_qa"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


@dataclass
class Project:
    id: int
    name: str
    git_url: str
    local_path: Optional[str]
    base_branch: str
    ci_provider: Optional[str]
    secrets: Optional[dict]
    default_models: Optional[dict]
    created_at: str
    updated_at: str
    project_classification: Optional[str] = None
    policy_pack_key: Optional[str] = None
    policy_pack_version: Optional[str] = None
    policy_overrides: Optional[dict] = None
    policy_repo_local_enabled: Optional[bool] = None
    policy_effective_hash: Optional[str] = None
    policy_enforcement_mode: Optional[str] = None


@dataclass
class ProtocolRun:
    id: int
    project_id: int
    protocol_name: str
    status: str
    base_branch: str
    worktree_path: Optional[str]
    protocol_root: Optional[str]
    description: Optional[str]
    template_config: Optional[dict]
    template_source: Optional[dict]
    created_at: str
    updated_at: str
    policy_pack_key: Optional[str] = None
    policy_pack_version: Optional[str] = None
    policy_effective_hash: Optional[str] = None
    policy_effective_json: Optional[dict] = None


@dataclass
class StepRun:
    id: int
    protocol_run_id: int
    step_index: int
    step_name: str
    step_type: str
    status: str
    retries: int
    model: Optional[str]
    engine_id: Optional[str]
    policy: Optional[object]
    runtime_state: Optional[dict]
    summary: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class Event:
    id: int
    protocol_run_id: int
    step_run_id: Optional[int]
    event_type: str
    message: str
    metadata: Optional[dict]
    created_at: str
    protocol_name: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None


class CodexRunStatus:
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CodexRun:
    run_id: str
    job_type: str
    status: str
    created_at: str
    updated_at: str
    run_kind: Optional[str] = None
    project_id: Optional[int] = None
    protocol_run_id: Optional[int] = None
    step_run_id: Optional[int] = None
    queue: Optional[str] = None
    attempt: Optional[int] = None
    worker_id: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    prompt_version: Optional[str] = None
    params: Optional[dict] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    log_path: Optional[str] = None
    cost_tokens: Optional[int] = None
    cost_cents: Optional[int] = None


@dataclass
class RunArtifact:
    id: int
    run_id: str
    name: str
    kind: str
    path: str
    sha256: Optional[str]
    bytes: Optional[int]
    created_at: str


@dataclass
class PolicyPack:
    id: int
    key: str
    version: str
    name: str
    description: Optional[str]
    status: str
    pack: dict
    created_at: str
    updated_at: str


@dataclass
class Clarification:
    id: int
    scope: str
    project_id: int
    protocol_run_id: Optional[int]
    step_run_id: Optional[int]
    key: str
    question: str
    recommended: Optional[dict]
    options: Optional[list]
    applies_to: Optional[str]
    blocking: bool
    answer: Optional[dict]
    status: str
    created_at: str
    updated_at: str
    answered_at: Optional[str] = None
    answered_by: Optional[str] = None
