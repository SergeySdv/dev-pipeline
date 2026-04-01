use super::App;
use crate::{
    api::{ApiClient, ApiError},
    models::{
        AgentAssignments, AgentHealth, AgentInfo, AgentMetrics, AgentPromptTemplate,
        EffectivePolicy, Event, FeedbackEvent, JobRun, MetricsSummary, PolicyFinding, PolicyPack,
        Project, ProjectBranch, ProjectClarification, ProjectCommit, ProjectOnboardingSummary,
        ProjectPolicy, ProjectPullRequest, ProjectSpec, ProjectWorktree, ProtocolArtifact,
        ProtocolRun, ProtocolSpec, QualityDashboard, QualitySummary, QueueJob,
        SpecificationContent, StepRun, UserProfile,
    },
    state::Page,
};
use anyhow::Result;
use serde_json::Value;
#[derive(Debug)]
pub(crate) enum BackgroundRequest {
    ProjectWorkspace {
        project_id: i64,
        selected_spec_id: Option<i64>,
        fetch_commits: bool,
        fetch_branches: bool,
    },
    ProtocolWorkspace {
        protocol_id: i64,
        step_filter: Option<String>,
    },
    StepWorkspace {
        step_id: i64,
    },
    RunWorkspace {
        run_id: String,
    },
    QualityDashboard,
    PolicyPacks {
        selected_key: Option<String>,
    },
    PolicyPackDetail {
        key: String,
    },
    AgentsPage {
        project_id: Option<i64>,
        selected_agent_id: Option<String>,
    },
    AgentDetail {
        project_id: Option<i64>,
        agent_id: String,
    },
    EventsPage {
        protocol_id: Option<i64>,
    },
    QueuesPage {
        status_filter: Option<String>,
    },
    Settings,
}

#[derive(Debug)]
pub(crate) struct BackgroundResult {
    request_id: u64,
    update: BackgroundUpdate,
}

#[derive(Debug)]
enum BackgroundUpdate {
    ProjectWorkspace(ProjectWorkspaceData),
    ProtocolWorkspace(ProtocolWorkspaceData),
    StepWorkspace(StepWorkspaceData),
    RunWorkspace(RunWorkspaceData),
    QualityDashboard(QualityDashboardData),
    PolicyPacks(PolicyPacksData),
    PolicyPackDetail(PolicyPackDetailData),
    AgentsPage(AgentsPageData),
    AgentDetail(AgentDetailData),
    EventsPage(EventsPageData),
    QueuesPage(QueuesPageData),
    Settings(SettingsData),
}

