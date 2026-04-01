use super::{App, InputField, Modal, ModalAction, QuickAction};
use crate::state::{Page, ProjectWorkspaceTab};
use anyhow::Result;
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use serde_json::Value;

impl App {
    fn agent_available_model_values(&self) -> Vec<String> {
        let models = self
            .state
            .agent_detail
            .as_ref()
            .or_else(|| {
                self.state
                    .agent_index
                    .and_then(|idx| self.state.agents.get(idx))
            })
            .map(|agent| &agent.available_models);

        let mut values = Vec::new();
        if let Some(models) = models {
            for model in models {
                let value = match model {
                    Value::String(value) => Some(value.clone()),
                    Value::Object(map) => map
                        .get("value")
                        .and_then(Value::as_str)
                        .or_else(|| map.get("id").and_then(Value::as_str))
                        .or_else(|| map.get("name").and_then(Value::as_str))
                        .map(str::to_string),
                    _ => None,
                };
                if let Some(value) = value.filter(|value| !value.is_empty()) {
                    if !values.iter().any(|existing| existing == &value) {
                        values.push(value);
                    }
                }
            }
        }
        values
    }

    fn cycle_agent_model_field(fields: &mut [InputField], delta: i32, available_models: &[String]) {
        if available_models.is_empty() {
            return;
        }
        let Some(field) = fields.get_mut(3) else {
            return;
        };
        let current = field.value.trim();
        let next_index = if current.is_empty() {
            if delta >= 0 {
                0
            } else {
                available_models.len() - 1
            }
        } else if let Some(idx) = available_models.iter().position(|model| model == current) {
            let len = available_models.len() as i32;
            (idx as i32 + delta).rem_euclid(len) as usize
        } else if delta >= 0 {
            0
        } else {
            available_models.len() - 1
        };
        field.value = available_models[next_index].clone();
    }

    fn agent_available_reasoning_values_for_model(&self, model_value: &str) -> Vec<String> {
        let models = self
            .state
            .agent_detail
            .as_ref()
            .or_else(|| {
                self.state
                    .agent_index
                    .and_then(|idx| self.state.agents.get(idx))
            })
            .map(|agent| &agent.available_models);

        let Some(models) = models else {
            return Vec::new();
        };

        let selected = models.iter().find(|model| {
            model
                .as_object()
                .and_then(|map| map.get("value"))
                .and_then(Value::as_str)
                == Some(model_value)
        });

        let Some(selected) = selected.and_then(Value::as_object) else {
            return Vec::new();
        };

        let mut values = Vec::new();
        if let Some(efforts) = selected.get("reasoning_efforts").and_then(Value::as_array) {
            for effort in efforts {
                let value = effort
                    .as_object()
                    .and_then(|map| map.get("value"))
                    .and_then(Value::as_str)
                    .map(str::to_string);
                if let Some(value) = value.filter(|value| !value.is_empty()) {
                    if !values.iter().any(|existing| existing == &value) {
                        values.push(value);
                    }
                }
            }
        }
        values
    }

    fn cycle_agent_reasoning_field(
        fields: &mut [InputField],
        delta: i32,
        available_efforts: &[String],
    ) {
        if available_efforts.is_empty() {
            return;
        }
        let Some(field) = fields.get_mut(4) else {
            return;
        };
        let current = field.value.trim();
        let next_index = if current.is_empty() {
            if delta >= 0 {
                0
            } else {
                available_efforts.len() - 1
            }
        } else if let Some(idx) = available_efforts
            .iter()
            .position(|effort| effort == current)
        {
            let len = available_efforts.len() as i32;
            (idx as i32 + delta).rem_euclid(len) as usize
        } else if delta >= 0 {
            0
        } else {
            available_efforts.len() - 1
        };
        field.value = available_efforts[next_index].clone();
    }

