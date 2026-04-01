#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;

#[derive(Debug, Clone, Deserialize, Default)]
pub struct Project {
    pub id: i64,
    pub name: String,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub status: Option<String>,
    #[serde(default)]
    pub git_url: Option<String>,
    #[serde(default)]
    pub base_branch: Option<String>,
    #[serde(default)]
    pub local_path: Option<String>,
    #[serde(default)]
    pub repo_mode: Option<String>,
    #[serde(default)]
    pub task_cycle_autonomous: bool,
    #[serde(default)]
    pub managed_repo_root_override: Option<String>,
    #[serde(default)]
    pub worktrees_root_override: Option<String>,
    #[serde(default)]
    pub artifacts_root_override: Option<String>,
    #[serde(default)]
    pub effective_repo_path: Option<String>,
    #[serde(default)]
    pub effective_worktrees_root: Option<String>,
    #[serde(default)]
    pub effective_artifacts_root: Option<String>,
    #[serde(default)]
    pub github_token_configured: bool,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub updated_at: Option<String>,
    #[serde(default)]
    pub constitution_version: Option<String>,
    #[serde(default)]
    pub policy_pack_key: Option<String>,
    #[serde(default)]
    pub policy_pack_version: Option<String>,
    #[serde(default)]
    pub policy_overrides: Option<Value>,
    #[serde(default)]
    pub policy_repo_local_enabled: Option<bool>,
    #[serde(default)]
    pub policy_effective_hash: Option<String>,
    #[serde(default)]
    pub policy_enforcement_mode: Option<String>,
    #[serde(default)]
    pub onboarding_queued: Option<bool>,
    #[serde(default)]
    pub onboarding_error: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProtocolRun {
    pub id: i64,
    #[serde(default)]
    pub project_id: Option<i64>,
    pub protocol_name: String,
    #[serde(default)]
    pub status: Option<String>,
    #[serde(default)]
    pub base_branch: Option<String>,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub protocol_root: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub summary: Option<String>,
    #[serde(default)]
    pub policy_pack_key: Option<String>,
    #[serde(default)]
    pub policy_pack_version: Option<String>,
    #[serde(default)]
    pub policy_effective_hash: Option<String>,
    #[serde(default)]
    pub policy_effective_json: Option<Value>,
    #[serde(default)]
    pub windmill_flow_id: Option<String>,
    #[serde(default)]
    pub speckit_metadata: Option<Value>,
    #[serde(default)]
    pub linked_sprint_id: Option<i64>,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct BrownfieldRun {
    #[serde(default)]
    pub success: bool,
    #[serde(default)]
    pub project_id: i64,
    #[serde(default)]
    pub output_mode: String,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub spec_path: Option<String>,
    #[serde(default)]
    pub plan_path: Option<String>,
    #[serde(default)]
    pub tasks_path: Option<String>,
    #[serde(default)]
    pub protocol: Option<ProtocolRun>,
    #[serde(default)]
    pub next_work_item_id: Option<i64>,
    #[serde(default)]
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct StepRun {
    pub id: i64,
    #[serde(default)]
    pub protocol_run_id: Option<i64>,
    pub step_index: i32,
    pub step_name: String,
    #[serde(default)]
    pub step_type: Option<String>,
    pub status: String,
    #[serde(default)]
    pub retries: i32,
    #[serde(default)]
    pub model: Option<String>,
    #[serde(default)]
    pub engine_id: Option<String>,
    #[serde(default)]
    pub policy: Option<Value>,
    #[serde(default)]
    pub runtime_state: Option<Value>,
    #[serde(default)]
    pub summary: Option<String>,
    #[serde(default)]
    pub assigned_agent: Option<String>,
    #[serde(default)]
    pub depends_on: Option<Vec<i64>>,
    #[serde(default)]
    pub parallel_group: Option<String>,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct Event {
    #[serde(default)]
    pub id: Option<i64>,
    #[serde(default)]
    pub protocol_run_id: Option<i64>,
    #[serde(default)]
    pub step_run_id: Option<i64>,
    pub event_type: String,
    pub message: String,
    #[serde(default)]
    pub created_at: String,
    #[serde(default)]
    pub metadata: Option<Value>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct QueueJob {
    #[serde(default)]
    pub job_id: Option<String>,
    #[serde(default)]
    pub job_type: Option<String>,
    #[serde(default)]
    pub status: Option<String>,
    #[serde(default)]
    pub enqueued_at: Option<String>,
    #[serde(default)]
    pub started_at: Option<String>,
    #[serde(default)]
    pub ended_at: Option<String>,
    #[serde(default)]
    pub payload: Option<Value>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProjectPolicy {
    #[serde(default)]
    pub policy_pack_key: Option<String>,
    #[serde(default)]
    pub policy_pack_version: Option<String>,
    #[serde(default)]
    pub policy_overrides: Option<Value>,
    #[serde(default)]
    pub policy_repo_local_enabled: bool,
    #[serde(default = "default_policy_enforcement_mode")]
    pub policy_enforcement_mode: String,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct EffectivePolicy {
    #[serde(default)]
    pub hash: String,
    #[serde(default)]
    pub policy: Value,
    #[serde(default)]
    pub pack_key: String,
    #[serde(default)]
    pub pack_version: String,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct PolicyFinding {
    #[serde(default)]
    pub code: String,
    #[serde(default)]
    pub severity: String,
    #[serde(default)]
    pub message: String,
    #[serde(default)]
    pub scope: String,
    #[serde(default)]
    pub location: Option<String>,
    #[serde(default)]
    pub suggested_fix: Option<String>,
    #[serde(default)]
    pub metadata: Option<Value>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProjectBranch {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub sha: String,
    #[serde(default)]
    pub is_remote: bool,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProjectClarification {
    pub id: i64,
    #[serde(default)]
    pub key: Option<String>,
    #[serde(default)]
    pub question: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub options: Option<Vec<String>>,
    #[serde(default)]
    pub blocking: Option<bool>,
    #[serde(default)]
    pub answer: Option<Value>,
    #[serde(default)]
    pub applies_to: Option<String>,
    #[serde(default)]
    pub answered_by: Option<String>,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub answered_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProjectCommit {
    #[serde(default)]
    pub sha: String,
    #[serde(default)]
    pub message: String,
    #[serde(default)]
    pub author: String,
    #[serde(default)]
    pub date: String,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProjectPullRequest {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub branch: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub checks: String,
    #[serde(default)]
    pub url: String,
    #[serde(default)]
    pub author: String,
    #[serde(default)]
    pub created_at: String,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProjectWorktree {
    #[serde(default)]
    pub branch_name: String,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub protocol_run_id: Option<i64>,
    #[serde(default)]
    pub protocol_name: Option<String>,
    #[serde(default)]
    pub protocol_status: Option<String>,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub last_commit_sha: Option<String>,
    #[serde(default)]
    pub last_commit_message: Option<String>,
    #[serde(default)]
    pub last_commit_date: Option<String>,
    #[serde(default)]
    pub pr_url: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProjectSpec {
    pub id: i64,
    #[serde(default)]
    pub project_id: Option<i64>,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub path: String,
    #[serde(default)]
    pub spec_path: Option<String>,
    #[serde(default)]
    pub plan_path: Option<String>,
    #[serde(default)]
    pub tasks_path: Option<String>,
    #[serde(default)]
    pub checklist_path: Option<String>,
    #[serde(default)]
    pub analysis_path: Option<String>,
    #[serde(default)]
    pub implement_path: Option<String>,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub error_message: Option<String>,
    #[serde(default)]
    pub branch_name: Option<String>,
    #[serde(default)]
    pub base_branch: Option<String>,
    #[serde(default)]
    pub feature_name: Option<String>,
    #[serde(default)]
    pub spec_number: Option<i64>,
    #[serde(default)]
    pub linked_tasks: i64,
    #[serde(default)]
    pub completed_tasks: i64,
    #[serde(default)]
    pub story_points: i64,
    #[serde(default)]
    pub has_plan: bool,
    #[serde(default)]
    pub has_tasks: bool,
    #[serde(default)]
    pub protocol_id: Option<i64>,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProjectSpecificationsList {
    #[serde(default)]
    pub items: Vec<ProjectSpec>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct OnboardingStage {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub started_at: Option<String>,
    #[serde(default)]
    pub completed_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct OnboardingEvent {
    pub id: i64,
    #[serde(default)]
    pub event_type: String,
    #[serde(default)]
    pub message: String,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub metadata: Option<Value>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProjectOnboardingSummary {
    pub project_id: i64,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub stages: Vec<OnboardingStage>,
    #[serde(default)]
    pub events: Vec<OnboardingEvent>,
    #[serde(default)]
    pub blocking_clarifications: i64,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct Artifact {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub r#type: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub size: i64,
    #[serde(default)]
    pub created_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ArtifactContent {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub r#type: String,
    #[serde(default)]
    pub content: String,
    #[serde(default)]
    pub truncated: bool,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SpecificationContent {
    pub id: i64,
    #[serde(default)]
    pub path: String,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub spec_content: Option<String>,
    #[serde(default)]
    pub plan_content: Option<String>,
    #[serde(default)]
    pub tasks_content: Option<String>,
    #[serde(default)]
    pub checklist_content: Option<String>,
    #[serde(default)]
    pub analysis_content: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SpecKitInitResult {
    #[serde(default)]
    pub success: bool,
    #[serde(default)]
    pub path: Option<String>,
    #[serde(default)]
    pub constitution_hash: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
    #[serde(default)]
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SpecKitSpecifyResult {
    #[serde(default)]
    pub success: bool,
    #[serde(default)]
    pub spec_path: Option<String>,
    #[serde(default)]
    pub spec_number: Option<i64>,
    #[serde(default)]
    pub feature_name: Option<String>,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub branch_name: Option<String>,
    #[serde(default)]
    pub base_branch: Option<String>,
    #[serde(default)]
    pub spec_root: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SpecKitPlanResult {
    #[serde(default)]
    pub success: bool,
    #[serde(default)]
    pub plan_path: Option<String>,
    #[serde(default)]
    pub data_model_path: Option<String>,
    #[serde(default)]
    pub contracts_path: Option<String>,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SpecKitTasksResult {
    #[serde(default)]
    pub success: bool,
    #[serde(default)]
    pub tasks_path: Option<String>,
    #[serde(default)]
    pub task_count: i64,
    #[serde(default)]
    pub parallelizable_count: i64,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SpecKitClarifyResult {
    #[serde(default)]
    pub success: bool,
    #[serde(default)]
    pub spec_path: Option<String>,
    #[serde(default)]
    pub clarifications_added: i64,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SpecKitChecklistResult {
    #[serde(default)]
    pub success: bool,
    #[serde(default)]
    pub checklist_path: Option<String>,
    #[serde(default)]
    pub item_count: i64,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SpecKitAnalyzeResult {
    #[serde(default)]
    pub success: bool,
    #[serde(default)]
    pub report_path: Option<String>,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SpecKitImplementResult {
    #[serde(default)]
    pub success: bool,
    #[serde(default)]
    pub run_path: Option<String>,
    #[serde(default)]
    pub metadata_path: Option<String>,
    #[serde(default)]
    pub protocol_id: Option<i64>,
    #[serde(default)]
    pub protocol_root: Option<String>,
    #[serde(default)]
    pub step_count: i64,
    #[serde(default)]
    pub warnings: Vec<String>,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SpecKitCleanupResult {
    #[serde(default)]
    pub success: bool,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub worktree_path: Option<String>,
    #[serde(default)]
    pub deleted_remote_branch: bool,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProtocolArtifact {
    #[serde(flatten)]
    pub artifact: Artifact,
    #[serde(default)]
    pub step_run_id: i64,
    #[serde(default)]
    pub step_name: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct JobRun {
    #[serde(default)]
    pub run_id: String,
    #[serde(default)]
    pub job_type: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub run_kind: Option<String>,
    #[serde(default)]
    pub project_id: Option<i64>,
    #[serde(default)]
    pub protocol_run_id: Option<i64>,
    #[serde(default)]
    pub step_run_id: Option<i64>,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub task_id: Option<i64>,
    #[serde(default)]
    pub task_title: Option<String>,
    #[serde(default)]
    pub task_board_status: Option<String>,
    #[serde(default)]
    pub sprint_id: Option<i64>,
    #[serde(default)]
    pub sprint_name: Option<String>,
    #[serde(default)]
    pub sprint_status: Option<String>,
    #[serde(default)]
    pub queue: Option<String>,
    #[serde(default)]
    pub attempt: Option<i64>,
    #[serde(default)]
    pub worker_id: Option<String>,
    #[serde(default)]
    pub started_at: Option<String>,
    #[serde(default)]
    pub finished_at: Option<String>,
    #[serde(default)]
    pub params: Option<Value>,
    #[serde(default)]
    pub result: Option<Value>,
    #[serde(default)]
    pub error: Option<String>,
    #[serde(default)]
    pub log_path: Option<String>,
    #[serde(default)]
    pub cost_tokens: Option<i64>,
    #[serde(default)]
    pub cost_cents: Option<i64>,
    #[serde(default)]
    pub windmill_job_id: Option<String>,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProtocolSpec {
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub spec_hash: Option<String>,
    #[serde(default)]
    pub validation_status: Option<String>,
    #[serde(default)]
    pub validated_at: Option<String>,
    #[serde(default)]
    pub spec: Value,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct GateFinding {
    #[serde(default)]
    pub code: String,
    #[serde(default)]
    pub severity: String,
    #[serde(default)]
    pub message: String,
    #[serde(default)]
    pub step_id: Option<String>,
    #[serde(default)]
    pub suggested_fix: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct GateResult {
    #[serde(default)]
    pub article: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub findings: Vec<GateFinding>,
    #[serde(default)]
    pub details: Option<Value>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ChecklistItem {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub passed: bool,
    #[serde(default)]
    pub required: bool,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ChecklistResult {
    #[serde(default)]
    pub passed: i64,
    #[serde(default)]
    pub total: i64,
    #[serde(default)]
    pub items: Vec<ChecklistItem>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct QualitySummary {
    #[serde(default)]
    pub protocol_run_id: i64,
    #[serde(default)]
    pub constitution_version: String,
    #[serde(default)]
    pub score: f64,
    #[serde(default)]
    pub gates: Vec<GateResult>,
    #[serde(default)]
    pub checklist: ChecklistResult,
    #[serde(default)]
    pub overall_status: String,
    #[serde(default)]
    pub blocking_issues: i64,
    #[serde(default)]
    pub warnings: i64,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct FeedbackEvent {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub action_taken: String,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub resolved: bool,
    #[serde(default)]
    pub clarification: Option<ProjectClarification>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct FeedbackList {
    #[serde(default)]
    pub events: Vec<FeedbackEvent>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct QualityOverview {
    #[serde(default)]
    pub total_protocols: i64,
    #[serde(default)]
    pub passed: i64,
    #[serde(default)]
    pub warnings: i64,
    #[serde(default)]
    pub failed: i64,
    #[serde(default)]
    pub average_score: i64,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct QualityFinding {
    #[serde(default)]
    pub id: i64,
    #[serde(default)]
    pub protocol_id: i64,
    #[serde(default)]
    pub spec_run_id: Option<i64>,
    #[serde(default)]
    pub project_name: String,
    #[serde(default)]
    pub article: String,
    #[serde(default)]
    pub article_name: String,
    #[serde(default)]
    pub severity: String,
    #[serde(default)]
    pub message: String,
    #[serde(default)]
    pub timestamp: String,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ConstitutionalGate {
    #[serde(default)]
    pub article: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub checks: i64,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct QualityDashboard {
    #[serde(default)]
    pub overview: QualityOverview,
    #[serde(default)]
    pub recent_findings: Vec<QualityFinding>,
    #[serde(default)]
    pub constitutional_gates: Vec<ConstitutionalGate>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct JobTypeMetric {
    #[serde(default)]
    pub job_type: String,
    #[serde(default)]
    pub count: i64,
    #[serde(default)]
    pub avg_duration_seconds: Option<f64>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct MetricsSummary {
    #[serde(default)]
    pub total_events: i64,
    #[serde(default)]
    pub total_protocol_runs: i64,
    #[serde(default)]
    pub total_step_runs: i64,
    #[serde(default)]
    pub total_job_runs: i64,
    #[serde(default)]
    pub active_projects: i64,
    #[serde(default)]
    pub success_rate: f64,
    #[serde(default)]
    pub job_type_metrics: Vec<JobTypeMetric>,
    #[serde(default)]
    pub recent_events_count: i64,
    #[serde(default)]
    pub degraded: bool,
    #[serde(default)]
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct PolicyPack {
    #[serde(default)]
    pub id: i64,
    #[serde(default)]
    pub key: String,
    #[serde(default)]
    pub version: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub pack: Value,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct AgentInfo {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub kind: String,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub default_model: Option<String>,
    #[serde(default)]
    pub available_models: Vec<Value>,
    #[serde(default)]
    pub reasoning_effort: Option<String>,
    #[serde(default)]
    pub command_dir: Option<String>,
    #[serde(default)]
    pub enabled: Option<bool>,
    #[serde(default)]
    pub command: Option<String>,
    #[serde(default)]
    pub endpoint: Option<String>,
    #[serde(default)]
    pub sandbox: Option<String>,
    #[serde(default)]
    pub format: Option<String>,
    #[serde(default)]
    pub timeout_seconds: Option<i64>,
    #[serde(default)]
    pub max_retries: Option<i64>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct AgentHealth {
    #[serde(default)]
    pub agent_id: String,
    #[serde(default)]
    pub available: bool,
    #[serde(default)]
    pub version: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
    #[serde(default)]
    pub response_time_ms: Option<f64>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct AgentMetrics {
    #[serde(default)]
    pub agent_id: String,
    #[serde(default)]
    pub active_steps: i64,
    #[serde(default)]
    pub completed_steps: i64,
    #[serde(default)]
    pub failed_steps: i64,
    #[serde(default)]
    pub total_steps: i64,
    #[serde(default)]
    pub last_activity_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct AgentAssignment {
    #[serde(default)]
    pub agent_id: Option<String>,
    #[serde(default)]
    pub prompt_id: Option<String>,
    #[serde(default)]
    pub model_override: Option<String>,
    #[serde(default)]
    pub enabled: Option<bool>,
    #[serde(default)]
    pub metadata: Option<Value>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct AgentAssignments {
    #[serde(default)]
    pub assignments: BTreeMap<String, AgentAssignment>,
    #[serde(default)]
    pub inherit_global: Option<bool>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct AgentPromptTemplate {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub path: String,
    #[serde(default)]
    pub kind: Option<String>,
    #[serde(default)]
    pub engine_id: Option<String>,
    #[serde(default)]
    pub model: Option<String>,
    #[serde(default)]
    pub tags: Option<Vec<String>>,
    #[serde(default)]
    pub enabled: Option<bool>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub source: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct AgentTestCheck {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub ok: bool,
    #[serde(default)]
    pub error: Option<String>,
    #[serde(default)]
    pub details: Value,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct AgentTestResult {
    #[serde(default)]
    pub agent_id: String,
    #[serde(default)]
    pub ok: bool,
    #[serde(default)]
    pub checks: Vec<AgentTestCheck>,
    #[serde(default)]
    pub duration_ms: Option<f64>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ActivityItem {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub action: String,
    #[serde(default)]
    pub target: String,
    #[serde(default)]
    pub time: String,
    #[serde(default)]
    pub icon: String,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct UserProfile {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub email: String,
    #[serde(default)]
    pub role: String,
    #[serde(default)]
    pub member_since: String,
    #[serde(default)]
    pub activity: Vec<ActivityItem>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct DeleteResponse {
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub project_id: Option<i64>,
}

fn default_policy_enforcement_mode() -> String {
    "warn".to_string()
}
