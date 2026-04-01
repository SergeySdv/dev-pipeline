use crate::models::{
    AgentAssignments, AgentHealth, AgentInfo, AgentMetrics, AgentPromptTemplate, AgentTestResult,
    Artifact, ArtifactContent, BrownfieldRun, DeleteResponse, EffectivePolicy, Event, FeedbackList,
    JobRun, MetricsSummary, PolicyFinding, PolicyPack, Project, ProjectBranch,
    ProjectClarification, ProjectCommit, ProjectOnboardingSummary, ProjectPolicy,
    ProjectPullRequest, ProjectSpec, ProjectSpecificationsList, ProjectWorktree, ProtocolArtifact,
    ProtocolRun, ProtocolSpec, QualityDashboard, QualitySummary, QueueJob, SpecKitAnalyzeResult,
    SpecKitChecklistResult, SpecKitClarifyResult, SpecKitCleanupResult, SpecKitImplementResult,
    SpecKitInitResult, SpecKitPlanResult, SpecKitSpecifyResult, SpecKitTasksResult,
    SpecificationContent, StepRun, UserProfile,
};
use anyhow::Result;
use reqwest::StatusCode;
use serde::de::DeserializeOwned;
use serde_json::Value;
use std::time::Duration;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ApiError {
    #[error("http error {status}: {message}")]
    Http { status: StatusCode, message: String },
    #[error("transport error: {0}")]
    Transport(#[from] reqwest::Error),
    #[error("unexpected response shape")]
    Unexpected,
}

#[derive(Clone)]
pub struct ApiClient {
    base_url: String,
    token: Option<String>,
    project_token: Option<String>,
    client: reqwest::Client,
}

impl ApiClient {
    pub fn new(
        base_url: String,
        token: Option<String>,
        project_token: Option<String>,
    ) -> Result<Self> {
        let client = reqwest::Client::builder()
            .connect_timeout(Duration::from_secs(3))
            .timeout(Duration::from_secs(10))
            .build()?;
        Ok(Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            token,
            project_token,
            client,
        })
    }

    fn auth_headers(&self) -> reqwest::header::HeaderMap {
        let mut headers = reqwest::header::HeaderMap::new();
        if let Some(token) = &self.token {
            if let Ok(val) = format!("Bearer {token}").parse() {
                headers.insert(reqwest::header::AUTHORIZATION, val);
            }
        }
        if let Some(token) = &self.project_token {
            if let Ok(val) = token.parse() {
                headers.insert("X-Project-Token", val);
            }
        }
        headers
    }

    async fn get<T: DeserializeOwned>(&self, path: &str) -> Result<T, ApiError> {
        let url = if path.starts_with("http") {
            path.to_string()
        } else {
            format!("{}/{}", self.base_url, path.trim_start_matches('/'))
        };
        let resp = self
            .client
            .get(url)
            .headers(self.auth_headers())
            .send()
            .await
            .map_err(ApiError::Transport)?;
        if !resp.status().is_success() {
            let status = resp.status();
            let message = resp
                .text()
                .await
                .unwrap_or_else(|_| "request failed".to_string());
            return Err(ApiError::Http { status, message });
        }
        resp.json::<T>().await.map_err(|_| ApiError::Unexpected)
    }

    async fn post_json<T: DeserializeOwned>(
        &self,
        path: &str,
        payload: Value,
    ) -> Result<T, ApiError> {
        let url = if path.starts_with("http") {
            path.to_string()
        } else {
            format!("{}/{}", self.base_url, path.trim_start_matches('/'))
        };
        let resp = self
            .client
            .post(url)
            .headers(self.auth_headers())
            .json(&payload)
            .send()
            .await
            .map_err(ApiError::Transport)?;
        if !resp.status().is_success() {
            let status = resp.status();
            let message = resp
                .text()
                .await
                .unwrap_or_else(|_| "request failed".to_string());
            return Err(ApiError::Http { status, message });
        }
        resp.json::<T>().await.map_err(|_| ApiError::Unexpected)
    }

    async fn delete<T: DeserializeOwned>(&self, path: &str) -> Result<T, ApiError> {
        let url = if path.starts_with("http") {
            path.to_string()
        } else {
            format!("{}/{}", self.base_url, path.trim_start_matches('/'))
        };
        let resp = self
            .client
            .delete(url)
            .headers(self.auth_headers())
            .send()
            .await
            .map_err(ApiError::Transport)?;
        if !resp.status().is_success() {
            let status = resp.status();
            let message = resp
                .text()
                .await
                .unwrap_or_else(|_| "request failed".to_string());
            return Err(ApiError::Http { status, message });
        }
        resp.json::<T>().await.map_err(|_| ApiError::Unexpected)
    }

    async fn put_json<T: DeserializeOwned>(
        &self,
        path: &str,
        payload: Value,
    ) -> Result<T, ApiError> {
        let url = if path.starts_with("http") {
            path.to_string()
        } else {
            format!("{}/{}", self.base_url, path.trim_start_matches('/'))
        };
        let resp = self
            .client
            .put(url)
            .headers(self.auth_headers())
            .json(&payload)
            .send()
            .await
            .map_err(ApiError::Transport)?;
        if !resp.status().is_success() {
            let status = resp.status();
            let message = resp
                .text()
                .await
                .unwrap_or_else(|_| "request failed".to_string());
            return Err(ApiError::Http { status, message });
        }
        resp.json::<T>().await.map_err(|_| ApiError::Unexpected)
    }

    pub async fn projects(&self) -> Result<Vec<Project>, ApiError> {
        self.get("/projects").await
    }

    pub async fn project(&self, project_id: i64) -> Result<Project, ApiError> {
        self.get(&format!("/projects/{project_id}")).await
    }

    pub async fn protocols(&self, project_id: i64) -> Result<Vec<ProtocolRun>, ApiError> {
        self.get(&format!("/projects/{project_id}/protocols")).await
    }

    pub async fn protocol(&self, protocol_id: i64) -> Result<ProtocolRun, ApiError> {
        self.get(&format!("/protocols/{protocol_id}")).await
    }

    pub async fn steps(&self, protocol_id: i64) -> Result<Vec<StepRun>, ApiError> {
        self.get(&format!("/protocols/{protocol_id}/steps")).await
    }

    pub async fn step(&self, step_id: i64) -> Result<StepRun, ApiError> {
        self.get(&format!("/steps/{step_id}")).await
    }

    pub async fn events(&self, protocol_id: i64) -> Result<Vec<Event>, ApiError> {
        self.get(&format!("/protocols/{protocol_id}/events")).await
    }

    pub async fn recent_events(&self, limit: u32) -> Result<Vec<Event>, ApiError> {
        self.get(&format!("/events?limit={limit}")).await
    }

    pub async fn queue_stats(&self) -> Result<Value, ApiError> {
        self.get("/queues").await
    }

    pub async fn queue_jobs(&self, status: Option<&str>) -> Result<Vec<QueueJob>, ApiError> {
        let path = match status {
            Some(s) => format!("/queues/jobs?status={s}"),
            None => "/queues/jobs".to_string(),
        };
        self.get(&path).await
    }

    pub async fn branches(&self, project_id: i64) -> Result<Vec<ProjectBranch>, ApiError> {
        self.get(&format!("/projects/{project_id}/branches")).await
    }

    pub async fn project_specs(&self, project_id: i64) -> Result<Vec<ProjectSpec>, ApiError> {
        let response: ProjectSpecificationsList = self
            .get(&format!(
                "/specifications?project_id={project_id}&limit=100"
            ))
            .await?;
        Ok(response.items)
    }

    pub async fn specification_content(
        &self,
        spec_id: i64,
    ) -> Result<SpecificationContent, ApiError> {
        self.get(&format!("/specifications/{spec_id}/content"))
            .await
    }

    pub async fn project_policy(&self, project_id: i64) -> Result<ProjectPolicy, ApiError> {
        self.get(&format!("/projects/{project_id}/policy")).await
    }

    pub async fn project_effective_policy(
        &self,
        project_id: i64,
    ) -> Result<EffectivePolicy, ApiError> {
        self.get(&format!("/projects/{project_id}/policy/effective"))
            .await
    }

    pub async fn project_policy_findings(
        &self,
        project_id: i64,
    ) -> Result<Vec<PolicyFinding>, ApiError> {
        self.get(&format!("/projects/{project_id}/policy/findings"))
            .await
    }

    pub async fn project_clarifications(
        &self,
        project_id: i64,
    ) -> Result<Vec<ProjectClarification>, ApiError> {
        self.get(&format!(
            "/projects/{project_id}/clarifications?status=open"
        ))
        .await
    }

    pub async fn project_commits(&self, project_id: i64) -> Result<Vec<ProjectCommit>, ApiError> {
        self.get(&format!("/projects/{project_id}/commits?limit=20"))
            .await
    }

    pub async fn project_pulls(
        &self,
        project_id: i64,
    ) -> Result<Vec<ProjectPullRequest>, ApiError> {
        self.get(&format!("/projects/{project_id}/pulls")).await
    }

    pub async fn project_worktrees(
        &self,
        project_id: i64,
    ) -> Result<Vec<ProjectWorktree>, ApiError> {
        self.get(&format!("/projects/{project_id}/worktrees")).await
    }

    pub async fn project_onboarding(
        &self,
        project_id: i64,
    ) -> Result<ProjectOnboardingSummary, ApiError> {
        self.get(&format!("/projects/{project_id}/onboarding"))
            .await
    }

    pub async fn archive_project(&self, project_id: i64) -> Result<Project, ApiError> {
        self.post_json(&format!("/projects/{project_id}/archive"), Value::Null)
            .await
    }

    pub async fn unarchive_project(&self, project_id: i64) -> Result<Project, ApiError> {
        self.post_json(&format!("/projects/{project_id}/unarchive"), Value::Null)
            .await
    }

    pub async fn delete_project(&self, project_id: i64) -> Result<DeleteResponse, ApiError> {
        self.delete(&format!("/projects/{project_id}")).await
    }

    pub async fn protocol_runs(&self, protocol_id: i64) -> Result<Vec<JobRun>, ApiError> {
        self.get(&format!("/protocols/{protocol_id}/runs")).await
    }

    pub async fn protocol_spec(&self, protocol_id: i64) -> Result<ProtocolSpec, ApiError> {
        self.get(&format!("/protocols/{protocol_id}/spec")).await
    }

    pub async fn protocol_artifacts(
        &self,
        protocol_id: i64,
    ) -> Result<Vec<ProtocolArtifact>, ApiError> {
        self.get(&format!("/protocols/{protocol_id}/artifacts"))
            .await
    }

    pub async fn protocol_quality(&self, protocol_id: i64) -> Result<QualitySummary, ApiError> {
        self.get(&format!("/protocols/{protocol_id}/quality")).await
    }

    pub async fn protocol_feedback(&self, protocol_id: i64) -> Result<FeedbackList, ApiError> {
        self.get(&format!("/protocols/{protocol_id}/feedback"))
            .await
    }

    pub async fn protocol_clarifications(
        &self,
        protocol_id: i64,
    ) -> Result<Vec<ProjectClarification>, ApiError> {
        self.get(&format!("/protocols/{protocol_id}/clarifications"))
            .await
    }

    pub async fn protocol_policy_findings(
        &self,
        protocol_id: i64,
    ) -> Result<Vec<PolicyFinding>, ApiError> {
        self.get(&format!("/protocols/{protocol_id}/policy/findings"))
            .await
    }

    pub async fn protocol_policy_snapshot(
        &self,
        protocol_id: i64,
    ) -> Result<EffectivePolicy, ApiError> {
        self.get(&format!("/protocols/{protocol_id}/policy/snapshot"))
            .await
    }

    pub async fn step_runs(&self, step_id: i64) -> Result<Vec<JobRun>, ApiError> {
        self.get(&format!("/steps/{step_id}/runs")).await
    }

    pub async fn step_artifacts(&self, step_id: i64) -> Result<Vec<Artifact>, ApiError> {
        self.get(&format!("/steps/{step_id}/artifacts")).await
    }

    pub async fn step_quality(&self, step_id: i64) -> Result<QualitySummary, ApiError> {
        self.get(&format!("/steps/{step_id}/quality")).await
    }

    pub async fn step_policy_findings(&self, step_id: i64) -> Result<Vec<PolicyFinding>, ApiError> {
        self.get(&format!("/steps/{step_id}/policy/findings")).await
    }

    pub async fn runs(
        &self,
        protocol_id: Option<i64>,
        step_id: Option<i64>,
        status: Option<&str>,
    ) -> Result<Vec<JobRun>, ApiError> {
        let mut params = vec!["limit=100".to_string()];
        if let Some(protocol_id) = protocol_id {
            params.push(format!("protocol_run_id={protocol_id}"));
        }
        if let Some(step_id) = step_id {
            params.push(format!("step_run_id={step_id}"));
        }
        if let Some(status) = status {
            params.push(format!("status={status}"));
        }
        self.get(&format!("/runs?{}", params.join("&"))).await
    }

    pub async fn run(&self, run_id: &str) -> Result<JobRun, ApiError> {
        self.get(&format!("/runs/{run_id}")).await
    }

    pub async fn run_logs(&self, run_id: &str) -> Result<ArtifactContent, ApiError> {
        self.get(&format!("/runs/{run_id}/logs")).await
    }

    pub async fn run_artifacts(&self, run_id: &str) -> Result<Vec<Artifact>, ApiError> {
        self.get(&format!("/runs/{run_id}/artifacts")).await
    }

    pub async fn quality_dashboard(&self) -> Result<QualityDashboard, ApiError> {
        self.get("/quality/dashboard").await
    }

    pub async fn metrics_summary(&self) -> Result<MetricsSummary, ApiError> {
        self.get("/metrics/summary").await
    }

    pub async fn policy_packs(&self) -> Result<Vec<PolicyPack>, ApiError> {
        self.get("/policy_packs").await
    }

    pub async fn policy_pack(&self, key: &str) -> Result<PolicyPack, ApiError> {
        self.get(&format!("/policy_packs/{key}")).await
    }

    pub async fn agents(&self, project_id: Option<i64>) -> Result<Vec<AgentInfo>, ApiError> {
        let path = match project_id {
            Some(project_id) => format!("/agents?project_id={project_id}"),
            None => "/agents".to_string(),
        };
        self.get(&path).await
    }

    pub async fn agent(
        &self,
        agent_id: &str,
        project_id: Option<i64>,
    ) -> Result<AgentInfo, ApiError> {
        let path = match project_id {
            Some(project_id) => format!("/agents/{agent_id}?project_id={project_id}"),
            None => format!("/agents/{agent_id}"),
        };
        self.get(&path).await
    }

    pub async fn agent_health(&self) -> Result<Vec<AgentHealth>, ApiError> {
        self.get("/agents/health").await
    }

    pub async fn agent_metrics(
        &self,
        project_id: Option<i64>,
    ) -> Result<Vec<AgentMetrics>, ApiError> {
        let path = match project_id {
            Some(project_id) => format!("/agents/metrics?project_id={project_id}"),
            None => "/agents/metrics".to_string(),
        };
        self.get(&path).await
    }

    pub async fn agent_assignments(
        &self,
        project_id: Option<i64>,
    ) -> Result<AgentAssignments, ApiError> {
        let path = match project_id {
            Some(project_id) => format!("/agents/assignments?project_id={project_id}"),
            None => "/agents/assignments".to_string(),
        };
        self.get(&path).await
    }

    pub async fn update_agent_assignments(
        &self,
        assignments: &AgentAssignments,
        project_id: Option<i64>,
    ) -> Result<AgentAssignments, ApiError> {
        let path = match project_id {
            Some(project_id) => format!("/projects/{project_id}/agents/assignments"),
            None => "/agents/assignments".to_string(),
        };
        let payload = serde_json::to_value(assignments).map_err(|_| ApiError::Unexpected)?;
        self.put_json(&path, payload).await
    }

    pub async fn update_agent_config(
        &self,
        agent_id: &str,
        payload: Value,
        project_id: Option<i64>,
    ) -> Result<AgentInfo, ApiError> {
        let path = match project_id {
            Some(project_id) => format!("/agents/projects/{project_id}/agents/{agent_id}"),
            None => format!("/agents/{agent_id}/config"),
        };
        self.put_json(&path, payload).await
    }

    pub async fn agent_prompts(
        &self,
        project_id: Option<i64>,
    ) -> Result<Vec<AgentPromptTemplate>, ApiError> {
        let path = match project_id {
            Some(project_id) => format!("/agents/prompts?project_id={project_id}"),
            None => "/agents/prompts".to_string(),
        };
        self.get(&path).await
    }

    pub async fn agent_test(&self, agent_id: &str) -> Result<AgentTestResult, ApiError> {
        self.post_json(&format!("/agents/{agent_id}/test"), serde_json::json!({}))
            .await
    }

    pub async fn profile(&self) -> Result<UserProfile, ApiError> {
        self.get("/profile").await
    }

    pub async fn speckit_init(&self, project_id: i64) -> Result<SpecKitInitResult, ApiError> {
        self.post_json(
            &format!("/projects/{project_id}/speckit/init"),
            serde_json::json!({}),
        )
        .await
    }

    pub async fn speckit_specify(
        &self,
        project_id: i64,
        description: &str,
        feature_name: Option<String>,
        base_branch: Option<String>,
    ) -> Result<SpecKitSpecifyResult, ApiError> {
        self.post_json(
            &format!("/projects/{project_id}/speckit/specify"),
            serde_json::json!({
                "description": description,
                "feature_name": feature_name,
                "base_branch": base_branch,
            }),
        )
        .await
    }

    pub async fn speckit_plan(
        &self,
        project_id: i64,
        spec_path: &str,
        spec_run_id: Option<i64>,
        context: Option<String>,
    ) -> Result<SpecKitPlanResult, ApiError> {
        self.post_json(
            &format!("/projects/{project_id}/speckit/plan"),
            serde_json::json!({
                "spec_path": spec_path,
                "spec_run_id": spec_run_id,
                "context": context,
            }),
        )
        .await
    }

    pub async fn speckit_tasks(
        &self,
        project_id: i64,
        plan_path: &str,
        spec_run_id: Option<i64>,
    ) -> Result<SpecKitTasksResult, ApiError> {
        self.post_json(
            &format!("/projects/{project_id}/speckit/tasks"),
            serde_json::json!({
                "plan_path": plan_path,
                "spec_run_id": spec_run_id,
            }),
        )
        .await
    }

    pub async fn speckit_clarify(
        &self,
        project_id: i64,
        spec_path: &str,
        spec_run_id: Option<i64>,
        notes: Option<String>,
    ) -> Result<SpecKitClarifyResult, ApiError> {
        self.post_json(
            &format!("/projects/{project_id}/speckit/clarify"),
            serde_json::json!({
                "spec_path": spec_path,
                "entries": [],
                "notes": notes,
                "spec_run_id": spec_run_id,
            }),
        )
        .await
    }

    pub async fn speckit_checklist(
        &self,
        project_id: i64,
        spec_path: &str,
        spec_run_id: Option<i64>,
    ) -> Result<SpecKitChecklistResult, ApiError> {
        self.post_json(
            &format!("/projects/{project_id}/speckit/checklist"),
            serde_json::json!({
                "spec_path": spec_path,
                "spec_run_id": spec_run_id,
            }),
        )
        .await
    }

    pub async fn speckit_analyze(
        &self,
        project_id: i64,
        spec_path: &str,
        plan_path: Option<String>,
        tasks_path: Option<String>,
        spec_run_id: Option<i64>,
    ) -> Result<SpecKitAnalyzeResult, ApiError> {
        self.post_json(
            &format!("/projects/{project_id}/speckit/analyze"),
            serde_json::json!({
                "spec_path": spec_path,
                "plan_path": plan_path,
                "tasks_path": tasks_path,
                "spec_run_id": spec_run_id,
            }),
        )
        .await
    }

    pub async fn speckit_implement(
        &self,
        project_id: i64,
        spec_path: &str,
        spec_run_id: Option<i64>,
    ) -> Result<SpecKitImplementResult, ApiError> {
        self.post_json(
            &format!("/projects/{project_id}/speckit/implement"),
            serde_json::json!({
                "spec_path": spec_path,
                "spec_run_id": spec_run_id,
            }),
        )
        .await
    }

    pub async fn speckit_cleanup(
        &self,
        spec_run_id: i64,
        delete_remote_branch: bool,
    ) -> Result<SpecKitCleanupResult, ApiError> {
        self.post_json(
            &format!("/speckit/spec-runs/{spec_run_id}/cleanup"),
            serde_json::json!({
                "delete_remote_branch": delete_remote_branch,
            }),
        )
        .await
    }

    pub async fn delete_branch(&self, project_id: i64, branch: &str) -> Result<Value, ApiError> {
        let payload = serde_json::json!({ "confirm": true });
        self.post_json(
            &format!("/projects/{project_id}/branches/{branch}/delete"),
            payload,
        )
        .await
    }

    pub async fn create_project(
        &self,
        name: &str,
        git_url: &str,
        base_branch: &str,
    ) -> Result<Project, ApiError> {
        let payload = serde_json::json!({
            "name": name,
            "git_url": git_url,
            "base_branch": base_branch,
        });
        self.post_json("/projects", payload).await
    }

    pub async fn create_protocol(
        &self,
        project_id: i64,
        protocol_name: &str,
        base_branch: &str,
        description: Option<String>,
    ) -> Result<ProtocolRun, ApiError> {
        let payload = serde_json::json!({
            "protocol_name": protocol_name,
            "base_branch": base_branch,
            "description": description,
            "status": "pending",
        });
        self.post_json(&format!("/projects/{project_id}/protocols"), payload)
            .await
    }

    pub async fn protocol_action(&self, protocol_id: i64, action: &str) -> Result<Value, ApiError> {
        self.post_json(
            &format!("/protocols/{protocol_id}/actions/{action}"),
            Value::Null,
        )
        .await
    }

    pub async fn protocol_open_pr(&self, protocol_id: i64) -> Result<Value, ApiError> {
        self.post_json(
            &format!("/protocols/{protocol_id}/actions/open_pr"),
            Value::Null,
        )
        .await
    }

    pub async fn step_run_next(&self, protocol_id: i64) -> Result<Value, ApiError> {
        self.post_json(
            &format!("/protocols/{protocol_id}/actions/run_next_step"),
            Value::Null,
        )
        .await
    }

    pub async fn step_retry_latest(&self, protocol_id: i64) -> Result<Value, ApiError> {
        self.post_json(
            &format!("/protocols/{protocol_id}/actions/retry_latest"),
            Value::Null,
        )
        .await
    }

    pub async fn step_run_qa(&self, step_id: i64) -> Result<Value, ApiError> {
        self.post_json(&format!("/steps/{step_id}/actions/qa"), Value::Null)
            .await
    }

    pub async fn step_approve(&self, step_id: i64) -> Result<Value, ApiError> {
        self.post_json(&format!("/steps/{step_id}/actions/approve"), Value::Null)
            .await
    }

    pub async fn spec_audit(
        &self,
        project_id: Option<i64>,
        protocol_id: Option<i64>,
        backfill: bool,
        interval_seconds: Option<i64>,
    ) -> Result<Value, ApiError> {
        let payload = serde_json::json!({
            "project_id": project_id,
            "protocol_id": protocol_id,
            "backfill": backfill,
            "interval_seconds": interval_seconds,
        });
        self.post_json("/specs/audit", payload).await
    }

    pub async fn import_codemachine(
        &self,
        project_id: i64,
        protocol_name: &str,
        workspace_path: &str,
        base_branch: &str,
        description: Option<String>,
        enqueue: bool,
    ) -> Result<Value, ApiError> {
        let payload = serde_json::json!({
            "protocol_name": protocol_name,
            "workspace_path": workspace_path,
            "base_branch": base_branch,
            "description": description,
            "enqueue": enqueue,
        });
        self.post_json(
            &format!("/projects/{project_id}/codemachine/import"),
            payload,
        )
        .await
    }

    pub async fn start_brownfield_run(
        &self,
        project_id: i64,
        feature_request: &str,
        feature_name: Option<String>,
        owner_agent: Option<String>,
    ) -> Result<BrownfieldRun, ApiError> {
        self.post_json(
            &format!("/projects/{project_id}/brownfield/run"),
            serde_json::json!({
                "feature_request": feature_request,
                "feature_name": feature_name,
                "output_mode": "task_cycle",
                "owner_agent": owner_agent,
                "helper_agents": [],
                "allow_helper_agents": false,
            }),
        )
        .await
    }

    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    pub fn has_token(&self) -> bool {
        self.token.is_some()
    }

    pub fn has_project_token(&self) -> bool {
        self.project_token.is_some()
    }
}
