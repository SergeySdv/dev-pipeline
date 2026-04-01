use super::{App, Screen};
use crate::{api::ApiError, state::Page};
use anyhow::Result;
use tokio::time::Instant;

impl App {
    pub(crate) async fn refresh_selection(&mut self) -> Result<()> {
        if self.screen != Screen::Dashboard {
            return Ok(());
        }
        let start = Instant::now();
        match self.state.page {
            Page::Chat => {
                self.load_chat_page().await?;
            }
            Page::Dashboard | Page::Projects => {
                self.load_protocols().await?;
                if self.state.page == Page::Projects {
                    self.load_project_workspace().await?;
                } else {
                    self.load_steps().await?;
                    self.load_recent_events().await?;
                }
            }
            Page::Protocols => {
                self.load_protocol_workspace().await?;
            }
            Page::Steps => {
                self.load_step_workspace().await?;
            }
            Page::Runs => {
                self.load_run_workspace().await?;
            }
            Page::Quality => {
                self.load_quality_dashboard().await?;
            }
            Page::Policy => {
                self.load_policy_packs().await?;
            }
            Page::Agents => {
                self.load_agents_page().await?;
            }
            Page::Settings => {
                self.load_settings_data().await?;
            }
            _ => {}
        }
        self.state.refreshing = false;
        self.state.status = format!("Selection updated in {}ms", start.elapsed().as_millis());
        Ok(())
    }

    pub async fn refresh_all(&mut self) -> Result<()> {
        if self.screen != Screen::Dashboard {
            return Ok(());
        }
        self.state.refreshing = true;
        self.state.last_error = None;
        self.state.status = "Refreshing...".to_string();
        let start = Instant::now();
        match self.state.page {
            Page::Chat => {
                self.load_chat_page().await?;
            }
            Page::Dashboard => {
                self.load_projects().await?;
                self.load_protocols().await?;
                self.load_steps().await?;
                self.load_recent_events().await?;
            }
            Page::Projects => {
                self.load_projects().await?;
                self.load_protocols().await?;
                self.load_project_workspace().await?;
            }
            Page::Protocols => {
                self.load_projects().await?;
                self.load_protocols().await?;
                self.load_protocol_workspace().await?;
            }
            Page::Steps => {
                self.load_projects().await?;
                self.load_step_workspace().await?;
            }
            Page::Runs => {
                self.load_projects().await?;
                self.load_runs_page().await?;
                self.load_run_workspace().await?;
            }
            Page::Quality => {
                self.load_projects().await?;
                self.load_quality_dashboard().await?;
            }
            Page::Policy => {
                self.load_projects().await?;
                self.load_policy_packs().await?;
            }
            Page::Agents => {
                self.load_projects().await?;
                self.load_agents_page().await?;
            }
            Page::Events => {
                self.load_projects().await?;
                self.load_events().await?;
                self.load_recent_events().await?;
                self.load_metrics_summary().await?;
            }
            Page::Queues => {
                self.load_projects().await?;
                self.load_queue().await?;
                self.load_metrics_summary().await?;
            }
            Page::Settings => {
                self.load_projects().await?;
                self.load_settings_data().await?;
            }
        }
        self.state.refreshing = false;
        self.state.status = format!("Refreshed in {}ms", start.elapsed().as_millis());
        Ok(())
    }

