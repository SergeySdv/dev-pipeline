use super::{App, InputField, QuickAction, Screen};
use crate::{
    api::ApiClient,
    models::{AgentAssignment, AgentAssignments},
    state::{Page, SearchScope},
};
use anyhow::Result;
use std::collections::BTreeMap;

impl App {
    pub(crate) async fn handle_form_submit(
        &mut self,
        action: super::ModalAction,
        fields: Vec<InputField>,
    ) -> Result<()> {
        match action {
            super::ModalAction::CreateProject => {
                if fields.len() >= 3 {
                    let name = fields[0].value.trim();
                    let git = fields[1].value.trim();
                    let branch = fields[2].value.trim();
                    if name.is_empty() || git.is_empty() {
                        self.state.last_error = Some("Name and Git URL required".into());
                        return Ok(());
                    }
                    match self
                        .client
                        .create_project(name, git, if branch.is_empty() { "main" } else { branch })
                        .await
                    {
                        Ok(proj) => {
                            self.state.projects.retain(|project| project.id != proj.id);
                            self.state.projects.insert(0, proj.clone());
                            self.state.select_project_by_id(proj.id);
                            self.state.status = format!("Created project {}", proj.id);
                            self.schedule_refresh("Refreshing projects...");
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
            super::ModalAction::CreateProtocol => {
                if let Some(project_id) = self.state.selected_project_id() {
                    if fields.len() >= 3 {
                        let name = fields[0].value.trim();
                        let branch = fields[1].value.trim();
                        let desc = fields[2].value.trim();
                        if name.is_empty() {
                            self.state.last_error = Some("Protocol name required".into());
                            return Ok(());
                        }
                        match self
                            .client
                            .create_protocol(
                                project_id,
                                name,
                                if branch.is_empty() { "main" } else { branch },
                                if desc.is_empty() {
                                    None
                                } else {
                                    Some(desc.to_string())
                                },
                            )
                            .await
                        {
                            Ok(run) => {
                                self.state.protocol_index = None;
                                self.state.status = format!("Created protocol {}", run.id);
                                self.schedule_refresh("Refreshing protocols...");
                            }
                            Err(err) => self.set_error(err),
                        }
                    }
                } else {
                    self.state.last_error = Some("Select a project first".into());
                }
            }
            super::ModalAction::SpecAudit => {
                let project_id = fields
                    .get(0)
                    .and_then(|f| f.value.trim().parse::<i64>().ok());
                let protocol_id = fields
                    .get(1)
                    .and_then(|f| f.value.trim().parse::<i64>().ok());
                let backfill = fields
                    .get(2)
                    .map(|f| f.value.trim().to_lowercase().starts_with('y'))
                    .unwrap_or(false);
                let interval_seconds = fields
                    .get(3)
                    .and_then(|f| f.value.trim().parse::<i64>().ok());
                match self
                    .client
                    .spec_audit(project_id, protocol_id, backfill, interval_seconds)
                    .await
                {
                    Ok(_) => self.state.status = "Spec audit enqueued".into(),
                    Err(err) => self.set_error(err),
                }
            }
            super::ModalAction::Search => {
                let load_name = fields
                    .get(3)
                    .map(|field| field.value.trim().to_string())
                    .unwrap_or_default();
                let saved = if load_name.is_empty() {
                    None
                } else {
                    self.state
                        .saved_filters
                        .iter()
                        .find(|saved| saved.name == load_name)
                        .cloned()
                };
                let scope = saved.as_ref().map(|saved| saved.scope).unwrap_or_else(|| {
                    fields
                        .first()
                        .map(|field| SearchScope::from_input(&field.value))
                        .unwrap_or_default()
                });
                let query = saved
                    .as_ref()
                    .map(|saved| saved.query.clone())
                    .unwrap_or_else(|| {
                        fields
                            .get(1)
                            .map(|field| field.value.trim().to_string())
                            .unwrap_or_default()
                    });
                let save_name = fields
                    .get(2)
                    .map(|field| field.value.trim().to_string())
                    .unwrap_or_default();
                if !load_name.is_empty() && saved.is_none() {
                    self.state.last_error = Some(format!("Saved filter '{load_name}' not found"));
                    return Ok(());
                }
                self.apply_search(
                    scope,
                    query,
                    if save_name.is_empty() {
                        None
                    } else {
                        Some(save_name)
                    },
                );
            }
            super::ModalAction::SpecInit => {
                if let Some(project_id) = self.state.selected_project_id() {
                    match self.client.speckit_init(project_id).await {
                        Ok(result) => {
                            self.state.status = if result.success {
                                "SpecKit initialized".into()
                            } else {
                                result.error.unwrap_or_else(|| "SpecKit init failed".into())
                            };
                            self.schedule_refresh("Refreshing project specs...");
                        }
                        Err(err) => self.set_error(err),
                    }
                } else {
                    self.state.last_error = Some("Select a project first".into());
                }
            }
            super::ModalAction::SpecGenerate => {
                if let Some(project_id) = self.state.selected_project_id() {
                    let description = fields
                        .first()
                        .map(|field| field.value.trim())
                        .unwrap_or_default();
                    if description.len() < 10 {
                        self.state.last_error =
                            Some("Feature description must be at least 10 characters".into());
                        return Ok(());
                    }
                    let feature_name = fields
                        .get(1)
                        .map(|field| field.value.trim())
                        .filter(|value| !value.is_empty())
                        .map(str::to_string);
                    let base_branch = fields
                        .get(2)
                        .map(|field| field.value.trim())
                        .filter(|value| !value.is_empty())
                        .map(str::to_string);
                    match self
                        .client
                        .speckit_specify(project_id, description, feature_name, base_branch)
                        .await
                    {
                        Ok(result) => {
                            self.state.status = if result.success {
                                format!(
                                    "Spec generated {}",
                                    result.spec_path.unwrap_or_else(|| "-".into())
                                )
                            } else {
                                result
                                    .error
                                    .unwrap_or_else(|| "Spec generation failed".into())
                            };
                            self.schedule_refresh("Refreshing project specs...");
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
            super::ModalAction::SpecPlan => {
                if let Some(project_id) = self.state.selected_project_id() {
                    let spec_path = fields
                        .first()
                        .map(|field| field.value.trim())
                        .unwrap_or_default();
                    if spec_path.is_empty() {
                        self.state.last_error = Some("Spec path required".into());
                        return Ok(());
                    }
                    let spec_run_id = fields
                        .get(1)
                        .and_then(|field| field.value.trim().parse::<i64>().ok());
                    let context = fields
                        .get(2)
                        .map(|field| field.value.trim())
                        .filter(|value| !value.is_empty())
                        .map(str::to_string);
                    match self
                        .client
                        .speckit_plan(project_id, spec_path, spec_run_id, context)
                        .await
                    {
                        Ok(result) => {
                            self.state.status = if result.success {
                                format!(
                                    "Plan generated {}",
                                    result.plan_path.unwrap_or_else(|| "-".into())
                                )
                            } else {
                                result
                                    .error
                                    .unwrap_or_else(|| "Spec planning failed".into())
                            };
                            self.schedule_refresh("Refreshing project specs...");
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
            super::ModalAction::SpecTasks => {
                if let Some(project_id) = self.state.selected_project_id() {
                    let plan_path = fields
                        .first()
                        .map(|field| field.value.trim())
                        .unwrap_or_default();
                    if plan_path.is_empty() {
                        self.state.last_error = Some("Plan path required".into());
                        return Ok(());
                    }
                    let spec_run_id = fields
                        .get(1)
                        .and_then(|field| field.value.trim().parse::<i64>().ok());
                    match self
                        .client
                        .speckit_tasks(project_id, plan_path, spec_run_id)
                        .await
                    {
                        Ok(result) => {
                            self.state.status = if result.success {
                                format!("Tasks generated: {}", result.task_count)
                            } else {
                                result
                                    .error
                                    .unwrap_or_else(|| "Task generation failed".into())
                            };
                            self.schedule_refresh("Refreshing project specs...");
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
            super::ModalAction::SpecClarify => {
                if let Some(project_id) = self.state.selected_project_id() {
                    let spec_path = fields
                        .first()
                        .map(|field| field.value.trim())
                        .unwrap_or_default();
                    if spec_path.is_empty() {
                        self.state.last_error = Some("Spec path required".into());
                        return Ok(());
                    }
                    let spec_run_id = fields
                        .get(1)
                        .and_then(|field| field.value.trim().parse::<i64>().ok());
                    let notes = fields
                        .get(2)
                        .map(|field| field.value.trim())
                        .filter(|value| !value.is_empty())
                        .map(str::to_string);
                    match self
                        .client
                        .speckit_clarify(project_id, spec_path, spec_run_id, notes)
                        .await
                    {
                        Ok(result) => {
                            self.state.status = if result.success {
                                format!("Clarifications added: {}", result.clarifications_added)
                            } else {
                                result.error.unwrap_or_else(|| "Clarify failed".into())
                            };
                            self.schedule_refresh("Refreshing project specs...");
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
            super::ModalAction::SpecChecklist => {
                if let Some(project_id) = self.state.selected_project_id() {
                    let spec_path = fields
                        .first()
                        .map(|field| field.value.trim())
                        .unwrap_or_default();
                    if spec_path.is_empty() {
                        self.state.last_error = Some("Spec path required".into());
                        return Ok(());
                    }
                    let spec_run_id = fields
                        .get(1)
                        .and_then(|field| field.value.trim().parse::<i64>().ok());
                    match self
                        .client
                        .speckit_checklist(project_id, spec_path, spec_run_id)
                        .await
                    {
                        Ok(result) => {
                            self.state.status = if result.success {
                                format!("Checklist generated: {} items", result.item_count)
                            } else {
                                result.error.unwrap_or_else(|| "Checklist failed".into())
                            };
                            self.schedule_refresh("Refreshing project specs...");
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
            super::ModalAction::SpecAnalyze => {
                if let Some(project_id) = self.state.selected_project_id() {
                    let spec_path = fields
                        .first()
                        .map(|field| field.value.trim())
                        .unwrap_or_default();
                    if spec_path.is_empty() {
                        self.state.last_error = Some("Spec path required".into());
                        return Ok(());
                    }
                    let plan_path = fields
                        .get(1)
                        .map(|field| field.value.trim())
                        .filter(|value| !value.is_empty())
                        .map(str::to_string);
                    let tasks_path = fields
                        .get(2)
                        .map(|field| field.value.trim())
                        .filter(|value| !value.is_empty())
                        .map(str::to_string);
                    let spec_run_id = fields
                        .get(3)
                        .and_then(|field| field.value.trim().parse::<i64>().ok());
                    match self
                        .client
                        .speckit_analyze(project_id, spec_path, plan_path, tasks_path, spec_run_id)
                        .await
                    {
                        Ok(result) => {
                            self.state.status = if result.success {
                                format!(
                                    "Analysis generated {}",
                                    result.report_path.unwrap_or_else(|| "-".into())
                                )
                            } else {
                                result.error.unwrap_or_else(|| "Analyze failed".into())
                            };
                            self.schedule_refresh("Refreshing project specs...");
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
            super::ModalAction::SpecImplement => {
                if let Some(project_id) = self.state.selected_project_id() {
                    let spec_path = fields
                        .first()
                        .map(|field| field.value.trim())
                        .unwrap_or_default();
                    if spec_path.is_empty() {
                        self.state.last_error = Some("Spec path required".into());
                        return Ok(());
                    }
                    let spec_run_id = fields
                        .get(1)
                        .and_then(|field| field.value.trim().parse::<i64>().ok());
                    match self
                        .client
                        .speckit_implement(project_id, spec_path, spec_run_id)
                        .await
                    {
                        Ok(result) => {
                            self.state.status = if result.success {
                                format!("Spec implemented with {} steps", result.step_count)
                            } else {
                                result.error.unwrap_or_else(|| "Implement failed".into())
                            };
                            self.schedule_refresh("Refreshing project specs...");
                            if let Some(protocol_id) = result.protocol_id {
                                self.switch_page(Page::Protocols);
                                self.schedule_refresh(format!("Loading protocol {protocol_id}..."));
                            }
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
            super::ModalAction::SpecCleanup => {
                let spec_run_id = fields
                    .first()
                    .and_then(|field| field.value.trim().parse::<i64>().ok());
                let delete_remote_branch = fields
                    .get(1)
                    .map(|field| field.value.trim().to_ascii_lowercase().starts_with('y'))
                    .unwrap_or(false);
                if let Some(spec_run_id) = spec_run_id {
                    match self
                        .client
                        .speckit_cleanup(spec_run_id, delete_remote_branch)
                        .await
                    {
                        Ok(result) => {
                            self.state.status = if result.success {
                                format!("Spec run {spec_run_id} cleaned up")
                            } else {
                                result.error.unwrap_or_else(|| "Cleanup failed".into())
                            };
                            self.schedule_refresh("Refreshing project specs...");
                        }
                        Err(err) => self.set_error(err),
                    }
                } else {
                    self.state.last_error = Some("Spec run ID required".into());
                }
            }
            super::ModalAction::AgentAssign => {
                let process = fields
                    .first()
                    .map(|field| field.value.trim())
                    .unwrap_or_default()
                    .to_string();
                let agent_id = fields
                    .get(1)
                    .map(|field| field.value.trim())
                    .unwrap_or_default()
                    .to_string();
                if process.is_empty() || agent_id.is_empty() {
                    self.state.last_error = Some("Process and agent ID required".into());
                    return Ok(());
                }
                let prompt_id = fields
                    .get(2)
                    .map(|field| field.value.trim())
                    .filter(|value| !value.is_empty())
                    .map(str::to_string);
                let model_override = fields
                    .get(3)
                    .map(|field| field.value.trim())
                    .filter(|value| !value.is_empty())
                    .map(str::to_string);
                let enabled = fields
                    .get(4)
                    .map(|field| field.value.trim().to_ascii_lowercase().starts_with('y'));
                let mut assignments =
                    self.state
                        .agent_assignments
                        .clone()
                        .unwrap_or_else(|| AgentAssignments {
                            assignments: BTreeMap::new(),
                            inherit_global: Some(false),
                        });
                assignments.assignments.insert(
                    process.clone(),
                    AgentAssignment {
                        agent_id: Some(agent_id.clone()),
                        prompt_id,
                        model_override,
                        enabled,
                        metadata: None,
                    },
                );
                let project_id = self.state.selected_project_id();
                match self
                    .client
                    .update_agent_assignments(&assignments, project_id)
                    .await
                {
                    Ok(updated) => {
                        self.state.agent_assignments = Some(updated);
                        self.state.status =
                            format!("Assigned process {process} to agent {agent_id}");
                        self.schedule_refresh("Refreshing agent assignments...");
                    }
                    Err(err) => self.set_error(err),
                }
            }
            super::ModalAction::AgentConfig => {
                let Some(agent_id) = self.state.selected_agent_id().map(str::to_string) else {
                    self.state.last_error = Some("Select an agent first".into());
                    return Ok(());
                };
                let text_value = |idx: usize| {
                    fields
                        .get(idx)
                        .map(|field| field.value.trim().to_string())
                        .unwrap_or_default()
                };
                let optional_value = |idx: usize| {
                    fields
                        .get(idx)
                        .map(|field| field.value.trim())
                        .filter(|value| !value.is_empty())
                        .map(str::to_string)
                };
                let parse_optional_i64 = |idx: usize, label: &str| -> Result<Option<i64>> {
                    let raw = text_value(idx);
                    if raw.is_empty() {
                        return Ok(None);
                    }
                    raw.parse::<i64>()
                        .map(Some)
                        .map_err(|_| anyhow::anyhow!("{label} must be a number"))
                };

                let timeout_seconds = match parse_optional_i64(11, "Timeout seconds") {
                    Ok(value) => value,
                    Err(err) => {
                        self.state.last_error = Some(err.to_string());
                        return Ok(());
                    }
                };
                let max_retries = match parse_optional_i64(12, "Max retries") {
                    Ok(value) => value,
                    Err(err) => {
                        self.state.last_error = Some(err.to_string());
                        return Ok(());
                    }
                };

                let capabilities = fields
                    .get(5)
                    .map(|field| {
                        field
                            .value
                            .split(',')
                            .map(str::trim)
                            .filter(|value| !value.is_empty())
                            .map(str::to_string)
                            .collect::<Vec<_>>()
                    })
                    .filter(|items| !items.is_empty());

                let payload = serde_json::json!({
                    "name": optional_value(0),
                    "kind": optional_value(1),
                    "enabled": fields
                        .get(2)
                        .map(|field| field.value.trim().to_ascii_lowercase().starts_with('y'))
                        .unwrap_or(false),
                    "default_model": optional_value(3),
                    "reasoning_effort": optional_value(4),
                    "capabilities": capabilities,
                    "command_dir": optional_value(6),
                    "command": optional_value(7),
                    "endpoint": optional_value(8),
                    "sandbox": optional_value(9),
                    "format": optional_value(10),
                    "timeout_seconds": timeout_seconds,
                    "max_retries": max_retries,
                });

                match self
                    .client
                    .update_agent_config(&agent_id, payload, self.state.selected_project_id())
                    .await
                {
                    Ok(updated) => {
                        self.state.agent_detail = Some(updated);
                        self.state.status = format!("Updated agent config for {agent_id}");
                        self.schedule_refresh("Refreshing agent configuration...");
                    }
                    Err(err) => self.set_error(err),
                }
            }
            super::ModalAction::ImportCodeMachine => {
                if let Some(project_id) = self.state.selected_project_id() {
                    if fields.len() >= 5 {
                        let name = fields[0].value.trim();
                        let path = fields[1].value.trim();
                        let branch = fields[2].value.trim();
                        let desc = fields[3].value.trim();
                        let enqueue = fields[4].value.trim().to_lowercase().starts_with('y');
                        if name.is_empty() || path.is_empty() {
                            self.state.last_error =
                                Some("Protocol name and workspace path required".into());
                            return Ok(());
                        }
                        match self
                            .client
                            .import_codemachine(
                                project_id,
                                name,
                                path,
                                if branch.is_empty() { "main" } else { branch },
                                if desc.is_empty() {
                                    None
                                } else {
                                    Some(desc.to_string())
                                },
                                enqueue,
                            )
                            .await
                        {
                            Ok(_) => {
                                self.state.status = "Import enqueued".into();
                                self.schedule_refresh("Refreshing import status...");
                            }
                            Err(err) => self.set_error(err),
                        }
                    }
                } else {
                    self.state.last_error = Some("Select a project first".into());
                }
            }
            super::ModalAction::TokenConfig => {
                if fields.len() >= 3 {
                    let api_base = fields[0].value.trim();
                    let token = fields[1].value.trim();
                    let project_token = fields[2].value.trim();
                    if !api_base.is_empty() {
                        self.client = ApiClient::new(
                            api_base.to_string(),
                            if token.is_empty() {
                                None
                            } else {
                                Some(token.to_string())
                            },
                            if project_token.is_empty() {
                                None
                            } else {
                                Some(project_token.to_string())
                            },
                        )?;
                        self.state.status = format!("API base set to {api_base}");
                    }
                }
            }
            super::ModalAction::DeleteBranch => {
                if let Some(idx) = self.state.branch_index {
                    if let (Some(branch), Some(project_id)) = (
                        self.state.branches.get(idx),
                        self.state.selected_project_id(),
                    ) {
                        match self.client.delete_branch(project_id, &branch.name).await {
                            Ok(_) => {
                                self.state.status = format!("Deleted branch {}", branch.name);
                                self.load_project_workspace().await?;
                            }
                            Err(err) => self.set_error(err),
                        }
                    }
                }
            }
            super::ModalAction::ArchiveProject => {
                if let Some(project_id) = self.state.selected_project_id() {
                    match self.client.archive_project(project_id).await {
                        Ok(project) => {
                            self.state.status = format!("Archived project {}", project.name);
                            self.schedule_refresh("Refreshing projects...");
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
            super::ModalAction::UnarchiveProject => {
                if let Some(project_id) = self.state.selected_project_id() {
                    match self.client.unarchive_project(project_id).await {
                        Ok(project) => {
                            self.state.status = format!("Unarchived project {}", project.name);
                            self.schedule_refresh("Refreshing projects...");
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
            super::ModalAction::DeleteProject => {
                if let Some(project_id) = self.state.selected_project_id() {
                    match self.client.delete_project(project_id).await {
                        Ok(_) => {
                            self.state.status = format!("Deleted project {}", project_id);
                            self.schedule_refresh("Refreshing projects...");
                        }
                        Err(err) => self.set_error(err),
                    }
                }
            }
        }
        Ok(())
    }

    pub(crate) async fn run_quick_action(&mut self, action: QuickAction) -> Result<()> {
        match action {
            QuickAction::CreateProject => self.open_project_modal(),
            QuickAction::CreateProtocol => self.open_protocol_modal(),
            QuickAction::TestAgent => self.run_agent_test().await?,
            QuickAction::RunNext => self.run_next().await?,
            QuickAction::RetryLatest => self.retry_latest().await?,
            QuickAction::RunQa => self.run_qa_latest().await?,
            QuickAction::Approve => self.approve_latest().await?,
            QuickAction::OpenPr => self.open_pr().await?,
            QuickAction::StartProtocol => {
                self.protocol_action("start", "Planning enqueued.").await?
            }
            QuickAction::PauseProtocol => self.protocol_action("pause", "Protocol paused.").await?,
            QuickAction::ResumeProtocol => {
                self.protocol_action("resume", "Protocol resumed.").await?
            }
            QuickAction::CancelProtocol => {
                self.protocol_action("cancel", "Protocol cancelled.")
                    .await?
            }
            QuickAction::ImportCodeMachine => self.open_cm_modal(),
            QuickAction::SpecAudit => self.open_spec_audit_modal(),
            QuickAction::Search => self.open_search_modal(),
            QuickAction::SpecInit => self.open_spec_init_modal(),
            QuickAction::SpecGenerate => self.open_spec_generate_modal(),
            QuickAction::SpecPlan => self.open_spec_plan_modal(),
            QuickAction::SpecTasks => self.open_spec_tasks_modal(),
            QuickAction::SpecClarify => self.open_spec_clarify_modal(),
            QuickAction::SpecChecklist => self.open_spec_checklist_modal(),
            QuickAction::SpecAnalyze => self.open_spec_analyze_modal(),
            QuickAction::SpecImplement => self.open_spec_implement_modal(),
            QuickAction::SpecCleanup => self.open_spec_cleanup_modal(),
            QuickAction::OpenLink => self.open_best_link()?,
            QuickAction::CopyLink => self.copy_best_link()?,
            QuickAction::DuplicateProject => self.open_duplicate_project_modal(),
            QuickAction::AssignAgent => self.open_agent_assignment_modal(),
            QuickAction::Configure => {
                if self.state.page == Page::Agents {
                    self.open_agent_config_modal();
                } else {
                    self.open_token_modal();
                }
            }
            QuickAction::Menu => {
                self.screen = Screen::Menu;
                self.menu_index = 0;
            }
        }
        Ok(())
    }

    pub(crate) async fn run_next(&mut self) -> Result<()> {
        if let Some(protocol_id) = self.state.selected_protocol_id() {
            match self.client.step_run_next(protocol_id).await {
                Ok(_) => {
                    self.state.status = "Run next enqueued".into();
                    self.schedule_refresh("Refreshing run state...");
                }
                Err(err) => self.set_error(err),
            }
        }
        Ok(())
    }

    pub(crate) async fn retry_latest(&mut self) -> Result<()> {
        if let Some(protocol_id) = self.state.selected_protocol_id() {
            match self.client.step_retry_latest(protocol_id).await {
                Ok(_) => {
                    self.state.status = "Retry enqueued".into();
                    self.schedule_refresh("Refreshing retry status...");
                }
                Err(err) => self.set_error(err),
            }
        }
        Ok(())
    }

    pub(crate) async fn run_qa_latest(&mut self) -> Result<()> {
        if let Some(step_id) = self.state.selected_step_id() {
            match self.client.step_run_qa(step_id).await {
                Ok(_) => {
                    self.state.status = "QA enqueued".into();
                    self.schedule_refresh("Refreshing QA status...");
                }
                Err(err) => self.set_error(err),
            }
        }
        Ok(())
    }

    pub(crate) async fn approve_latest(&mut self) -> Result<()> {
        if let Some(step_id) = self.state.selected_step_id() {
            match self.client.step_approve(step_id).await {
                Ok(_) => {
                    self.state.status = "Approved".into();
                    self.schedule_refresh("Refreshing approval status...");
                }
                Err(err) => self.set_error(err),
            }
        }
        Ok(())
    }

    pub(crate) async fn open_pr(&mut self) -> Result<()> {
        if let Some(protocol_id) = self.state.selected_protocol_id() {
            match self.client.protocol_open_pr(protocol_id).await {
                Ok(_) => {
                    self.state.status = "Open PR enqueued".into();
                    self.schedule_refresh("Refreshing PR status...");
                }
                Err(err) => self.set_error(err),
            }
        }
        Ok(())
    }

    pub(crate) async fn protocol_action(&mut self, action: &str, success: &str) -> Result<()> {
        if let Some(protocol_id) = self.state.selected_protocol_id() {
            match self.client.protocol_action(protocol_id, action).await {
                Ok(_) => {
                    self.state.status = success.into();
                    self.schedule_refresh("Refreshing protocol state...");
                }
                Err(err) => self.set_error(err),
            }
        }
        Ok(())
    }

    pub(crate) async fn cycle_job_filter(&mut self) -> Result<()> {
        let order = [
            None,
            Some("queued"),
            Some("started"),
            Some("failed"),
            Some("finished"),
        ];
        let idx = order
            .iter()
            .position(|v| v.as_deref() == self.state.job_status_filter.as_deref())
            .unwrap_or(0);
        let next = order[(idx + 1) % order.len()];
        self.state.job_status_filter = next.map(|s| s.to_string());
        self.state.status = format!(
            "Job filter: {}",
            self.state
                .job_status_filter
                .clone()
                .unwrap_or_else(|| "all".into())
        );
        self.load_queue().await?;
        Ok(())
    }

    pub(crate) async fn cycle_step_filter(&mut self) -> Result<()> {
        let order = [
            None,
            Some("pending"),
            Some("running"),
            Some("needs_qa"),
            Some("failed"),
        ];
        let idx = order
            .iter()
            .position(|v| v.as_deref() == self.state.step_filter.as_deref())
            .unwrap_or(0);
        let next = order[(idx + 1) % order.len()];
        self.state.step_filter = next.map(|s| s.to_string());
        self.state.status = format!(
            "Step filter: {}",
            self.state
                .step_filter
                .clone()
                .unwrap_or_else(|| "all".into())
        );
        self.load_steps().await?;
        Ok(())
    }

    pub(crate) async fn run_agent_test(&mut self) -> Result<()> {
        if let Some(agent_id) = self.state.selected_agent_id().map(str::to_string) {
            match self.client.agent_test(&agent_id).await {
                Ok(result) => {
                    self.state.status =
                        format!("Agent test {}", if result.ok { "passed" } else { "failed" });
                    self.state.agent_test_result = Some(result);
                }
                Err(err) => self.set_error(err),
            }
        }
        Ok(())
    }
}