#[derive(Debug, Default)]
struct ProjectWorkspaceData {
    project_detail: Option<Project>,
    project_specs: Option<Vec<ProjectSpec>>,
    project_spec_content: Option<SpecificationContent>,
    project_policy: Option<ProjectPolicy>,
    project_effective_policy: Option<EffectivePolicy>,
    project_policy_findings: Option<Vec<PolicyFinding>>,
    project_clarifications: Option<Vec<ProjectClarification>>,
    project_commits: Option<Vec<ProjectCommit>>,
    project_commits_supported: Option<bool>,
    project_pulls: Option<Vec<ProjectPullRequest>>,
    project_worktrees: Option<Vec<ProjectWorktree>>,
    project_onboarding: Option<ProjectOnboardingSummary>,
    branches: Option<Vec<ProjectBranch>>,
    project_branches_supported: Option<bool>,
    notices: Vec<String>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct ProtocolWorkspaceData {
    steps: Option<Vec<StepRun>>,
    events: Option<Vec<crate::models::Event>>,
    protocol_detail: Option<ProtocolRun>,
    protocol_runs: Option<Vec<JobRun>>,
    protocol_spec: Option<ProtocolSpec>,
    protocol_artifacts: Option<Vec<ProtocolArtifact>>,
    protocol_quality: Option<QualitySummary>,
    protocol_policy_snapshot: Option<EffectivePolicy>,
    protocol_policy_findings: Option<Vec<PolicyFinding>>,
    protocol_clarifications: Option<Vec<ProjectClarification>>,
    protocol_feedback: Option<Vec<FeedbackEvent>>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct StepWorkspaceData {
    step_detail: Option<StepRun>,
    step_runs: Option<Vec<JobRun>>,
    step_artifacts: Option<Vec<crate::models::Artifact>>,
    step_quality: Option<QualitySummary>,
    step_policy_findings: Option<Vec<PolicyFinding>>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct RunWorkspaceData {
    run_detail: Option<JobRun>,
    run_logs: Option<crate::models::ArtifactContent>,
    run_artifacts: Option<Vec<crate::models::Artifact>>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct QualityDashboardData {
    quality_dashboard: Option<QualityDashboard>,
    metrics_summary: Option<MetricsSummary>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct PolicyPacksData {
    policy_packs: Option<Vec<PolicyPack>>,
    policy_pack_detail: Option<PolicyPack>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct PolicyPackDetailData {
    policy_pack_detail: Option<PolicyPack>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct AgentsPageData {
    agents: Option<Vec<AgentInfo>>,
    agent_detail: Option<AgentInfo>,
    agent_health: Option<Vec<AgentHealth>>,
    agent_metrics: Option<Vec<AgentMetrics>>,
    agent_assignments: Option<AgentAssignments>,
    agent_prompts: Option<Vec<AgentPromptTemplate>>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct AgentDetailData {
    agent_detail: Option<AgentInfo>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct EventsPageData {
    events: Option<Vec<Event>>,
    recent_events: Option<Vec<Event>>,
    metrics_summary: Option<MetricsSummary>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct QueuesPageData {
    queue_stats: Option<Value>,
    queue_jobs: Option<Vec<QueueJob>>,
    metrics_summary: Option<MetricsSummary>,
    errors: Vec<String>,
}

#[derive(Debug, Default)]
struct SettingsData {
    profile: Option<UserProfile>,
    errors: Vec<String>,
}

impl App {
    pub(crate) fn invalidate_background_requests(&mut self) {
        self.background_request_id = self.background_request_id.wrapping_add(1);
        if let Some(handle) = self.background_handle.take() {
            handle.abort();
        }
    }

    pub(crate) fn apply_background_updates(&mut self) {
        while let Ok(result) = self.background_rx.try_recv() {
            if result.request_id != self.background_request_id {
                continue;
            }
            self.background_handle = None;
            self.state.refreshing = false;
            self.apply_background_update(result.update);
        }
    }

    pub(crate) async fn dispatch_background_refresh(&mut self) -> Result<bool> {
        match self.state.page {
            Page::Projects => {
                self.load_projects().await?;
                self.load_protocols().await?;
                if let Some(project_id) = self.state.selected_project_id() {
                    let request = BackgroundRequest::ProjectWorkspace {
                        project_id,
                        selected_spec_id: self.state.selected_project_spec().map(|spec| spec.id),
                        fetch_commits: self.state.project_commits_supported != Some(false),
                        fetch_branches: self.state.project_branches_supported != Some(false),
                    };
                    self.start_background_request(request, "Loading project workspace...");
                    return Ok(true);
                }
            }
            Page::Protocols => {
                self.load_projects().await?;
                self.load_protocols().await?;
                if let Some(protocol_id) = self.state.selected_protocol_id() {
                    let request = BackgroundRequest::ProtocolWorkspace {
                        protocol_id,
                        step_filter: self.state.step_filter.clone(),
                    };
                    self.start_background_request(request, "Loading protocol workspace...");
                    return Ok(true);
                }
            }
            Page::Steps => {
                self.load_projects().await?;
                if self.state.protocols.is_empty() && self.state.selected_project_id().is_some() {
                    self.load_protocols().await?;
                }
                self.load_steps().await?;
                if let Some(step_id) = self.state.selected_step_id() {
                    self.start_background_request(
                        BackgroundRequest::StepWorkspace { step_id },
                        "Loading step workspace...",
                    );
                    return Ok(true);
                }
            }
            Page::Runs => {
                self.load_projects().await?;
                self.load_runs_page().await?;
                if let Some(run_id) = self.state.selected_run_id().map(str::to_string) {
                    self.start_background_request(
                        BackgroundRequest::RunWorkspace { run_id },
                        "Loading run workspace...",
                    );
                    return Ok(true);
                }
            }
            Page::Quality => {
                self.start_background_request(
                    BackgroundRequest::QualityDashboard,
                    "Loading quality dashboard...",
                );
                return Ok(true);
            }
            Page::Policy => {
                self.start_background_request(
                    BackgroundRequest::PolicyPacks {
                        selected_key: self.state.selected_policy_pack_key().map(str::to_string),
                    },
                    "Loading policy packs...",
                );
                return Ok(true);
            }
            Page::Agents => {
                self.load_projects().await?;
                self.load_chat_agents().await?;
                self.start_background_request(
                    BackgroundRequest::AgentsPage {
                        project_id: self.state.selected_project_id(),
                        selected_agent_id: self.state.selected_agent_id().map(str::to_string),
                    },
                    "Loading agents workspace...",
                );
                return Ok(true);
            }
            Page::Events => {
                self.start_background_request(
                    BackgroundRequest::EventsPage {
                        protocol_id: self.state.selected_protocol_id(),
                    },
                    "Loading events...",
                );
                return Ok(true);
            }
            Page::Queues => {
                self.start_background_request(
                    BackgroundRequest::QueuesPage {
                        status_filter: self.state.job_status_filter.clone(),
                    },
                    "Loading queues...",
                );
                return Ok(true);
            }
            Page::Settings => {
                self.start_background_request(BackgroundRequest::Settings, "Loading settings...");
                return Ok(true);
            }
            _ => {}
        }
        Ok(false)
    }

    pub(crate) async fn dispatch_background_selection_refresh(&mut self) -> Result<bool> {
        match self.state.page {
            Page::Projects => {
                self.load_protocols().await?;
                if let Some(project_id) = self.state.selected_project_id() {
                    self.start_background_request(
                        BackgroundRequest::ProjectWorkspace {
                            project_id,
                            selected_spec_id: self
                                .state
                                .selected_project_spec()
                                .map(|spec| spec.id),
                            fetch_commits: self.state.project_commits_supported != Some(false),
                            fetch_branches: self.state.project_branches_supported != Some(false),
                        },
                        "Updating project workspace...",
                    );
                    return Ok(true);
                }
            }
            Page::Protocols => {
                if let Some(protocol_id) = self.state.selected_protocol_id() {
                    self.start_background_request(
                        BackgroundRequest::ProtocolWorkspace {
                            protocol_id,
                            step_filter: self.state.step_filter.clone(),
                        },
                        "Updating protocol workspace...",
                    );
                    return Ok(true);
                }
            }
            Page::Steps => {
                if let Some(step_id) = self.state.selected_step_id() {
                    self.start_background_request(
                        BackgroundRequest::StepWorkspace { step_id },
                        "Updating step workspace...",
                    );
                    return Ok(true);
                }
            }
            Page::Runs => {
                if let Some(run_id) = self.state.selected_run_id().map(str::to_string) {
                    self.start_background_request(
                        BackgroundRequest::RunWorkspace { run_id },
                        "Updating run workspace...",
                    );
                    return Ok(true);
                }
            }
            Page::Policy => {
                if let Some(key) = self.state.selected_policy_pack_key().map(str::to_string) {
                    self.start_background_request(
                        BackgroundRequest::PolicyPackDetail { key },
                        "Updating policy pack...",
                    );
                    return Ok(true);
                }
            }
            Page::Agents => {
                if let Some(agent_id) = self.state.selected_agent_id().map(str::to_string) {
                    self.start_background_request(
                        BackgroundRequest::AgentDetail {
                            project_id: self.state.selected_project_id(),
                            agent_id,
                        },
                        "Updating agent detail...",
                    );
                    return Ok(true);
                }
            }
            _ => {}
        }
        Ok(false)
    }

    pub(crate) fn start_background_request(&mut self, request: BackgroundRequest, status: &str) {
        self.background_request_id = self.background_request_id.wrapping_add(1);
        if let Some(handle) = self.background_handle.take() {
            handle.abort();
        }
        let request_id = self.background_request_id;
        let client = self.client.clone();
        let tx = self.background_tx.clone();
        self.state.refreshing = true;
        self.state.last_error = None;
        self.state.status = status.to_string();
        self.background_handle = Some(tokio::spawn(async move {
            let update = fetch_background_update(client, request).await;
            let _ = tx.send(BackgroundResult { request_id, update });
        }));
    }

    fn apply_background_update(&mut self, update: BackgroundUpdate) {
        match update {
            BackgroundUpdate::ProjectWorkspace(data) => {
                self.apply_errors(&data.errors);
                if let Some(project) = data.project_detail {
                    self.state.project_detail = Some(project);
                }
                if let Some(specs) = data.project_specs {
                    self.state.project_specs = specs;
                    if self.state.project_specs.is_empty() {
                        self.state.project_spec_index = None;
                        self.state.project_spec_content = None;
                    } else if self
                        .state
                        .project_spec_index
                        .map(|idx| idx >= self.state.project_specs.len())
                        .unwrap_or(true)
                    {
                        self.state.project_spec_index = Some(0);
                    }
                }
                if let Some(content) = data.project_spec_content {
                    self.state.project_spec_content = Some(content);
                }
                if let Some(policy) = data.project_policy {
                    self.state.project_policy = Some(policy);
                }
                if let Some(policy) = data.project_effective_policy {
                    self.state.project_effective_policy = Some(policy);
                }
                if let Some(findings) = data.project_policy_findings {
                    self.state.project_policy_findings = findings;
                }
                if let Some(clarifications) = data.project_clarifications {
                    self.state.project_clarifications = clarifications;
                }
                if let Some(commits) = data.project_commits {
                    self.state.project_commits = commits;
                }
                if let Some(supported) = data.project_commits_supported {
                    self.state.project_commits_supported = Some(supported);
                    if !supported {
                        self.state.project_commits.clear();
                    }
                }
                if let Some(pulls) = data.project_pulls {
                    self.state.project_pulls = pulls;
                }
                if let Some(worktrees) = data.project_worktrees {
                    self.state.project_worktrees = worktrees;
                }
                if let Some(onboarding) = data.project_onboarding {
                    self.state.project_onboarding = Some(onboarding);
                }
                if let Some(branches) = data.branches {
                    self.state.branches = branches;
                    if self.state.branches.is_empty() {
                        self.state.branch_index = None;
                    } else if self
                        .state
                        .branch_index
                        .map(|idx| idx >= self.state.branches.len())
                        .unwrap_or(true)
                    {
                        self.state.branch_index = Some(0);
                    }
                }
                if let Some(supported) = data.project_branches_supported {
                    self.state.project_branches_supported = Some(supported);
                    if !supported {
                        self.state.branches.clear();
                        self.state.branch_index = None;
                    }
                }
                if let Some(notice) = data.notices.last() {
                    self.state.status = notice.clone();
                } else {
                    self.state.status = "Project workspace loaded".into();
                }
            }
            BackgroundUpdate::ProtocolWorkspace(data) => {
                self.apply_errors(&data.errors);
                if let Some(steps) = data.steps {
                    self.state.steps = steps;
                    if self.state.steps.is_empty() {
                        self.state.step_index = None;
                        self.state.clear_step_workspace();
                    } else if self
                        .state
                        .step_index
                        .map(|idx| idx >= self.state.steps.len())
                        .unwrap_or(true)
                    {
                        self.state.step_index = Some(self.state.steps.len() - 1);
                    }
                }
                if let Some(events) = data.events {
                    self.state.events = events;
                    if self.state.events.is_empty() {
                        self.state.event_index = None;
                    } else if self
                        .state
                        .event_index
                        .map(|idx| idx >= self.state.events.len())
                        .unwrap_or(true)
                    {
                        self.state.event_index = Some(self.state.events.len() - 1);
                    }
                }
                if let Some(protocol) = data.protocol_detail {
                    self.state.protocol_detail = Some(protocol);
                }
                if let Some(runs) = data.protocol_runs {
                    self.state.protocol_runs = runs;
                }
                if let Some(spec) = data.protocol_spec {
                    self.state.protocol_spec = Some(spec);
                }
                if let Some(artifacts) = data.protocol_artifacts {
                    self.state.protocol_artifacts = artifacts;
                }
                if let Some(quality) = data.protocol_quality {
                    self.state.protocol_quality = Some(quality);
                }
                if let Some(policy) = data.protocol_policy_snapshot {
                    self.state.protocol_policy_snapshot = Some(policy);
                }
                if let Some(findings) = data.protocol_policy_findings {
                    self.state.protocol_policy_findings = findings;
                }
                if let Some(clarifications) = data.protocol_clarifications {
                    self.state.protocol_clarifications = clarifications;
                }
                if let Some(feedback) = data.protocol_feedback {
                    self.state.protocol_feedback = feedback;
                }
                self.state.status = "Protocol workspace loaded".into();
            }
            BackgroundUpdate::StepWorkspace(data) => {
                self.apply_errors(&data.errors);
                if let Some(step) = data.step_detail {
                    self.state.step_detail = Some(step);
                }
                if let Some(runs) = data.step_runs {
                    self.state.step_runs = runs;
                }
                if let Some(artifacts) = data.step_artifacts {
                    self.state.step_artifacts = artifacts;
                }
                if let Some(quality) = data.step_quality {
                    self.state.step_quality = Some(quality);
                }
                if let Some(findings) = data.step_policy_findings {
                    self.state.step_policy_findings = findings;
                }
                self.state.status = "Step workspace loaded".into();
            }
            BackgroundUpdate::RunWorkspace(data) => {
                self.apply_errors(&data.errors);
                if let Some(run) = data.run_detail {
                    self.state.run_detail = Some(run);
                }
                if let Some(logs) = data.run_logs {
                    self.state.run_logs = Some(logs);
                }
                if let Some(artifacts) = data.run_artifacts {
                    self.state.run_artifacts = artifacts;
                }
                self.state.status = "Run workspace loaded".into();
            }
            BackgroundUpdate::QualityDashboard(data) => {
                self.apply_errors(&data.errors);
                if let Some(dashboard) = data.quality_dashboard {
                    self.state.quality_dashboard = Some(dashboard);
                }
                if let Some(summary) = data.metrics_summary {
                    self.state.metrics_summary = Some(summary);
                }
                self.state.status = "Quality dashboard loaded".into();
            }
            BackgroundUpdate::PolicyPacks(data) => {
                self.apply_errors(&data.errors);
                if let Some(packs) = data.policy_packs {
                    self.state.policy_packs = packs;
                    if self.state.policy_packs.is_empty() {
                        self.state.policy_pack_index = None;
                        self.state.policy_pack_detail = None;
                    } else if self
                        .state
                        .policy_pack_index
                        .map(|idx| idx >= self.state.policy_packs.len())
                        .unwrap_or(true)
                    {
                        self.state.policy_pack_index = Some(0);
                    }
                }
                if let Some(pack) = data.policy_pack_detail {
                    self.state.policy_pack_detail = Some(pack);
                }
                self.state.status = "Policy packs loaded".into();
            }
            BackgroundUpdate::PolicyPackDetail(data) => {
                self.apply_errors(&data.errors);
                if let Some(pack) = data.policy_pack_detail {
                    self.state.policy_pack_detail = Some(pack);
                }
                self.state.status = "Policy pack loaded".into();
            }
            BackgroundUpdate::AgentsPage(data) => {
                self.apply_errors(&data.errors);
                if let Some(agents) = data.agents {
                    self.state.agents = agents;
                    if self.state.agents.is_empty() {
                        self.state.agent_index = None;
                        self.state.agent_detail = None;
                    } else if self
                        .state
                        .agent_index
                        .map(|idx| idx >= self.state.agents.len())
                        .unwrap_or(true)
                    {
                        self.state.agent_index = Some(0);
                    }
                }
                if let Some(agent) = data.agent_detail {
                    self.state.agent_detail = Some(agent);
                }
                if let Some(health) = data.agent_health {
                    self.state.agent_health = health;
                }
                if let Some(metrics) = data.agent_metrics {
                    self.state.agent_metrics = metrics;
                }
                if let Some(assignments) = data.agent_assignments {
                    self.state.agent_assignments = Some(assignments);
                }
                if let Some(prompts) = data.agent_prompts {
                    self.state.agent_prompts = prompts;
                }
                self.state.status = "Agents workspace loaded".into();
            }
            BackgroundUpdate::AgentDetail(data) => {
                self.apply_errors(&data.errors);
                if let Some(agent) = data.agent_detail {
                    self.state.agent_detail = Some(agent);
                }
                self.state.status = "Agent detail loaded".into();
            }
            BackgroundUpdate::EventsPage(data) => {
                self.apply_errors(&data.errors);
                if let Some(events) = data.events {
                    self.state.events = events;
                    if self.state.events.is_empty() {
                        self.state.event_index = None;
                    } else if self
                        .state
                        .event_index
                        .map(|idx| idx >= self.state.events.len())
                        .unwrap_or(true)
                    {
                        self.state.event_index = Some(self.state.events.len() - 1);
                    }
                }
                if let Some(recent_events) = data.recent_events {
                    self.state.recent_events = recent_events;
                    if self.state.recent_events.is_empty() {
                        self.state.recent_event_index = None;
                    } else if self
                        .state
                        .recent_event_index
                        .map(|idx| idx >= self.state.recent_events.len())
                        .unwrap_or(true)
                    {
                        self.state.recent_event_index = Some(0);
                    }
                }
                if let Some(summary) = data.metrics_summary {
                    self.state.metrics_summary = Some(summary);
                }
                self.state.status = "Events loaded".into();
            }
            BackgroundUpdate::QueuesPage(data) => {
                self.apply_errors(&data.errors);
                if let Some(queue_stats) = data.queue_stats {
                    self.state.queue_stats = queue_stats;
                }
                if let Some(queue_jobs) = data.queue_jobs {
                    self.state.queue_jobs = queue_jobs;
                    if self.state.queue_jobs.is_empty() {
                        self.state.queue_job_index = None;
                    } else if self
                        .state
                        .queue_job_index
                        .map(|idx| idx >= self.state.queue_jobs.len())
                        .unwrap_or(true)
                    {
                        self.state.queue_job_index = Some(0);
                    }
                }
                if let Some(summary) = data.metrics_summary {
                    self.state.metrics_summary = Some(summary);
                }
                self.state.status = "Queues loaded".into();
            }
            BackgroundUpdate::Settings(data) => {
                self.apply_errors(&data.errors);
                if let Some(profile) = data.profile {
                    self.state.profile = Some(profile);
                }
                self.state.status = "Settings loaded".into();
            }
        }
    }

    fn apply_errors(&mut self, errors: &[String]) {
        if let Some(last) = errors.last() {
            self.state.last_error = Some(last.clone());
        }
    }
}

async fn fetch_background_update(
    client: ApiClient,
    request: BackgroundRequest,
) -> BackgroundUpdate {
    match request {
        BackgroundRequest::ProjectWorkspace {
            project_id,
            selected_spec_id,
            fetch_commits,
            fetch_branches,
        } => BackgroundUpdate::ProjectWorkspace(
            fetch_project_workspace(
                client,
                project_id,
                selected_spec_id,
                fetch_commits,
                fetch_branches,
            )
            .await,
        ),
        BackgroundRequest::ProtocolWorkspace {
            protocol_id,
            step_filter,
        } => BackgroundUpdate::ProtocolWorkspace(
            fetch_protocol_workspace(client, protocol_id, step_filter).await,
        ),
        BackgroundRequest::StepWorkspace { step_id } => {
            BackgroundUpdate::StepWorkspace(fetch_step_workspace(client, step_id).await)
        }
        BackgroundRequest::RunWorkspace { run_id } => {
            BackgroundUpdate::RunWorkspace(fetch_run_workspace(client, &run_id).await)
        }
        BackgroundRequest::QualityDashboard => {
            BackgroundUpdate::QualityDashboard(fetch_quality_dashboard(client).await)
        }
        BackgroundRequest::PolicyPacks { selected_key } => {
            BackgroundUpdate::PolicyPacks(fetch_policy_packs(client, selected_key).await)
        }
        BackgroundRequest::PolicyPackDetail { key } => {
            BackgroundUpdate::PolicyPackDetail(fetch_policy_pack_detail(client, &key).await)
        }
        BackgroundRequest::AgentsPage {
            project_id,
            selected_agent_id,
        } => BackgroundUpdate::AgentsPage(
            fetch_agents_page(client, project_id, selected_agent_id.as_deref()).await,
        ),
        BackgroundRequest::AgentDetail {
            project_id,
            agent_id,
        } => BackgroundUpdate::AgentDetail(fetch_agent_detail(client, project_id, &agent_id).await),
        BackgroundRequest::EventsPage { protocol_id } => {
            BackgroundUpdate::EventsPage(fetch_events_page(client, protocol_id).await)
        }
        BackgroundRequest::QueuesPage { status_filter } => {
            BackgroundUpdate::QueuesPage(fetch_queues_page(client, status_filter.as_deref()).await)
        }
        BackgroundRequest::Settings => BackgroundUpdate::Settings(fetch_settings(client).await),
    }
}

async fn fetch_project_workspace(
    client: ApiClient,
    project_id: i64,
    selected_spec_id: Option<i64>,
    fetch_commits: bool,
    fetch_branches: bool,
) -> ProjectWorkspaceData {
    let mut data = ProjectWorkspaceData::default();
    let (
        project_res,
        specs_res,
        project_policy_res,
        effective_policy_res,
        findings_res,
        clarifications_res,
        commits_res,
        pulls_res,
        worktrees_res,
        onboarding_res,
        branches_res,
    ) = tokio::join!(
        client.project(project_id),
        client.project_specs(project_id),
        client.project_policy(project_id),
        client.project_effective_policy(project_id),
        client.project_policy_findings(project_id),
        client.project_clarifications(project_id),
        async {
            if fetch_commits {
                Some(client.project_commits(project_id).await)
            } else {
                None
            }
        },
        client.project_pulls(project_id),
        client.project_worktrees(project_id),
        client.project_onboarding(project_id),
        async {
            if fetch_branches {
                Some(client.branches(project_id).await)
            } else {
                None
            }
        },
    );
    match project_res {
        Ok(project) => data.project_detail = Some(project),
        Err(err) => data.errors.push(err.to_string()),
    }
    match specs_res {
        Ok(specs) => data.project_specs = Some(specs),
        Err(err) => data.errors.push(err.to_string()),
    }
    match project_policy_res {
        Ok(policy) => data.project_policy = Some(policy),
        Err(err) => data.errors.push(err.to_string()),
    }
    match effective_policy_res {
        Ok(policy) => data.project_effective_policy = Some(policy),
        Err(err) => data.errors.push(err.to_string()),
    }
    match findings_res {
        Ok(findings) => data.project_policy_findings = Some(findings),
        Err(err) => data.errors.push(err.to_string()),
    }
    match clarifications_res {
        Ok(clarifications) => data.project_clarifications = Some(clarifications),
        Err(err) => data.errors.push(err.to_string()),
    }
    match commits_res {
        Some(Ok(commits)) => {
            data.project_commits = Some(commits);
            data.project_commits_supported = Some(true);
        }
        Some(Err(ApiError::Http { status, .. })) if status == reqwest::StatusCode::BAD_REQUEST => {
            data.project_commits_supported = Some(false);
            data.notices
                .push("Project commits endpoint unavailable on this backend".into());
        }
        Some(Err(err)) => data.errors.push(err.to_string()),
        None => {}
    }
    match pulls_res {
        Ok(pulls) => data.project_pulls = Some(pulls),
        Err(err) => data.errors.push(err.to_string()),
    }
    match worktrees_res {
        Ok(worktrees) => data.project_worktrees = Some(worktrees),
        Err(err) => data.errors.push(err.to_string()),
    }
    match onboarding_res {
        Ok(onboarding) => data.project_onboarding = Some(onboarding),
        Err(err) => data.errors.push(err.to_string()),
    }
    match branches_res {
        Some(Ok(branches)) => {
            data.branches = Some(branches);
            data.project_branches_supported = Some(true);
        }
        Some(Err(ApiError::Http { status, .. })) if status == reqwest::StatusCode::BAD_REQUEST => {
            data.project_branches_supported = Some(false);
            data.notices
                .push("Project branches endpoint unavailable on this backend".into());
        }
        Some(Err(err)) => data.errors.push(err.to_string()),
        None => {}
    }
    if let Some(spec_id) = selected_spec_id {
        match client.specification_content(spec_id).await {
            Ok(content) => data.project_spec_content = Some(content),
            Err(err) => data.errors.push(err.to_string()),
        }
    }
    data
}

async fn fetch_protocol_workspace(
    client: ApiClient,
    protocol_id: i64,
    step_filter: Option<String>,
) -> ProtocolWorkspaceData {
    let mut data = ProtocolWorkspaceData::default();
    let (
        steps_res,
        events_res,
        protocol_res,
        runs_res,
        spec_res,
        artifacts_res,
        quality_res,
        policy_snapshot_res,
        policy_findings_res,
        clarifications_res,
        feedback_res,
    ) = tokio::join!(
        client.steps(protocol_id),
        client.events(protocol_id),
        client.protocol(protocol_id),
        client.protocol_runs(protocol_id),
        client.protocol_spec(protocol_id),
        client.protocol_artifacts(protocol_id),
        client.protocol_quality(protocol_id),
        client.protocol_policy_snapshot(protocol_id),
        client.protocol_policy_findings(protocol_id),
        client.protocol_clarifications(protocol_id),
        client.protocol_feedback(protocol_id),
    );
    match steps_res {
        Ok(steps) => {
            data.steps = Some(
                steps
                    .into_iter()
                    .filter(|step| {
                        step_filter
                            .as_ref()
                            .map(|f| &step.status == f)
                            .unwrap_or(true)
                    })
                    .collect(),
            );
        }
        Err(err) => data.errors.push(err.to_string()),
    }
    match events_res {
        Ok(events) => data.events = Some(events),
        Err(err) => data.errors.push(err.to_string()),
    }
    match protocol_res {
        Ok(protocol) => data.protocol_detail = Some(protocol),
        Err(err) => data.errors.push(err.to_string()),
    }
    match runs_res {
        Ok(runs) => data.protocol_runs = Some(runs),
        Err(err) => data.errors.push(err.to_string()),
    }
    match spec_res {
        Ok(spec) => data.protocol_spec = Some(spec),
        Err(err) => data.errors.push(err.to_string()),
    }
    match artifacts_res {
        Ok(artifacts) => data.protocol_artifacts = Some(artifacts),
        Err(err) => data.errors.push(err.to_string()),
    }
    match quality_res {
        Ok(quality) => data.protocol_quality = Some(quality),
        Err(err) => data.errors.push(err.to_string()),
    }
    match policy_snapshot_res {
        Ok(policy) => data.protocol_policy_snapshot = Some(policy),
        Err(err) => data.errors.push(err.to_string()),
    }
    match policy_findings_res {
        Ok(findings) => data.protocol_policy_findings = Some(findings),
        Err(err) => data.errors.push(err.to_string()),
    }
    match clarifications_res {
        Ok(clarifications) => data.protocol_clarifications = Some(clarifications),
        Err(err) => data.errors.push(err.to_string()),
    }
    match feedback_res {
        Ok(feedback) => data.protocol_feedback = Some(feedback.events),
        Err(err) => data.errors.push(err.to_string()),
    }
    data
}

async fn fetch_step_workspace(client: ApiClient, step_id: i64) -> StepWorkspaceData {
    let mut data = StepWorkspaceData::default();
    let (step_res, runs_res, artifacts_res, quality_res, policy_findings_res) = tokio::join!(
        client.step(step_id),
        client.step_runs(step_id),
        client.step_artifacts(step_id),
        client.step_quality(step_id),
        client.step_policy_findings(step_id),
    );
    match step_res {
        Ok(step) => data.step_detail = Some(step),
        Err(err) => data.errors.push(err.to_string()),
    }
    match runs_res {
        Ok(runs) => data.step_runs = Some(runs),
        Err(err) => data.errors.push(err.to_string()),
    }
    match artifacts_res {
        Ok(artifacts) => data.step_artifacts = Some(artifacts),
        Err(err) => data.errors.push(err.to_string()),
    }
    match quality_res {
        Ok(quality) => data.step_quality = Some(quality),
        Err(err) => data.errors.push(err.to_string()),
    }
    match policy_findings_res {
        Ok(findings) => data.step_policy_findings = Some(findings),
        Err(err) => data.errors.push(err.to_string()),
    }
    data
}

async fn fetch_run_workspace(client: ApiClient, run_id: &str) -> RunWorkspaceData {
    let mut data = RunWorkspaceData::default();
    let (run_res, logs_res, artifacts_res) = tokio::join!(
        client.run(run_id),
        client.run_logs(run_id),
        client.run_artifacts(run_id),
    );
    match run_res {
        Ok(run) => data.run_detail = Some(run),
        Err(err) => data.errors.push(err.to_string()),
    }
    match logs_res {
        Ok(logs) => data.run_logs = Some(logs),
        Err(err) => data.errors.push(err.to_string()),
    }
    match artifacts_res {
        Ok(artifacts) => data.run_artifacts = Some(artifacts),
        Err(err) => data.errors.push(err.to_string()),
    }
    data
}

async fn fetch_quality_dashboard(client: ApiClient) -> QualityDashboardData {
    let mut data = QualityDashboardData::default();
    let (quality_res, metrics_res) =
        tokio::join!(client.quality_dashboard(), client.metrics_summary());
    match quality_res {
        Ok(dashboard) => data.quality_dashboard = Some(dashboard),
        Err(err) => data.errors.push(err.to_string()),
    }
    match metrics_res {
        Ok(summary) => data.metrics_summary = Some(summary),
        Err(err) => data.errors.push(err.to_string()),
    }
    data
}

async fn fetch_policy_packs(client: ApiClient, selected_key: Option<String>) -> PolicyPacksData {
    let mut data = PolicyPacksData::default();
    match client.policy_packs().await {
        Ok(packs) => data.policy_packs = Some(packs),
        Err(err) => data.errors.push(err.to_string()),
    }
    if let Some(key) = selected_key {
        match client.policy_pack(&key).await {
            Ok(pack) => data.policy_pack_detail = Some(pack),
            Err(err) => data.errors.push(err.to_string()),
        }
    }
    data
}

async fn fetch_policy_pack_detail(client: ApiClient, key: &str) -> PolicyPackDetailData {
    let mut data = PolicyPackDetailData::default();
    match client.policy_pack(key).await {
        Ok(pack) => data.policy_pack_detail = Some(pack),
        Err(err) => data.errors.push(err.to_string()),
    }
    data
}

async fn fetch_agents_page(
    client: ApiClient,
    project_id: Option<i64>,
    selected_agent_id: Option<&str>,
) -> AgentsPageData {
    let mut data = AgentsPageData::default();
    let (agents_res, health_res, metrics_res, assignments_res, prompts_res) = tokio::join!(
        client.agents(project_id),
        client.agent_health(),
        client.agent_metrics(project_id),
        client.agent_assignments(project_id),
        client.agent_prompts(project_id),
    );
    match agents_res {
        Ok(agents) => data.agents = Some(agents),
        Err(err) => data.errors.push(err.to_string()),
    }
    match health_res {
        Ok(health) => data.agent_health = Some(health),
        Err(err) => data.errors.push(err.to_string()),
    }
    match metrics_res {
        Ok(metrics) => data.agent_metrics = Some(metrics),
        Err(err) => data.errors.push(err.to_string()),
    }
    match assignments_res {
        Ok(assignments) => data.agent_assignments = Some(assignments),
        Err(err) => data.errors.push(err.to_string()),
    }
    match prompts_res {
        Ok(prompts) => data.agent_prompts = Some(prompts),
        Err(err) => data.errors.push(err.to_string()),
    }
    if let Some(agent_id) = selected_agent_id {
        match client.agent(agent_id, project_id).await {
            Ok(agent) => data.agent_detail = Some(agent),
            Err(err) => data.errors.push(err.to_string()),
        }
    }
    data
}

async fn fetch_agent_detail(
    client: ApiClient,
    project_id: Option<i64>,
    agent_id: &str,
) -> AgentDetailData {
    let mut data = AgentDetailData::default();
    match client.agent(agent_id, project_id).await {
        Ok(agent) => data.agent_detail = Some(agent),
        Err(err) => data.errors.push(err.to_string()),
    }
    data
}

async fn fetch_settings(client: ApiClient) -> SettingsData {
    let mut data = SettingsData::default();
    match client.profile().await {
        Ok(profile) => data.profile = Some(profile),
        Err(err) => data.errors.push(err.to_string()),
    }
    data
}

async fn fetch_events_page(client: ApiClient, protocol_id: Option<i64>) -> EventsPageData {
    let mut data = EventsPageData::default();
    let (events_res, recent_events_res, metrics_res) = tokio::join!(
        async {
            if let Some(protocol_id) = protocol_id {
                Some(client.events(protocol_id).await)
            } else {
                None
            }
        },
        client.recent_events(50),
        client.metrics_summary(),
    );

    match events_res {
        Some(Ok(events)) => data.events = Some(events),
        Some(Err(err)) => data.errors.push(err.to_string()),
        None => data.events = Some(Vec::new()),
    }
    match recent_events_res {
        Ok(events) => data.recent_events = Some(events),
        Err(err) => data.errors.push(err.to_string()),
    }
    match metrics_res {
        Ok(summary) => data.metrics_summary = Some(summary),
        Err(err) => data.errors.push(err.to_string()),
    }
    data
}

async fn fetch_queues_page(client: ApiClient, status_filter: Option<&str>) -> QueuesPageData {
    let mut data = QueuesPageData::default();
    let (stats_res, jobs_res, metrics_res) = tokio::join!(
        client.queue_stats(),
        client.queue_jobs(status_filter),
        client.metrics_summary(),
    );

    match stats_res {
        Ok(stats) => data.queue_stats = Some(stats),
        Err(err) => data.errors.push(err.to_string()),
    }
    match jobs_res {
        Ok(jobs) => data.queue_jobs = Some(jobs),
        Err(err) => data.errors.push(err.to_string()),
    }
    match metrics_res {
        Ok(summary) => data.metrics_summary = Some(summary),
        Err(err) => data.errors.push(err.to_string()),
    }
    data
}