    pub async fn refresh_scoped(&mut self) -> Result<()> {
        if self.screen != Screen::Dashboard {
            return Ok(());
        }
        if !matches!(
            self.state.page,
            Page::Chat | Page::Dashboard | Page::Events | Page::Queues
        ) {
            return Ok(());
        }
        if self.state.page == Page::Chat
            && (!self.state.composer_input.is_empty()
                || self.last_interaction_at.elapsed()
                    < self.refresh_interval.min(std::time::Duration::from_secs(2)))
        {
            self.state.refreshing = false;
            return Ok(());
        }
        if matches!(
            self.state.page,
            Page::Dashboard | Page::Events | Page::Queues
        ) && self.last_interaction_at.elapsed()
            < self.refresh_interval.min(std::time::Duration::from_secs(1))
        {
            self.state.refreshing = false;
            return Ok(());
        }
        if self.state.page == Page::Chat
            && self.state.active_flow.is_none()
            && self.state.selected_run_id().is_none()
        {
            self.state.refreshing = false;
            self.state.status = "Chat idle".to_string();
            return Ok(());
        }
        if self.state.stream_paused && matches!(self.state.page, Page::Events | Page::Queues) {
            self.state.refreshing = false;
            self.state.status = "Stream refresh paused".to_string();
            return Ok(());
        }
        self.state.refreshing = true;
        self.state.last_error = None;
        let start = Instant::now();
        match self.state.page {
            Page::Chat => {
                self.state.status = "Refreshing chat flow...".to_string();
                self.load_recent_events().await?;
                if self.state.protocols.is_empty() && self.state.selected_project_id().is_some() {
                    self.load_protocols().await?;
                }
                if let Some(protocol_id) = self
                    .state
                    .active_flow
                    .as_ref()
                    .and_then(|flow| flow.protocol_id)
                {
                    self.state.select_protocol_by_id(protocol_id);
                }
                if self.state.selected_protocol_id().is_some() {
                    self.load_protocol_workspace().await?;
                }
                if self.state.selected_run_id().is_some() {
                    self.load_run_workspace().await?;
                }
                self.sync_chat_events();
            }
            Page::Dashboard => {
                self.state.status = "Refreshing dashboard feed...".to_string();
                self.load_steps().await?;
                self.load_recent_events().await?;
            }
            Page::Projects => {
                self.state.status = "Refreshing projects...".to_string();
                self.load_projects().await?;
                self.load_protocols().await?;
                self.load_project_workspace().await?;
            }
            Page::Protocols => {
                self.state.status = "Refreshing protocols...".to_string();
                self.load_protocols().await?;
                self.load_protocol_workspace().await?;
            }
            Page::Steps => {
                self.state.status = "Refreshing steps...".to_string();
                self.load_step_workspace().await?;
            }
            Page::Runs => {
                self.state.status = "Refreshing runs...".to_string();
                self.load_runs_page().await?;
                self.load_run_workspace().await?;
            }
            Page::Quality => {
                self.state.status = "Refreshing quality...".to_string();
                self.load_quality_dashboard().await?;
            }
            Page::Policy => {
                self.state.status = "Refreshing policy packs...".to_string();
                self.load_policy_packs().await?;
            }
            Page::Agents => {
                self.state.status = "Refreshing agents...".to_string();
                self.load_agents_page().await?;
            }
            Page::Events => {
                self.state.status = "Refreshing events...".to_string();
                self.load_events().await?;
                self.load_recent_events().await?;
                self.load_metrics_summary().await?;
            }
            Page::Queues => {
                self.state.status = "Refreshing queues...".to_string();
                self.load_queue().await?;
                self.load_metrics_summary().await?;
            }
            Page::Settings => {
                self.state.status = "Refreshing settings...".to_string();
                self.load_settings_data().await?;
            }
        }
        self.state.refreshing = false;
        self.state.status = format!(
            "Refreshed current page in {}ms",
            start.elapsed().as_millis()
        );
        Ok(())
    }

