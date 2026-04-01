use crate::models::{
    AgentAssignments, AgentHealth, AgentInfo, AgentMetrics, AgentPromptTemplate, AgentTestResult,
    Artifact, ArtifactContent, BrownfieldRun, EffectivePolicy, Event, FeedbackEvent, JobRun,
    MetricsSummary, PolicyFinding, PolicyPack, Project, ProjectBranch, ProjectClarification,
    ProjectCommit, ProjectOnboardingSummary, ProjectPolicy, ProjectPullRequest, ProjectSpec,
    ProjectWorktree, ProtocolArtifact, ProtocolRun, ProtocolSpec, QualityDashboard, QualitySummary,
    QueueJob, SpecificationContent, StepRun, UserProfile,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Page {
    Chat,
    Dashboard,
    Projects,
    Protocols,
    Steps,
    Runs,
    Quality,
    Policy,
    Agents,
    Events,
    Queues,
    Settings,
}

impl Default for Page {
    fn default() -> Self {
        Page::Chat
    }
}

impl Page {
    pub fn next(self) -> Self {
        match self {
            Page::Chat => Page::Dashboard,
            Page::Dashboard => Page::Projects,
            Page::Projects => Page::Protocols,
            Page::Protocols => Page::Steps,
            Page::Steps => Page::Runs,
            Page::Runs => Page::Quality,
            Page::Quality => Page::Policy,
            Page::Policy => Page::Agents,
            Page::Agents => Page::Events,
            Page::Events => Page::Queues,
            Page::Queues => Page::Settings,
            Page::Settings => Page::Chat,
        }
    }

    pub fn prev(self) -> Self {
        match self {
            Page::Chat => Page::Settings,
            Page::Dashboard => Page::Chat,
            Page::Projects => Page::Dashboard,
            Page::Protocols => Page::Projects,
            Page::Steps => Page::Protocols,
            Page::Runs => Page::Steps,
            Page::Quality => Page::Runs,
            Page::Policy => Page::Quality,
            Page::Agents => Page::Policy,
            Page::Events => Page::Agents,
            Page::Queues => Page::Events,
            Page::Settings => Page::Queues,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ChatMessageKind {
    User,
    Agent,
    Flow,
    Step,
    Tool,
    Check,
    Warn,
}

#[derive(Debug, Clone, Default)]
pub struct ChatMessage {
    pub kind: Option<ChatMessageKind>,
    pub text: String,
}

#[derive(Debug, Clone, Default)]
pub struct ChatFlowState {
    pub kind: String,
    pub label: String,
    pub status: String,
    pub stage: Option<String>,
    pub protocol_id: Option<i64>,
    pub step_id: Option<i64>,
    pub run_id: Option<String>,
    pub summary: Option<String>,
    pub last_tool: Option<String>,
    pub artifact_hint: Option<String>,
    pub waiting_on: Option<String>,
    pub operator_hint: Option<String>,
    pub last_event: Option<String>,
    pub updated_at: Option<String>,
}

#[derive(Debug, Default, Clone)]
pub struct AppState {
    pub page: Page,
    pub chat_messages: Vec<ChatMessage>,
    pub composer_input: String,
    pub active_flow: Option<ChatFlowState>,
    pub last_brownfield_run: Option<BrownfieldRun>,
    pub seen_chat_event_keys: Vec<String>,
    pub projects: Vec<Project>,
    pub project_index: Option<usize>,
    pub project_spec_index: Option<usize>,
    pub project_workspace_tab: ProjectWorkspaceTab,
    pub protocol_workspace_tab: ProtocolWorkspaceTab,
    pub step_workspace_tab: StepWorkspaceTab,
    pub settings_tab: SettingsTab,
    pub project_detail: Option<Project>,
    pub project_specs: Vec<ProjectSpec>,
    pub project_spec_content: Option<SpecificationContent>,
    pub project_policy: Option<ProjectPolicy>,
    pub project_effective_policy: Option<EffectivePolicy>,
    pub project_policy_findings: Vec<PolicyFinding>,
    pub project_clarifications: Vec<ProjectClarification>,
    pub project_commits: Vec<ProjectCommit>,
    pub project_commits_supported: Option<bool>,
    pub project_pulls: Vec<ProjectPullRequest>,
    pub project_worktrees: Vec<ProjectWorktree>,
    pub project_onboarding: Option<ProjectOnboardingSummary>,
    pub protocols: Vec<ProtocolRun>,
    pub protocol_index: Option<usize>,
    pub protocol_detail: Option<ProtocolRun>,
    pub protocol_runs: Vec<JobRun>,
    pub protocol_spec: Option<ProtocolSpec>,
    pub protocol_artifacts: Vec<ProtocolArtifact>,
    pub protocol_quality: Option<QualitySummary>,
    pub protocol_policy_snapshot: Option<EffectivePolicy>,
    pub protocol_policy_findings: Vec<PolicyFinding>,
    pub protocol_clarifications: Vec<ProjectClarification>,
    pub protocol_feedback: Vec<FeedbackEvent>,
    pub steps: Vec<StepRun>,
    pub step_index: Option<usize>,
    pub step_filter: Option<String>,
    pub step_detail: Option<StepRun>,
    pub step_runs: Vec<JobRun>,
    pub step_artifacts: Vec<Artifact>,
    pub step_quality: Option<QualitySummary>,
    pub step_policy_findings: Vec<PolicyFinding>,
    pub events: Vec<Event>,
    pub event_index: Option<usize>,
    pub recent_events: Vec<Event>,
    pub recent_event_index: Option<usize>,
    pub event_filter: Option<String>,
    pub queue_stats: Value,
    pub queue_jobs: Vec<QueueJob>,
    pub queue_job_index: Option<usize>,
    pub runs: Vec<JobRun>,
    pub run_index: Option<usize>,
    pub run_detail: Option<JobRun>,
    pub run_logs: Option<ArtifactContent>,
    pub run_artifacts: Vec<Artifact>,
    pub run_status_filter: Option<String>,
    pub quality_dashboard: Option<QualityDashboard>,
    pub metrics_summary: Option<MetricsSummary>,
    pub policy_packs: Vec<PolicyPack>,
    pub policy_pack_index: Option<usize>,
    pub policy_pack_detail: Option<PolicyPack>,
    pub agents: Vec<AgentInfo>,
    pub agent_index: Option<usize>,
    pub agent_detail: Option<AgentInfo>,
    pub agent_health: Vec<AgentHealth>,
    pub agent_metrics: Vec<AgentMetrics>,
    pub agent_assignments: Option<AgentAssignments>,
    pub agent_prompts: Vec<AgentPromptTemplate>,
    pub agent_test_result: Option<AgentTestResult>,
    pub profile: Option<UserProfile>,
    pub branches: Vec<ProjectBranch>,
    pub branch_index: Option<usize>,
    pub project_branches_supported: Option<bool>,
    pub global_query: Option<String>,
    pub search_scope: SearchScope,
    pub search_results: Vec<SearchResult>,
    pub saved_filters: Vec<SavedFilter>,
    pub external_action_result: Option<String>,
    pub job_status_filter: Option<String>,
    pub stream_paused: bool,
    pub status: String,
    pub last_error: Option<String>,
    pub refreshing: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SearchScope {
    All,
    Projects,
    Specs,
    Protocols,
    Steps,
    Runs,
    Events,
    Queues,
    Policy,
    Agents,
}

#[derive(Debug, Clone, Default)]
pub struct SearchResult {
    pub scope: SearchScope,
    pub label: String,
    pub detail: String,
    pub project_index: Option<usize>,
    pub project_spec_index: Option<usize>,
    pub protocol_index: Option<usize>,
    pub step_index: Option<usize>,
    pub run_index: Option<usize>,
    pub policy_pack_index: Option<usize>,
    pub agent_index: Option<usize>,
    pub event_index: Option<usize>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SavedFilter {
    pub name: String,
    pub scope: SearchScope,
    pub query: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProjectWorkspaceTab {
    Summary,
    Specs,
    Branches,
    Clarifications,
    Policy,
    Settings,
    Onboarding,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProtocolWorkspaceTab {
    Summary,
    Steps,
    Runs,
    Events,
    Quality,
    Policy,
    Clarify,
    Spec,
    Artifacts,
    Feedback,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StepWorkspaceTab {
    Summary,
    Runs,
    Artifacts,
    Quality,
    Policy,
    Runtime,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SettingsTab {
    Connection,
    Profile,
}

impl Default for ProjectWorkspaceTab {
    fn default() -> Self {
        Self::Summary
    }
}

impl Default for SearchScope {
    fn default() -> Self {
        Self::All
    }
}

impl SearchScope {
    pub fn label(self) -> &'static str {
        match self {
            Self::All => "all",
            Self::Projects => "projects",
            Self::Specs => "specs",
            Self::Protocols => "protocols",
            Self::Steps => "steps",
            Self::Runs => "runs",
            Self::Events => "events",
            Self::Queues => "queues",
            Self::Policy => "policy",
            Self::Agents => "agents",
        }
    }

    pub fn from_input(value: &str) -> Self {
        match value.trim().to_ascii_lowercase().as_str() {
            "projects" | "project" => Self::Projects,
            "specs" | "spec" => Self::Specs,
            "protocols" | "protocol" => Self::Protocols,
            "steps" | "step" => Self::Steps,
            "runs" | "run" => Self::Runs,
            "events" | "event" => Self::Events,
            "queues" | "queue" | "jobs" => Self::Queues,
            "policy" | "policies" => Self::Policy,
            "agents" | "agent" => Self::Agents,
            _ => Self::All,
        }
    }
}

impl ProjectWorkspaceTab {
    pub fn next(self) -> Self {
        match self {
            Self::Summary => Self::Specs,
            Self::Specs => Self::Branches,
            Self::Branches => Self::Clarifications,
            Self::Clarifications => Self::Policy,
            Self::Policy => Self::Settings,
            Self::Settings => Self::Onboarding,
            Self::Onboarding => Self::Summary,
        }
    }

    pub fn prev(self) -> Self {
        match self {
            Self::Summary => Self::Onboarding,
            Self::Specs => Self::Summary,
            Self::Branches => Self::Specs,
            Self::Clarifications => Self::Branches,
            Self::Policy => Self::Clarifications,
            Self::Settings => Self::Policy,
            Self::Onboarding => Self::Settings,
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            Self::Summary => "summary",
            Self::Specs => "specs",
            Self::Branches => "branches",
            Self::Clarifications => "clarify",
            Self::Policy => "policy",
            Self::Settings => "settings",
            Self::Onboarding => "onboarding",
        }
    }
}

impl Default for ProtocolWorkspaceTab {
    fn default() -> Self {
        Self::Summary
    }
}

impl ProtocolWorkspaceTab {
    pub fn next(self) -> Self {
        match self {
            Self::Summary => Self::Steps,
            Self::Steps => Self::Runs,
            Self::Runs => Self::Events,
            Self::Events => Self::Quality,
            Self::Quality => Self::Policy,
            Self::Policy => Self::Clarify,
            Self::Clarify => Self::Spec,
            Self::Spec => Self::Artifacts,
            Self::Artifacts => Self::Feedback,
            Self::Feedback => Self::Summary,
        }
    }

    pub fn prev(self) -> Self {
        match self {
            Self::Summary => Self::Feedback,
            Self::Steps => Self::Summary,
            Self::Runs => Self::Steps,
            Self::Events => Self::Runs,
            Self::Quality => Self::Events,
            Self::Policy => Self::Quality,
            Self::Clarify => Self::Policy,
            Self::Spec => Self::Clarify,
            Self::Artifacts => Self::Spec,
            Self::Feedback => Self::Artifacts,
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            Self::Summary => "summary",
            Self::Steps => "steps",
            Self::Runs => "runs",
            Self::Events => "events",
            Self::Quality => "quality",
            Self::Policy => "policy",
            Self::Clarify => "clarify",
            Self::Spec => "spec",
            Self::Artifacts => "artifacts",
            Self::Feedback => "feedback",
        }
    }
}

impl Default for StepWorkspaceTab {
    fn default() -> Self {
        Self::Summary
    }
}

impl StepWorkspaceTab {
    pub fn next(self) -> Self {
        match self {
            Self::Summary => Self::Runs,
            Self::Runs => Self::Artifacts,
            Self::Artifacts => Self::Quality,
            Self::Quality => Self::Policy,
            Self::Policy => Self::Runtime,
            Self::Runtime => Self::Summary,
        }
    }

    pub fn prev(self) -> Self {
        match self {
            Self::Summary => Self::Runtime,
            Self::Runs => Self::Summary,
            Self::Artifacts => Self::Runs,
            Self::Quality => Self::Artifacts,
            Self::Policy => Self::Quality,
            Self::Runtime => Self::Policy,
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            Self::Summary => "summary",
            Self::Runs => "runs",
            Self::Artifacts => "artifacts",
            Self::Quality => "quality",
            Self::Policy => "policy",
            Self::Runtime => "runtime",
        }
    }
}

impl Default for SettingsTab {
    fn default() -> Self {
        Self::Connection
    }
}

impl SettingsTab {
    pub fn next(self) -> Self {
        match self {
            Self::Connection => Self::Profile,
            Self::Profile => Self::Connection,
        }
    }

    pub fn prev(self) -> Self {
        self.next()
    }

    pub fn label(self) -> &'static str {
        match self {
            Self::Connection => "connection",
            Self::Profile => "profile",
        }
    }
}

impl AppState {
    pub fn push_chat_message(&mut self, kind: ChatMessageKind, text: impl Into<String>) {
        self.chat_messages.push(ChatMessage {
            kind: Some(kind),
            text: text.into(),
        });
        if self.chat_messages.len() > 200 {
            let overflow = self.chat_messages.len().saturating_sub(200);
            self.chat_messages.drain(0..overflow);
        }
    }

    pub fn select_project_by_id(&mut self, project_id: i64) {
        self.project_index = self
            .projects
            .iter()
            .position(|project| project.id == project_id);
    }

    pub fn select_project(&mut self, delta: i32) {
        self.project_index = move_index(self.project_index, self.projects.len(), delta);
    }

    pub fn select_protocol(&mut self, delta: i32) {
        self.protocol_index = move_index(self.protocol_index, self.protocols.len(), delta);
    }

    pub fn select_protocol_by_id(&mut self, protocol_id: i64) {
        self.protocol_index = self
            .protocols
            .iter()
            .position(|protocol| protocol.id == protocol_id);
    }

    pub fn select_project_spec(&mut self, delta: i32) {
        self.project_spec_index =
            move_index(self.project_spec_index, self.project_specs.len(), delta);
    }

    pub fn select_step(&mut self, delta: i32) {
        self.step_index = move_index(self.step_index, self.steps.len(), delta);
    }

    pub fn select_step_by_id(&mut self, step_id: i64) {
        self.step_index = self.steps.iter().position(|step| step.id == step_id);
    }

    pub fn select_run(&mut self, delta: i32) {
        self.run_index = move_index(self.run_index, self.runs.len(), delta);
    }

    pub fn select_policy_pack(&mut self, delta: i32) {
        self.policy_pack_index = move_index(self.policy_pack_index, self.policy_packs.len(), delta);
    }

    pub fn select_agent(&mut self, delta: i32) {
        self.agent_index = move_index(self.agent_index, self.agents.len(), delta);
    }

    pub fn select_agent_by_id(&mut self, agent_id: &str) {
        self.agent_index = self.agents.iter().position(|agent| agent.id == agent_id);
    }

    pub fn selected_project_id(&self) -> Option<i64> {
        self.project_index
            .and_then(|idx| self.projects.get(idx))
            .map(|p| p.id)
    }

    pub fn selected_project(&self) -> Option<&Project> {
        self.project_index.and_then(|idx| self.projects.get(idx))
    }

    pub fn selected_project_spec(&self) -> Option<&ProjectSpec> {
        self.project_spec_index
            .and_then(|idx| self.project_specs.get(idx))
    }

    pub fn selected_protocol_id(&self) -> Option<i64> {
        self.protocol_index
            .and_then(|idx| self.protocols.get(idx))
            .map(|p| p.id)
    }

    pub fn selected_step_id(&self) -> Option<i64> {
        self.step_index
            .and_then(|idx| self.steps.get(idx))
            .map(|s| s.id)
    }

    pub fn selected_run_id(&self) -> Option<&str> {
        self.run_index
            .and_then(|idx| self.runs.get(idx))
            .map(|run| run.run_id.as_str())
    }

    pub fn selected_policy_pack_key(&self) -> Option<&str> {
        self.policy_pack_index
            .and_then(|idx| self.policy_packs.get(idx))
            .map(|pack| pack.key.as_str())
    }

    pub fn selected_agent_id(&self) -> Option<&str> {
        self.agent_index
            .and_then(|idx| self.agents.get(idx))
            .map(|agent| agent.id.as_str())
    }

    pub fn selected_queue_job(&self) -> Option<&QueueJob> {
        self.queue_job_index
            .and_then(|idx| self.queue_jobs.get(idx))
    }

    pub fn select_branch(&mut self, delta: i32) {
        self.branch_index = move_index(self.branch_index, self.branches.len(), delta);
    }

    pub fn select_event(&mut self, delta: i32) {
        self.event_index = move_index(self.event_index, self.events.len(), delta);
    }

    pub fn select_queue_job(&mut self, delta: i32) {
        self.queue_job_index = move_index(self.queue_job_index, self.queue_jobs.len(), delta);
    }

    pub fn clear_project_workspace(&mut self) {
        self.project_detail = None;
        self.project_specs.clear();
        self.project_spec_index = None;
        self.project_spec_content = None;
        self.project_policy = None;
        self.project_effective_policy = None;
        self.project_policy_findings.clear();
        self.project_clarifications.clear();
        self.project_commits.clear();
        self.project_commits_supported = None;
        self.project_pulls.clear();
        self.project_worktrees.clear();
        self.project_onboarding = None;
        self.branches.clear();
        self.branch_index = None;
        self.project_branches_supported = None;
    }

    pub fn clear_protocol_workspace(&mut self) {
        self.protocol_detail = None;
        self.protocol_runs.clear();
        self.protocol_spec = None;
        self.protocol_artifacts.clear();
        self.protocol_quality = None;
        self.protocol_policy_snapshot = None;
        self.protocol_policy_findings.clear();
        self.protocol_clarifications.clear();
        self.protocol_feedback.clear();
    }

    pub fn clear_step_workspace(&mut self) {
        self.step_detail = None;
        self.step_runs.clear();
        self.step_artifacts.clear();
        self.step_quality = None;
        self.step_policy_findings.clear();
    }

    pub fn clear_run_workspace(&mut self) {
        self.run_detail = None;
        self.run_logs = None;
        self.run_artifacts.clear();
    }
}

fn move_index(current: Option<usize>, len: usize, delta: i32) -> Option<usize> {
    if len == 0 {
        return None;
    }
    let idx = current.unwrap_or(0) as i32 + delta;
    let idx = idx.clamp(0, (len as i32) - 1);
    Some(idx as usize)
}
