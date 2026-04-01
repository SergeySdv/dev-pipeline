use super::App;
use crate::state::{Page, ProjectWorkspaceTab, SavedFilter, SearchResult, SearchScope};
use anyhow::Result;
use std::{
    env, fs,
    path::PathBuf,
    process::{Command, Stdio},
};

pub(crate) fn load_saved_filters() -> Vec<SavedFilter> {
    let path = saved_filters_path();
    let Ok(body) = fs::read_to_string(path) else {
        return Vec::new();
    };
    serde_json::from_str(&body).unwrap_or_default()
}

fn persist_saved_filters(filters: &[SavedFilter]) -> Result<()> {
    let path = saved_filters_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let body = serde_json::to_string_pretty(filters)?;
    fs::write(path, body)?;
    Ok(())
}

fn saved_filters_path() -> PathBuf {
    if let Ok(dir) = env::var("DEVGODZILLA_TUI_STATE_DIR") {
        return PathBuf::from(dir).join("saved-filters.json");
    }
    let home = env::var("HOME").unwrap_or_else(|_| ".".into());
    PathBuf::from(home)
        .join(".config")
        .join("devgodzilla-tui")
        .join("saved-filters.json")
}

impl App {
    pub(crate) fn apply_search(
        &mut self,
        scope: SearchScope,
        query: String,
        save_name: Option<String>,
    ) {
        let query = query.trim().to_string();
        self.state.search_scope = scope;
        self.state.global_query = if query.is_empty() {
            None
        } else {
            Some(query.clone())
        };
        self.state.search_results = self.build_search_results(scope, &query);
        if let Some(name) = save_name.filter(|name| !name.trim().is_empty()) {
            let filter = SavedFilter {
                name,
                scope,
                query: query.clone(),
            };
            if let Some(existing) = self
                .state
                .saved_filters
                .iter_mut()
                .find(|saved| saved.name == filter.name)
            {
                *existing = filter;
            } else {
                self.state.saved_filters.push(filter);
            }
            if let Err(err) = persist_saved_filters(&self.state.saved_filters) {
                self.state.last_error = Some(format!("Unable to persist saved filters: {err}"));
            }
        }
        if let Some(result) = self.state.search_results.first().cloned() {
            self.jump_to_search_result(&result);
            self.state.status = format!(
                "Search {} found {} result(s)",
                scope.label(),
                self.state.search_results.len()
            );
        } else {
            self.state.status = format!("Search {} found no matches", scope.label());
        }
    }