    pub(crate) async fn load_chat_page(&mut self) -> Result<()> {
        self.ensure_chat_seeded();
        self.load_projects().await?;
        if self.state.selected_project_id().is_some() {
            self.load_protocols().await?;
            self.load_chat_agents().await?;
        } else {
            self.state.protocols.clear();
            self.state.protocol_index = None;
            self.state.agents.clear();
            self.state.agent_index = None;
            self.state.agent_detail = None;
        }
        let chat_has_live_context =
            self.state.active_flow.is_some() || self.state.selected_run_id().is_some();
        if chat_has_live_context {
            self.load_recent_events().await?;
            if let Some(protocol_id) = self
                .state
                .active_flow
                .as_ref()
                .and_then(|flow| flow.protocol_id)
            {
                self.state.select_protocol_by_id(protocol_id);
            }
            if self.state.selected_protocol_id().is_some() {
                self.load_protocol_workspace().await?;
            }
        }
        if let Some(step_id) = self
            .state
            .active_flow
            .as_ref()
            .and_then(|flow| flow.step_id)
        {
            self.state.select_step_by_id(step_id);
        }
        if let Some(flow) = self.state.active_flow.as_mut() {
            if let Some(protocol) = self
                .state
                .protocol_detail
                .as_ref()
                .filter(|protocol| Some(protocol.id) == flow.protocol_id)
            {
                if let Some(status) = &protocol.status {
                    flow.status = status.clone();
                }
                if flow.summary.is_none() {
                    flow.summary = protocol.summary.clone();
                }
            }
        }
        if chat_has_live_context && self.state.selected_run_id().is_some() {
            self.load_run_workspace().await?;
        }
        if chat_has_live_context {
            self.sync_chat_events();
        }
        Ok(())
    }