    pub(crate) fn open_project_modal(&mut self) {
        self.modal = Some(Modal::Form {
            title: "Create project".into(),
            fields: vec![
                InputField {
                    label: "Name".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Git URL".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Base branch (optional, default main)".into(),
                    value: "".into(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::CreateProject,
        });
    }

    pub(crate) fn open_duplicate_project_modal(&mut self) {
        let project = self.state.selected_project();
        self.modal = Some(Modal::Form {
            title: "Duplicate project".into(),
            fields: vec![
                InputField {
                    label: "Name".into(),
                    value: project
                        .map(|p| format!("{}-copy", p.name))
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Git URL".into(),
                    value: project.and_then(|p| p.git_url.clone()).unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Base branch".into(),
                    value: project
                        .and_then(|p| p.base_branch.clone())
                        .unwrap_or_else(|| "main".into()),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::CreateProject,
        });
    }

    pub(crate) fn open_protocol_modal(&mut self) {
        self.modal = Some(Modal::Form {
            title: "Create protocol".into(),
            fields: vec![
                InputField {
                    label: "Protocol name".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Base branch (optional, default main)".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Description (optional)".into(),
                    value: "".into(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::CreateProtocol,
        });
    }

    pub(crate) fn open_token_modal(&mut self) {
        self.modal = Some(Modal::Form {
            title: "Configure API/token".into(),
            fields: vec![
                InputField {
                    label: "API base".into(),
                    value: self.client.base_url().to_string(),
                    is_secret: false,
                },
                InputField {
                    label: "API token (optional)".into(),
                    value: "".into(),
                    is_secret: true,
                },
                InputField {
                    label: "Project token (optional)".into(),
                    value: "".into(),
                    is_secret: true,
                },
            ],
            focus: 0,
            action: ModalAction::TokenConfig,
        });
    }

    pub(crate) fn open_spec_audit_modal(&mut self) {
        let project_default = self
            .state
            .selected_project_id()
            .map(|p| p.to_string())
            .unwrap_or_default();
        let protocol_default = self
            .state
            .selected_protocol_id()
            .map(|p| p.to_string())
            .unwrap_or_default();
        self.modal = Some(Modal::Form {
            title: "Spec audit".into(),
            fields: vec![
                InputField {
                    label: "Project ID (optional)".into(),
                    value: project_default,
                    is_secret: false,
                },
                InputField {
                    label: "Protocol ID (optional)".into(),
                    value: protocol_default,
                    is_secret: false,
                },
                InputField {
                    label: "Backfill? (y/N)".into(),
                    value: "y".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Interval seconds (optional)".into(),
                    value: "".into(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::SpecAudit,
        });
    }

    pub(crate) fn open_search_modal(&mut self) {
        self.modal = Some(Modal::Form {
            title: "Search".into(),
            fields: vec![
                InputField {
                    label: "Scope".into(),
                    value: self.state.search_scope.label().into(),
                    is_secret: false,
                },
                InputField {
                    label: "Query".into(),
                    value: self.state.global_query.clone().unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Save as (optional)".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Load saved filter (optional)".into(),
                    value: self
                        .state
                        .saved_filters
                        .last()
                        .map(|filter| filter.name.clone())
                        .unwrap_or_default(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::Search,
        });
    }

    pub(crate) fn open_spec_init_modal(&mut self) {
        self.modal = Some(Modal::Confirm {
            title: "Initialize SpecKit".into(),
            message: "Initialize SpecKit for the selected project?".into(),
            action: ModalAction::SpecInit,
        });
    }

    pub(crate) fn open_spec_generate_modal(&mut self) {
        let base_branch = self
            .state
            .selected_project()
            .and_then(|project| project.base_branch.clone())
            .unwrap_or_else(|| "main".into());
        self.modal = Some(Modal::Form {
            title: "Generate spec".into(),
            fields: vec![
                InputField {
                    label: "Feature description".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Feature name (optional)".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Base branch (optional)".into(),
                    value: base_branch,
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::SpecGenerate,
        });
    }

    pub(crate) fn open_spec_plan_modal(&mut self) {
        let spec = self.state.selected_project_spec();
        self.modal = Some(Modal::Form {
            title: "Plan spec".into(),
            fields: vec![
                InputField {
                    label: "Spec path".into(),
                    value: spec
                        .and_then(|spec| spec.spec_path.clone().or_else(|| Some(spec.path.clone())))
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Spec run ID (optional)".into(),
                    value: spec
                        .and_then(|spec| spec.spec_run_id.map(|id| id.to_string()))
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Planning context (optional)".into(),
                    value: "".into(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::SpecPlan,
        });
    }

    pub(crate) fn open_spec_tasks_modal(&mut self) {
        let spec = self.state.selected_project_spec();
        self.modal = Some(Modal::Form {
            title: "Generate tasks".into(),
            fields: vec![
                InputField {
                    label: "Plan path".into(),
                    value: spec
                        .and_then(|spec| spec.plan_path.clone())
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Spec run ID (optional)".into(),
                    value: spec
                        .and_then(|spec| spec.spec_run_id.map(|id| id.to_string()))
                        .unwrap_or_default(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::SpecTasks,
        });
    }

    pub(crate) fn open_spec_clarify_modal(&mut self) {
        let spec = self.state.selected_project_spec();
        self.modal = Some(Modal::Form {
            title: "Clarify spec".into(),
            fields: vec![
                InputField {
                    label: "Spec path".into(),
                    value: spec
                        .and_then(|spec| spec.spec_path.clone().or_else(|| Some(spec.path.clone())))
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Spec run ID (optional)".into(),
                    value: spec
                        .and_then(|spec| spec.spec_run_id.map(|id| id.to_string()))
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Notes".into(),
                    value: "".into(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::SpecClarify,
        });
    }

    pub(crate) fn open_spec_checklist_modal(&mut self) {
        let spec = self.state.selected_project_spec();
        self.modal = Some(Modal::Form {
            title: "Checklist spec".into(),
            fields: vec![
                InputField {
                    label: "Spec path".into(),
                    value: spec
                        .and_then(|spec| spec.spec_path.clone().or_else(|| Some(spec.path.clone())))
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Spec run ID (optional)".into(),
                    value: spec
                        .and_then(|spec| spec.spec_run_id.map(|id| id.to_string()))
                        .unwrap_or_default(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::SpecChecklist,
        });
    }

    pub(crate) fn open_spec_analyze_modal(&mut self) {
        let spec = self.state.selected_project_spec();
        self.modal = Some(Modal::Form {
            title: "Analyze spec".into(),
            fields: vec![
                InputField {
                    label: "Spec path".into(),
                    value: spec
                        .and_then(|spec| spec.spec_path.clone().or_else(|| Some(spec.path.clone())))
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Plan path (optional)".into(),
                    value: spec
                        .and_then(|spec| spec.plan_path.clone())
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Tasks path (optional)".into(),
                    value: spec
                        .and_then(|spec| spec.tasks_path.clone())
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Spec run ID (optional)".into(),
                    value: spec
                        .and_then(|spec| spec.spec_run_id.map(|id| id.to_string()))
                        .unwrap_or_default(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::SpecAnalyze,
        });
    }

    pub(crate) fn open_spec_implement_modal(&mut self) {
        let spec = self.state.selected_project_spec();
        self.modal = Some(Modal::Form {
            title: "Implement spec".into(),
            fields: vec![
                InputField {
                    label: "Spec path".into(),
                    value: spec
                        .and_then(|spec| spec.spec_path.clone().or_else(|| Some(spec.path.clone())))
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Spec run ID (optional)".into(),
                    value: spec
                        .and_then(|spec| spec.spec_run_id.map(|id| id.to_string()))
                        .unwrap_or_default(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::SpecImplement,
        });
    }

    pub(crate) fn open_spec_cleanup_modal(&mut self) {
        let spec_run = self
            .state
            .selected_project_spec()
            .and_then(|spec| spec.spec_run_id)
            .map(|id| id.to_string())
            .unwrap_or_default();
        self.modal = Some(Modal::Form {
            title: "Cleanup spec run".into(),
            fields: vec![
                InputField {
                    label: "Spec run ID".into(),
                    value: spec_run,
                    is_secret: false,
                },
                InputField {
                    label: "Delete remote branch? (y/N)".into(),
                    value: "n".into(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::SpecCleanup,
        });
    }

    pub(crate) fn open_agent_assignment_modal(&mut self) {
        let first_process = self
            .state
            .agent_assignments
            .as_ref()
            .and_then(|assignments| assignments.assignments.keys().next().cloned())
            .unwrap_or_else(|| "planning".into());
        let current_agent = self
            .state
            .selected_agent_id()
            .map(str::to_string)
            .unwrap_or_default();
        self.modal = Some(Modal::Form {
            title: "Assign process to agent".into(),
            fields: vec![
                InputField {
                    label: "Process".into(),
                    value: first_process,
                    is_secret: false,
                },
                InputField {
                    label: "Agent ID".into(),
                    value: current_agent,
                    is_secret: false,
                },
                InputField {
                    label: "Prompt ID (optional)".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Model override (optional)".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Enabled? (y/N)".into(),
                    value: "y".into(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::AgentAssign,
        });
    }

    pub(crate) fn open_agent_config_modal(&mut self) {
        let Some(agent) = self.state.agent_detail.clone() else {
            self.state.last_error = Some("Select an agent first".into());
            return;
        };
        let title = if let Some(project_id) = self.state.selected_project_id() {
            format!("Configure agent {} (project {project_id})", agent.id)
        } else {
            format!("Configure agent {}", agent.id)
        };
        self.modal = Some(Modal::Form {
            title,
            fields: vec![
                InputField {
                    label: "Name".into(),
                    value: agent.name,
                    is_secret: false,
                },
                InputField {
                    label: "Kind".into(),
                    value: agent.kind,
                    is_secret: false,
                },
                InputField {
                    label: "Enabled? (y/N)".into(),
                    value: if agent.enabled.unwrap_or(false) {
                        "y"
                    } else {
                        "n"
                    }
                    .into(),
                    is_secret: false,
                },
                InputField {
                    label: "Default model".into(),
                    value: agent.default_model.unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Reasoning effort".into(),
                    value: agent.reasoning_effort.unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Capabilities (comma-separated)".into(),
                    value: agent.capabilities.join(", "),
                    is_secret: false,
                },
                InputField {
                    label: "Command dir".into(),
                    value: agent.command_dir.unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Command".into(),
                    value: agent.command.unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Endpoint".into(),
                    value: agent.endpoint.unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Sandbox".into(),
                    value: agent.sandbox.unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Format".into(),
                    value: agent.format.unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Timeout seconds".into(),
                    value: agent
                        .timeout_seconds
                        .map(|value| value.to_string())
                        .unwrap_or_default(),
                    is_secret: false,
                },
                InputField {
                    label: "Max retries".into(),
                    value: agent
                        .max_retries
                        .map(|value| value.to_string())
                        .unwrap_or_default(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::AgentConfig,
        });
    }

    pub(crate) fn open_cm_modal(&mut self) {
        self.modal = Some(Modal::Form {
            title: "Import CodeMachine".into(),
            fields: vec![
                InputField {
                    label: "Protocol name".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Workspace path".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Base branch".into(),
                    value: "main".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Description (optional)".into(),
                    value: "".into(),
                    is_secret: false,
                },
                InputField {
                    label: "Enqueue? (y/N)".into(),
                    value: "y".into(),
                    is_secret: false,
                },
            ],
            focus: 0,
            action: ModalAction::ImportCodeMachine,
        });
    }

    pub(crate) fn open_action_palette(&mut self) {
        let mut items = match self.state.page {
            Page::Chat => vec![
                QuickAction::CreateProject,
                QuickAction::CreateProtocol,
                QuickAction::StartProtocol,
                QuickAction::ResumeProtocol,
                QuickAction::Search,
                QuickAction::TestAgent,
                QuickAction::Configure,
                QuickAction::Menu,
            ],
            Page::Agents => vec![
                QuickAction::Configure,
                QuickAction::TestAgent,
                QuickAction::AssignAgent,
                QuickAction::Search,
                QuickAction::Menu,
            ],
            Page::Dashboard => vec![
                QuickAction::CreateProject,
                QuickAction::CreateProtocol,
                QuickAction::RunNext,
                QuickAction::RetryLatest,
                QuickAction::RunQa,
                QuickAction::Approve,
                QuickAction::OpenPr,
                QuickAction::StartProtocol,
                QuickAction::PauseProtocol,
                QuickAction::ResumeProtocol,
                QuickAction::CancelProtocol,
                QuickAction::ImportCodeMachine,
                QuickAction::SpecAudit,
                QuickAction::Search,
                QuickAction::OpenLink,
                QuickAction::CopyLink,
                QuickAction::Configure,
                QuickAction::Menu,
            ],
            _ => vec![
                QuickAction::RunNext,
                QuickAction::RetryLatest,
                QuickAction::RunQa,
                QuickAction::Approve,
                QuickAction::OpenPr,
                QuickAction::StartProtocol,
                QuickAction::PauseProtocol,
                QuickAction::ResumeProtocol,
                QuickAction::CancelProtocol,
                QuickAction::ImportCodeMachine,
                QuickAction::SpecAudit,
                QuickAction::Search,
                QuickAction::OpenLink,
                QuickAction::CopyLink,
                QuickAction::Configure,
                QuickAction::Menu,
            ],
        };
        if self.state.page == Page::Projects {
            items.splice(
                0..0,
                [QuickAction::CreateProject, QuickAction::CreateProtocol],
            );
            items.push(QuickAction::DuplicateProject);
            if self.state.project_workspace_tab == ProjectWorkspaceTab::Specs {
                items.extend([
                    QuickAction::SpecInit,
                    QuickAction::SpecGenerate,
                    QuickAction::SpecPlan,
                    QuickAction::SpecTasks,
                    QuickAction::SpecClarify,
                    QuickAction::SpecChecklist,
                    QuickAction::SpecAnalyze,
                    QuickAction::SpecImplement,
                    QuickAction::SpecCleanup,
                ]);
            }
        }
        self.modal = Some(Modal::Palette { items, index: 0 });
    }

    pub(crate) fn open_delete_branch_modal(&mut self) {
        if let Some(idx) = self.state.branch_index {
            if let Some(branch) = self.state.branches.get(idx) {
                self.modal = Some(Modal::Confirm {
                    title: "Delete branch".into(),
                    message: format!("Delete branch '{}'?", branch.name),
                    action: ModalAction::DeleteBranch,
                });
            }
        }
    }

    pub(crate) fn open_archive_project_modal(&mut self) {
        if let Some(project) = self.state.selected_project() {
            self.modal = Some(Modal::Confirm {
                title: "Archive project".into(),
                message: format!("Archive project '{}'?", project.name),
                action: ModalAction::ArchiveProject,
            });
        }
    }

    pub(crate) fn open_unarchive_project_modal(&mut self) {
        if let Some(project) = self.state.selected_project() {
            self.modal = Some(Modal::Confirm {
                title: "Unarchive project".into(),
                message: format!("Unarchive project '{}'?", project.name),
                action: ModalAction::UnarchiveProject,
            });
        }
    }

    pub(crate) fn open_delete_project_modal(&mut self) {
        if let Some(project) = self.state.selected_project() {
            self.modal = Some(Modal::Confirm {
                title: "Delete project".into(),
                message: format!("Delete project '{}' and all related data?", project.name),
                action: ModalAction::DeleteProject,
            });
        }
    }

    pub(crate) async fn handle_modal_key(&mut self, key: &KeyEvent) -> Result<bool> {
        if self.modal.is_none() {
            return Ok(false);
        }
        let available_models = self.agent_available_model_values();
        let current_model = self
            .modal
            .as_ref()
            .and_then(|modal| match modal {
                Modal::Form { fields, .. } => {
                    fields.get(3).map(|field| field.value.trim().to_string())
                }
                _ => None,
            })
            .unwrap_or_default();
        let available_reasoning =
            self.agent_available_reasoning_values_for_model(current_model.as_str());
        match self.modal.as_mut().unwrap() {
            Modal::Confirm { action, .. } => {
                if key.code == KeyCode::Enter {
                    let action = *action;
                    self.modal = None;
                    self.handle_modal_submit(action).await?;
                } else if key.code == KeyCode::Esc {
                    self.modal = None;
                }
                return Ok(true);
            }
            Modal::Palette { items, index } => {
                match key.code {
                    KeyCode::Up | KeyCode::Char('k') => {
                        if *index == 0 {
                            *index = items.len().saturating_sub(1);
                        } else {
                            *index -= 1;
                        }
                    }
                    KeyCode::Down | KeyCode::Char('j') => {
                        *index = (*index + 1) % items.len();
                    }
                    KeyCode::Enter => {
                        let action = items.get(*index).copied();
                        self.modal = None;
                        if let Some(act) = action {
                            self.run_quick_action(act).await?;
                        }
                    }
                    KeyCode::Esc => {
                        self.modal = None;
                    }
                    _ => {}
                }
                return Ok(true);
            }
            Modal::Form {
                fields,
                focus,
                action,
                ..
            } => {
                let is_agent_config = matches!(action, ModalAction::AgentConfig);
                match key.code {
                    KeyCode::Tab => {
                        *focus = (*focus + 1) % fields.len();
                    }
                    KeyCode::BackTab => {
                        if *focus == 0 {
                            *focus = fields.len() - 1;
                        } else {
                            *focus -= 1;
                        }
                    }
                    KeyCode::Enter => {
                        let action = *action;
                        let data = fields.clone();
                        self.modal = None;
                        self.handle_form_submit(action, data).await?;
                    }
                    KeyCode::Esc => {
                        self.modal = None;
                    }
                    KeyCode::Up
                        if is_agent_config
                            && *focus == 3
                            && !key.modifiers.contains(KeyModifiers::SHIFT) =>
                    {
                        Self::cycle_agent_model_field(fields, -1, &available_models);
                    }
                    KeyCode::Down
                        if is_agent_config
                            && *focus == 3
                            && !key.modifiers.contains(KeyModifiers::SHIFT) =>
                    {
                        Self::cycle_agent_model_field(fields, 1, &available_models);
                    }
                    KeyCode::Char('k')
                        if is_agent_config
                            && *focus == 3
                            && key.modifiers.contains(KeyModifiers::CONTROL) =>
                    {
                        Self::cycle_agent_model_field(fields, -1, &available_models);
                    }
                    KeyCode::Char('j')
                        if is_agent_config
                            && *focus == 3
                            && key.modifiers.contains(KeyModifiers::CONTROL) =>
                    {
                        Self::cycle_agent_model_field(fields, 1, &available_models);
                    }
                    KeyCode::Up
                        if is_agent_config
                            && *focus == 4
                            && !key.modifiers.contains(KeyModifiers::SHIFT) =>
                    {
                        Self::cycle_agent_reasoning_field(fields, -1, &available_reasoning);
                    }
                    KeyCode::Down
                        if is_agent_config
                            && *focus == 4
                            && !key.modifiers.contains(KeyModifiers::SHIFT) =>
                    {
                        Self::cycle_agent_reasoning_field(fields, 1, &available_reasoning);
                    }
                    KeyCode::Char('k')
                        if is_agent_config
                            && *focus == 4
                            && key.modifiers.contains(KeyModifiers::CONTROL) =>
                    {
                        Self::cycle_agent_reasoning_field(fields, -1, &available_reasoning);
                    }
                    KeyCode::Char('j')
                        if is_agent_config
                            && *focus == 4
                            && key.modifiers.contains(KeyModifiers::CONTROL) =>
                    {
                        Self::cycle_agent_reasoning_field(fields, 1, &available_reasoning);
                    }
                    KeyCode::Char('u') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                        if let Some(field) = fields.get_mut(*focus) {
                            field.value.clear();
                        }
                    }
                    KeyCode::Backspace => {
                        if let Some(field) = fields.get_mut(*focus) {
                            field.value.pop();
                        }
                    }
                    KeyCode::Char(c) => {
                        if let Some(field) = fields.get_mut(*focus) {
                            field.value.push(c);
                        }
                    }
                    _ => {}
                }
                return Ok(true);
            }
        }
    }

    pub(crate) async fn handle_modal_submit(&mut self, action: ModalAction) -> Result<()> {
        match action {
            ModalAction::DeleteBranch
            | ModalAction::SpecInit
            | ModalAction::ArchiveProject
            | ModalAction::UnarchiveProject
            | ModalAction::DeleteProject => self.handle_form_submit(action, vec![]).await?,
            _ => {}
        }
        Ok(())
    }
}