    pub(crate) fn build_search_results(
        &self,
        scope: SearchScope,
        query: &str,
    ) -> Vec<SearchResult> {
        let query = query.to_ascii_lowercase();
        let mut results = Vec::new();
        let matches = |value: &str| query.is_empty() || value.to_ascii_lowercase().contains(&query);
        let include_scope =
            |candidate: SearchScope| scope == SearchScope::All || scope == candidate;

        if include_scope(SearchScope::Projects) {
            for (project_index, project) in self.state.projects.iter().enumerate() {
                let haystack = format!(
                    "{} {} {}",
                    project.name,
                    project.description.clone().unwrap_or_default(),
                    project.git_url.clone().unwrap_or_default()
                );
                if matches(&haystack) {
                    results.push(SearchResult {
                        scope: SearchScope::Projects,
                        label: project.name.clone(),
                        detail: format!("project {}", project.id),
                        project_index: Some(project_index),
                        ..Default::default()
                    });
                }
            }
        }
        if include_scope(SearchScope::Specs) {
            for (project_spec_index, spec) in self.state.project_specs.iter().enumerate() {
                let haystack = format!("{} {} {}", spec.title, spec.path, spec.status);
                if matches(&haystack) {
                    results.push(SearchResult {
                        scope: SearchScope::Specs,
                        label: spec.title.clone(),
                        detail: spec.path.clone(),
                        project_index: self.state.project_index,
                        project_spec_index: Some(project_spec_index),
                        ..Default::default()
                    });
                }
            }
        }
        if include_scope(SearchScope::Protocols) {
            for (protocol_index, protocol) in self.state.protocols.iter().enumerate() {
                let haystack = format!(
                    "{} {} {}",
                    protocol.id,
                    protocol.protocol_name,
                    protocol.status.clone().unwrap_or_default()
                );
                if matches(&haystack) {
                    results.push(SearchResult {
                        scope: SearchScope::Protocols,
                        label: protocol.protocol_name.clone(),
                        detail: format!("protocol {}", protocol.id),
                        project_index: self.state.project_index,
                        protocol_index: Some(protocol_index),
                        ..Default::default()
                    });
                }
            }
        }
        if include_scope(SearchScope::Steps) {
            for (step_index, step) in self.state.steps.iter().enumerate() {
                let haystack = format!("{} {} {}", step.id, step.step_name, step.status);
                if matches(&haystack) {
                    results.push(SearchResult {
                        scope: SearchScope::Steps,
                        label: step.step_name.clone(),
                        detail: format!("step {}", step.id),
                        project_index: self.state.project_index,
                        protocol_index: self.state.protocol_index,
                        step_index: Some(step_index),
                        ..Default::default()
                    });
                }
            }
        }
        if include_scope(SearchScope::Runs) {
            for (run_index, run) in self.state.runs.iter().enumerate() {
                let haystack = format!("{} {} {}", run.run_id, run.job_type, run.status);
                if matches(&haystack) {
                    results.push(SearchResult {
                        scope: SearchScope::Runs,
                        label: run.run_id.clone(),
                        detail: format!("{} [{}]", run.job_type, run.status),
                        run_index: Some(run_index),
                        ..Default::default()
                    });
                }
            }
        }
        if include_scope(SearchScope::Events) {
            for (event_index, event) in self.state.recent_events.iter().enumerate() {
                let haystack = format!("{} {}", event.event_type, event.message);
                if matches(&haystack) {
                    results.push(SearchResult {
                        scope: SearchScope::Events,
                        label: event.event_type.clone(),
                        detail: event.message.clone(),
                        event_index: Some(event_index),
                        ..Default::default()
                    });
                }
            }
        }
        if include_scope(SearchScope::Queues) {
            for job in &self.state.queue_jobs {
                let haystack = format!(
                    "{} {}",
                    job.job_id.clone().unwrap_or_default(),
                    job.status.clone().unwrap_or_default()
                );
                if matches(&haystack) {
                    results.push(SearchResult {
                        scope: SearchScope::Queues,
                        label: job.job_id.clone().unwrap_or_else(|| "-".into()),
                        detail: job.status.clone().unwrap_or_else(|| "-".into()),
                        ..Default::default()
                    });
                }
            }
        }
        if include_scope(SearchScope::Policy) {
            for (policy_pack_index, pack) in self.state.policy_packs.iter().enumerate() {
                let haystack = format!("{} {} {}", pack.key, pack.name, pack.version);
                if matches(&haystack) {
                    results.push(SearchResult {
                        scope: SearchScope::Policy,
                        label: pack.name.clone(),
                        detail: format!("{}@{}", pack.key, pack.version),
                        policy_pack_index: Some(policy_pack_index),
                        ..Default::default()
                    });
                }
            }
        }
        if include_scope(SearchScope::Agents) {
            for (agent_index, agent) in self.state.agents.iter().enumerate() {
                let haystack = format!("{} {} {}", agent.id, agent.name, agent.kind);
                if matches(&haystack) {
                    results.push(SearchResult {
                        scope: SearchScope::Agents,
                        label: agent.name.clone(),
                        detail: agent.id.clone(),
                        agent_index: Some(agent_index),
                        ..Default::default()
                    });
                }
            }
        }
        results
    }

    pub(crate) fn jump_to_search_result(&mut self, result: &SearchResult) {
        if let Some(project_index) = result.project_index {
            self.state.project_index = Some(project_index);
        }
        if let Some(project_spec_index) = result.project_spec_index {
            self.state.project_spec_index = Some(project_spec_index);
        }
        if let Some(protocol_index) = result.protocol_index {
            self.state.protocol_index = Some(protocol_index);
        }
        if let Some(step_index) = result.step_index {
            self.state.step_index = Some(step_index);
        }
        if let Some(run_index) = result.run_index {
            self.state.run_index = Some(run_index);
        }
        if let Some(policy_pack_index) = result.policy_pack_index {
            self.state.policy_pack_index = Some(policy_pack_index);
        }
        if let Some(agent_index) = result.agent_index {
            self.state.agent_index = Some(agent_index);
        }
        if let Some(event_index) = result.event_index {
            self.state.recent_event_index = Some(event_index);
        }
        match result.scope {
            SearchScope::Projects => self.state.page = Page::Projects,
            SearchScope::Specs => {
                self.state.page = Page::Projects;
                self.state.project_workspace_tab = ProjectWorkspaceTab::Specs;
            }
            SearchScope::Protocols => self.state.page = Page::Protocols,
            SearchScope::Steps => self.state.page = Page::Steps,
            SearchScope::Runs => self.state.page = Page::Runs,
            SearchScope::Events => self.state.page = Page::Events,
            SearchScope::Queues => self.state.page = Page::Queues,
            SearchScope::Policy => self.state.page = Page::Policy,
            SearchScope::Agents => self.state.page = Page::Agents,
            SearchScope::All => {}
        }
        self.pending_refresh = true;
    }

