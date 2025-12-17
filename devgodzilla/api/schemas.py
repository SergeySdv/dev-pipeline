from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

# =============================================================================
# Enums
# =============================================================================

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class ProtocolStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"

# =============================================================================
# Base Models
# =============================================================================

class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class Health(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    service: str = "devgodzilla"

# =============================================================================
# Project Models
# =============================================================================

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    git_url: Optional[str] = None
    local_path: Optional[str] = None
    base_branch: str = "main"

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    git_url: Optional[str] = None
    base_branch: Optional[str] = None
    local_path: Optional[str] = None

class ProjectOut(APIModel):
    id: int
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    git_url: Optional[str]
    base_branch: str = "main"
    local_path: Optional[str]
    created_at: Any
    updated_at: Any
    constitution_version: Optional[str] = None

# =============================================================================
# Protocol Models
# =============================================================================

class ProtocolCreate(BaseModel):
    project_id: int
    name: str = Field(..., description="Name of the protocol run")
    description: Optional[str] = None
    branch_name: Optional[str] = None
    template: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None

class ProtocolAction(str, Enum):
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"

class ProtocolActionRequest(BaseModel):
    action: ProtocolAction
    reason: Optional[str] = None

class ProtocolOut(APIModel):
    id: int
    project_id: int
    protocol_name: str
    status: str
    base_branch: str
    worktree_path: Optional[str]
    summary: Optional[str] = None
    windmill_flow_id: Optional[str]
    speckit_metadata: Optional[Dict[str, Any]]
    created_at: Any
    updated_at: Any

# =============================================================================
# Step Models
# =============================================================================

class StepOut(APIModel):
    id: int
    protocol_run_id: int
    step_index: int
    step_name: str
    step_type: str
    status: str
    retries: int = 0
    model: Optional[str] = None
    engine_id: Optional[str] = None
    policy: Optional[Dict[str, Any]] = None
    runtime_state: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    assigned_agent: Optional[str]
    depends_on: Optional[List[int]] = None
    parallel_group: Optional[str] = None
    created_at: Any
    updated_at: Any

class StepAction(str, Enum):
    EXECUTE = "execute"
    RETRY = "retry"
    SKIP = "skip"

class StepActionRequest(BaseModel):
    action: StepAction
    force: bool = False

# =============================================================================
# Agent Models
# =============================================================================

class AgentInfo(BaseModel):
    id: str
    name: str
    kind: str
    capabilities: List[str]
    status: str = "available"
    default_model: Optional[str] = None
    command_dir: Optional[str] = None

# =============================================================================
# Clarification Models
# =============================================================================

class ClarificationAnswer(BaseModel):
    answer: str
    answered_by: Optional[str] = None

class ClarificationOut(APIModel):
    id: int
    protocol_run_id: Optional[int]
    key: Optional[str] = None
    question: str
    status: str
    options: Optional[List[str]] = None
    recommended: Optional[Dict[str, Any]] = None
    applies_to: Optional[str] = None
    blocking: Optional[bool] = None
    answer: Optional[Dict[str, Any]]
    created_at: Any
    answered_at: Optional[Any]
    answered_by: Optional[str] = None

# =============================================================================
# QA Models
# =============================================================================

class QAFindingOut(BaseModel):
    severity: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    rule_id: Optional[str] = None
    suggestion: Optional[str] = None

class QAGateOut(BaseModel):
    id: str
    name: str
    status: str  # passed|warning|failed|skipped
    findings: List[QAFindingOut] = Field(default_factory=list)

class QAResultOut(BaseModel):
    verdict: str  # passed|warning|failed
    summary: Optional[str] = None
    gates: List[QAGateOut] = Field(default_factory=list)

# =============================================================================
# Artifact Models
# =============================================================================

class ArtifactOut(BaseModel):
    id: str
    type: str  # log|diff|file|report|json|text|unknown
    name: str
    size: int
    created_at: Optional[str] = None

class ArtifactContentOut(BaseModel):
    id: str
    name: str
    type: str
    content: str
    truncated: bool = False


class ProtocolArtifactOut(ArtifactOut):
    step_run_id: int
    step_name: Optional[str] = None

# =============================================================================
# Workflow / UI Convenience Models (Windmill React app)
# =============================================================================

class NextStepOut(BaseModel):
    step_run_id: Optional[int] = None


class GateFindingOut(BaseModel):
    code: str
    severity: str  # info|warning|error
    message: str
    step_id: Optional[str] = None
    suggested_fix: Optional[str] = None


class GateResultOut(BaseModel):
    article: str
    name: str
    status: str  # passed|warning|failed|skipped
    findings: List[GateFindingOut] = Field(default_factory=list)


class ChecklistItemOut(BaseModel):
    id: str
    description: str
    passed: bool
    required: bool


class ChecklistResultOut(BaseModel):
    passed: int
    total: int
    items: List[ChecklistItemOut] = Field(default_factory=list)


class QualitySummaryOut(BaseModel):
    protocol_run_id: int
    constitution_version: str = "1"
    score: float
    gates: List[GateResultOut] = Field(default_factory=list)
    checklist: ChecklistResultOut
    overall_status: str  # passed|warning|failed
    blocking_issues: int
    warnings: int


class FeedbackEventOut(BaseModel):
    id: str
    action_taken: str
    created_at: Any
    resolved: bool
    clarification: Optional[ClarificationOut] = None


class FeedbackListOut(BaseModel):
    events: List[FeedbackEventOut] = Field(default_factory=list)