    pub(crate) async fn load_chat_agents(&mut self) -> Result<()> {
        let project_id = self.state.selected_project_id();
        match self.client.agents(project_id).await {
            Ok(agents) => {
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
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_projects(&mut self) -> Result<()> {
        match self.client.projects().await {
            Ok(data) => {
                self.state.projects = data;
                if self.state.projects.is_empty() {
                    self.state.project_index = None;
                    self.state.clear_project_workspace();
                } else if self
                    .state
                    .project_index
                    .map(|idx| idx >= self.state.projects.len())
                    .unwrap_or(true)
                {
                    self.state.project_index = Some(0);
                }
            }
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_project_workspace(&mut self) -> Result<()> {
        let Some(project_id) = self.state.selected_project_id() else {
            self.state.clear_project_workspace();
            return Ok(());
        };

        let client = self.client.clone();
        let fetch_commits = self.state.project_commits_supported != Some(false);
        let fetch_branches = self.state.project_branches_supported != Some(false);
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
            Ok(project) => self.state.project_detail = Some(project),
            Err(err) => self.set_error(err),
        }
        match specs_res {
            Ok(specs) => {
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
            Err(err) => self.set_error(err),
        }
        match project_policy_res {
            Ok(policy) => self.state.project_policy = Some(policy),
            Err(err) => self.set_error(err),
        }
        match effective_policy_res {
            Ok(policy) => self.state.project_effective_policy = Some(policy),
            Err(err) => self.set_error(err),
        }
        match findings_res {
            Ok(findings) => self.state.project_policy_findings = findings,
            Err(err) => self.set_error(err),
        }
        match clarifications_res {
            Ok(clarifications) => self.state.project_clarifications = clarifications,
            Err(err) => self.set_error(err),
        }
        match commits_res {
            Some(Ok(commits)) => {
                self.state.project_commits = commits;
                self.state.project_commits_supported = Some(true);
            }
            Some(Err(ApiError::Http { status, .. }))
                if status == reqwest::StatusCode::BAD_REQUEST =>
            {
                self.state.project_commits_supported = Some(false);
                self.state.project_commits.clear();
                self.state.status = "Project commits endpoint unavailable on this backend".into();
            }
            Some(Err(err)) => self.set_error(err),
            None => {}
        }
        match pulls_res {
            Ok(pulls) => self.state.project_pulls = pulls,
            Err(err) => self.set_error(err),
        }
        match worktrees_res {
            Ok(worktrees) => self.state.project_worktrees = worktrees,
            Err(err) => self.set_error(err),
        }
        match onboarding_res {
            Ok(onboarding) => self.state.project_onboarding = Some(onboarding),
            Err(err) => self.set_error(err),
        }
        match branches_res {
            Some(Ok(branches)) => {
                self.state.branches = branches;
                self.state.project_branches_supported = Some(true);
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
            Some(Err(ApiError::Http { status, .. }))
                if status == reqwest::StatusCode::BAD_REQUEST =>
            {
                self.state.project_branches_supported = Some(false);
                self.state.branches.clear();
                self.state.branch_index = None;
                self.state.status = "Project branches endpoint unavailable on this backend".into();
            }
            Some(Err(err)) => self.set_error(err),
            None => {}
        }

        if let Some(spec_id) = self.state.selected_project_spec().map(|spec| spec.id) {
            match self.client.specification_content(spec_id).await {
                Ok(content) => self.state.project_spec_content = Some(content),
                Err(err) => self.set_error(err),
            }
        }

        Ok(())
    }

    pub(crate) async fn load_protocols(&mut self) -> Result<()> {
        let Some(project_id) = self.state.selected_project_id() else {
            self.state.protocols.clear();
            self.state.protocol_index = None;
            self.state.clear_protocol_workspace();
            return Ok(());
        };
        match self.client.protocols(project_id).await {
            Ok(data) => {
                self.state.protocols = data;
                if self.state.protocols.is_empty() {
                    self.state.protocol_index = None;
                    self.state.clear_protocol_workspace();
                } else if self
                    .state
                    .protocol_index
                    .map(|idx| idx >= self.state.protocols.len())
                    .unwrap_or(true)
                {
                    self.state.protocol_index = Some(0);
                }
            }
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_steps(&mut self) -> Result<()> {
        let Some(protocol_id) = self.state.selected_protocol_id() else {
            self.state.steps.clear();
            self.state.step_index = None;
            self.state.clear_step_workspace();
            return Ok(());
        };
        match self.client.steps(protocol_id).await {
            Ok(data) => {
                self.state.steps = data
                    .into_iter()
                    .filter(|s| {
                        if let Some(filter) = &self.state.step_filter {
                            &s.status == filter
                        } else {
                            true
                        }
                    })
                    .collect();
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
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_events(&mut self) -> Result<()> {
        let Some(protocol_id) = self.state.selected_protocol_id() else {
            self.state.events.clear();
            self.state.event_index = None;
            return Ok(());
        };
        match self.client.events(protocol_id).await {
            Ok(data) => {
                self.state.events = data;
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
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_recent_events(&mut self) -> Result<()> {
        match self.client.recent_events(50).await {
            Ok(data) => {
                self.state.recent_events = data;
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
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_queue(&mut self) -> Result<()> {
        let client = self.client.clone();
        let (stats_res, jobs_res) = tokio::join!(
            client.queue_stats(),
            client.queue_jobs(self.state.job_status_filter.as_deref()),
        );
        match stats_res {
            Ok(data) => self.state.queue_stats = data,
            Err(err) => self.set_error(err),
        }
        match jobs_res {
            Ok(data) => {
                self.state.queue_jobs = data;
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
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_branches(&mut self) -> Result<()> {
        let Some(project_id) = self.state.selected_project_id() else {
            self.state.branches.clear();
            self.state.branch_index = None;
            return Ok(());
        };
        if self.state.project_branches_supported == Some(false) {
            self.state.branches.clear();
            self.state.branch_index = None;
            self.state.status = "Project branches endpoint unavailable on this backend".into();
            return Ok(());
        }
        match self.client.branches(project_id).await {
            Ok(branches) => {
                self.state.branches = branches;
                self.state.project_branches_supported = Some(true);
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
            Err(ApiError::Http { status, .. }) if status == reqwest::StatusCode::BAD_REQUEST => {
                self.state.project_branches_supported = Some(false);
                self.state.branches.clear();
                self.state.branch_index = None;
                self.state.status = "Project branches endpoint unavailable on this backend".into();
            }
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_protocol_workspace(&mut self) -> Result<()> {
        let Some(protocol_id) = self.state.selected_protocol_id() else {
            self.state.clear_protocol_workspace();
            return Ok(());
        };
        let client = self.client.clone();
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
            Ok(data) => {
                self.state.steps = data
                    .into_iter()
                    .filter(|s| {
                        if let Some(filter) = &self.state.step_filter {
                            &s.status == filter
                        } else {
                            true
                        }
                    })
                    .collect();
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
            Err(err) => self.set_error(err),
        }
        match events_res {
            Ok(data) => {
                self.state.events = data;
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
            Err(err) => self.set_error(err),
        }
        match protocol_res {
            Ok(protocol) => self.state.protocol_detail = Some(protocol),
            Err(err) => self.set_error(err),
        }
        match runs_res {
            Ok(runs) => self.state.protocol_runs = runs,
            Err(err) => self.set_error(err),
        }
        match spec_res {
            Ok(spec) => self.state.protocol_spec = Some(spec),
            Err(err) => self.set_error(err),
        }
        match artifacts_res {
            Ok(artifacts) => self.state.protocol_artifacts = artifacts,
            Err(err) => self.set_error(err),
        }
        match quality_res {
            Ok(quality) => self.state.protocol_quality = Some(quality),
            Err(err) => self.set_error(err),
        }
        match policy_snapshot_res {
            Ok(policy) => self.state.protocol_policy_snapshot = Some(policy),
            Err(err) => self.set_error(err),
        }
        match policy_findings_res {
            Ok(findings) => self.state.protocol_policy_findings = findings,
            Err(err) => self.set_error(err),
        }
        match clarifications_res {
            Ok(clarifications) => self.state.protocol_clarifications = clarifications,
            Err(err) => self.set_error(err),
        }
        match feedback_res {
            Ok(feedback) => self.state.protocol_feedback = feedback.events,
            Err(err) => self.set_error(err),
        }

        Ok(())
    }

    pub(crate) async fn load_step_workspace(&mut self) -> Result<()> {
        let Some(step_id) = self.state.selected_step_id() else {
            self.state.clear_step_workspace();
            return Ok(());
        };

        if self.state.protocol_index.is_some() && self.state.steps.is_empty() {
            self.load_steps().await?;
        }

        let client = self.client.clone();
        let (step_res, runs_res, artifacts_res, quality_res, policy_findings_res) = tokio::join!(
            client.step(step_id),
            client.step_runs(step_id),
            client.step_artifacts(step_id),
            client.step_quality(step_id),
            client.step_policy_findings(step_id),
        );

        match step_res {
            Ok(step) => self.state.step_detail = Some(step),
            Err(err) => self.set_error(err),
        }
        match runs_res {
            Ok(runs) => self.state.step_runs = runs,
            Err(err) => self.set_error(err),
        }
        match artifacts_res {
            Ok(artifacts) => self.state.step_artifacts = artifacts,
            Err(err) => self.set_error(err),
        }
        match quality_res {
            Ok(quality) => self.state.step_quality = Some(quality),
            Err(err) => self.set_error(err),
        }
        match policy_findings_res {
            Ok(findings) => self.state.step_policy_findings = findings,
            Err(err) => self.set_error(err),
        }

        Ok(())
    }

    pub(crate) async fn load_runs_page(&mut self) -> Result<()> {
        match self
            .client
            .runs(None, None, self.state.run_status_filter.as_deref())
            .await
        {
            Ok(runs) => {
                self.state.runs = runs;
                if self.state.runs.is_empty() {
                    self.state.run_index = None;
                    self.state.clear_run_workspace();
                } else if self
                    .state
                    .run_index
                    .map(|idx| idx >= self.state.runs.len())
                    .unwrap_or(true)
                {
                    self.state.run_index = Some(0);
                }
            }
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_run_workspace(&mut self) -> Result<()> {
        let Some(run_id) = self.state.selected_run_id().map(str::to_string) else {
            self.state.clear_run_workspace();
            return Ok(());
        };
        let client = self.client.clone();
        let (run_res, logs_res, artifacts_res) = tokio::join!(
            client.run(&run_id),
            client.run_logs(&run_id),
            client.run_artifacts(&run_id),
        );
        match run_res {
            Ok(run) => self.state.run_detail = Some(run),
            Err(err) => self.set_error(err),
        }
        match logs_res {
            Ok(logs) => self.state.run_logs = Some(logs),
            Err(err) => self.set_error(err),
        }
        match artifacts_res {
            Ok(artifacts) => self.state.run_artifacts = artifacts,
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_quality_dashboard(&mut self) -> Result<()> {
        let client = self.client.clone();
        let (quality_res, metrics_res) =
            tokio::join!(client.quality_dashboard(), client.metrics_summary());
        match quality_res {
            Ok(dashboard) => self.state.quality_dashboard = Some(dashboard),
            Err(err) => self.set_error(err),
        }
        match metrics_res {
            Ok(summary) => self.state.metrics_summary = Some(summary),
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_metrics_summary(&mut self) -> Result<()> {
        match self.client.metrics_summary().await {
            Ok(summary) => self.state.metrics_summary = Some(summary),
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) async fn load_policy_packs(&mut self) -> Result<()> {
        match self.client.policy_packs().await {
            Ok(packs) => {
                self.state.policy_packs = packs;
                if self.state.policy_packs.is_empty() {
                    self.state.policy_pack_index = None;
                    self.state.policy_pack_detail = None;
                    return Ok(());
                }
                if self
                    .state
                    .policy_pack_index
                    .map(|idx| idx >= self.state.policy_packs.len())
                    .unwrap_or(true)
                {
                    self.state.policy_pack_index = Some(0);
                }
            }
            Err(err) => self.set_error(err),
        }
        if let Some(key) = self.state.selected_policy_pack_key().map(str::to_string) {
            match self.client.policy_pack(&key).await {
                Ok(pack) => self.state.policy_pack_detail = Some(pack),
                Err(err) => self.set_error(err),
            }
        }
        Ok(())
    }

    pub(crate) async fn load_agents_page(&mut self) -> Result<()> {
        let project_id = self.state.selected_project_id();
        let client = self.client.clone();
        let (agents_res, health_res, metrics_res, assignments_res, prompts_res) = tokio::join!(
            client.agents(project_id),
            client.agent_health(),
            client.agent_metrics(project_id),
            client.agent_assignments(project_id),
            client.agent_prompts(project_id),
        );
        match agents_res {
            Ok(agents) => {
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
            Err(err) => self.set_error(err),
        }
        match health_res {
            Ok(health) => self.state.agent_health = health,
            Err(err) => self.set_error(err),
        }
        match metrics_res {
            Ok(metrics) => self.state.agent_metrics = metrics,
            Err(err) => self.set_error(err),
        }
        match assignments_res {
            Ok(assignments) => self.state.agent_assignments = Some(assignments),
            Err(err) => self.set_error(err),
        }
        match prompts_res {
            Ok(prompts) => self.state.agent_prompts = prompts,
            Err(err) => self.set_error(err),
        }
        self.load_selected_agent_detail().await?;
        Ok(())
    }

    pub(crate) async fn load_selected_agent_detail(&mut self) -> Result<()> {
        if let Some(agent_id) = self.state.selected_agent_id().map(str::to_string) {
            match self
                .client
                .agent(&agent_id, self.state.selected_project_id())
                .await
            {
                Ok(agent) => self.state.agent_detail = Some(agent),
                Err(err) => self.set_error(err),
            }
        } else {
            self.state.agent_detail = None;
        }
        Ok(())
    }

    pub(crate) async fn load_settings_data(&mut self) -> Result<()> {
        match self.client.profile().await {
            Ok(profile) => self.state.profile = Some(profile),
            Err(err) => self.set_error(err),
        }
        Ok(())
    }

    pub(crate) fn set_error(&mut self, err: ApiError) {
        self.state.last_error = Some(err.to_string());
        self.state.refreshing = false;
        self.state.status = "Request failed".into();
    }
}