    pub(crate) fn review_links(&self) -> Vec<(String, String)> {
        let mut links = Vec::new();
        let base = self.client.base_url().trim_end_matches('/');
        if self.state.page == Page::Projects {
            if let Some(project) = self.state.selected_project() {
                if let Some(path) = &project.effective_repo_path {
                    links.push(("repo path".into(), path.clone()));
                }
                if let Some(repo) = &project.git_url {
                    links.push(("repository".into(), repo.clone()));
                }
                links.push((
                    "project api".into(),
                    format!("{base}/projects/{}", project.id),
                ));
            }
            return links;
        }
        if let Some(run_id) = self.state.selected_run_id() {
            links.push(("run api".into(), format!("{base}/runs/{run_id}")));
            links.push(("run logs".into(), format!("{base}/runs/{run_id}/logs")));
        }
        if let Some(step_id) = self.state.selected_step_id() {
            links.push(("step api".into(), format!("{base}/steps/{step_id}")));
        }
        if let Some(protocol_id) = self.state.selected_protocol_id() {
            links.push((
                "protocol api".into(),
                format!("{base}/protocols/{protocol_id}"),
            ));
        }
        if let Some(spec) = self.state.selected_project_spec() {
            links.push((
                "spec content".into(),
                format!("{base}/specifications/{}/content", spec.id),
            ));
        }
        if let Some(project) = self.state.selected_project() {
            links.push((
                "project api".into(),
                format!("{base}/projects/{}", project.id),
            ));
            if let Some(repo) = &project.git_url {
                links.push(("repository".into(), repo.clone()));
            }
            if let Some(path) = &project.effective_repo_path {
                links.push(("repo path".into(), path.clone()));
            }
        }
        links
    }

    pub(crate) fn best_link(&self) -> Option<String> {
        self.review_links()
            .into_iter()
            .map(|(_, value)| value)
            .next()
    }

    pub(crate) fn open_best_link(&mut self) -> Result<()> {
        let Some(link) = self.best_link() else {
            self.state.last_error = Some("No link available for the current selection".into());
            return Ok(());
        };
        let openers = if cfg!(target_os = "macos") {
            vec!["open", "xdg-open"]
        } else {
            vec!["xdg-open", "open"]
        };
        for opener in openers {
            if Command::new(opener)
                .arg(&link)
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .is_ok()
            {
                self.state.external_action_result = Some(format!("Opened {link}"));
                self.state.status = format!("Opened {link}");
                return Ok(());
            }
        }
        self.state.last_error = Some(format!("Unable to open {link}"));
        Ok(())
    }

    pub(crate) fn copy_best_link(&mut self) -> Result<()> {
        let Some(link) = self.best_link() else {
            self.state.last_error = Some("No link available for the current selection".into());
            return Ok(());
        };
        let copied = if cfg!(target_os = "macos") {
            Command::new("pbcopy")
                .stdin(Stdio::piped())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .and_then(|mut child| {
                    if let Some(stdin) = child.stdin.as_mut() {
                        use std::io::Write;
                        let _ = stdin.write_all(link.as_bytes());
                    }
                    child.wait().map(|status| status.success())
                })
                .unwrap_or(false)
        } else {
            false
        };
        if copied {
            self.state.external_action_result = Some(format!("Copied {link}"));
            self.state.status = format!("Copied {link}");
        } else {
            self.state.last_error = Some("Unable to copy link to clipboard".into());
        }
        Ok(())
    }
}
