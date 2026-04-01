use super::App;
use crate::state::{ChatFlowState, ChatMessageKind, Page};
use anyhow::Result;
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use serde_json::Value;

impl App {
    pub(crate) fn ensure_chat_seeded(&mut self) {
        if !self.state.chat_messages.is_empty() {
            return;
        }
        self.state.push_chat_message(
            ChatMessageKind::Agent,
            "Chat workspace ready. I can inspect project state, run brownfield flow, start or resume protocols, and show progress inline.",
        );
        self.state.push_chat_message(
            ChatMessageKind::Tool,
            "Try: /flow list, /agent use codex, /flow run brownfield <feature request>, /flow resume, /step show <id>, /run show <run_id>",
        );
    }

    pub(crate) async fn handle_chat_key(&mut self, key: &KeyEvent) -> Result<bool> {
        if self.state.page != Page::Chat {
            return Ok(false);
        }

        if key.modifiers.contains(KeyModifiers::CONTROL) {
            match key.code {
                KeyCode::Char('j') | KeyCode::Down => {
                    if self.state.agents.is_empty() {
                        self.load_chat_agents().await?;
                    }
                    self.state.select_agent(1);
                    self.state.status = "Chat agent selected".into();
                    return Ok(true);
                }
                KeyCode::Char('k') | KeyCode::Up => {
                    if self.state.agents.is_empty() {
                        self.load_chat_agents().await?;
                    }
                    self.state.select_agent(-1);
                    self.state.status = "Chat agent selected".into();
                    return Ok(true);
                }
                _ => return Ok(false),
            }
        }

        match key.code {
            KeyCode::Enter => {
                if self.state.composer_input.trim().is_empty() {
                    self.open_action_palette();
                } else {
                    self.submit_chat_input().await?;
                }
                Ok(true)
            }
            KeyCode::Esc => {
                if !self.state.composer_input.is_empty() {
                    self.state.composer_input.clear();
                    self.state.status = "Composer cleared".into();
                    return Ok(true);
                }
                Ok(false)
            }
            KeyCode::Backspace => {
                self.state.composer_input.pop();
                Ok(true)
            }
            KeyCode::Up | KeyCode::Char('k')
                if self.state.composer_input.is_empty()
                    && !key.modifiers.contains(KeyModifiers::ALT) =>
            {
                self.state.select_project(-1);
                self.schedule_selection_refresh("Loading chat project...");
                Ok(true)
            }
            KeyCode::Down | KeyCode::Char('j')
                if self.state.composer_input.is_empty()
                    && !key.modifiers.contains(KeyModifiers::ALT) =>
            {
                self.state.select_project(1);
                self.schedule_selection_refresh("Loading chat project...");
                Ok(true)
            }
            KeyCode::Char(ch)
                if !key.modifiers.contains(KeyModifiers::ALT)
                    && !key.modifiers.contains(KeyModifiers::CONTROL) =>
            {
                self.state.composer_input.push(ch);
                Ok(true)
            }
            _ => Ok(false),
        }
    }

    pub(crate) async fn submit_chat_input(&mut self) -> Result<()> {
        let input = self.state.composer_input.trim().to_string();
        self.state.composer_input.clear();
        if input.is_empty() {
            return Ok(());
        }
        self.state
            .push_chat_message(ChatMessageKind::User, format!("You> {input}"));
        self.dispatch_chat_message(&input).await
    }

    async fn dispatch_chat_message(&mut self, input: &str) -> Result<()> {
        self.ensure_chat_seeded();
        if input.starts_with('/') {
            self.handle_chat_command(input).await?;
        } else {
            self.handle_chat_natural_language(input).await?;
        }
        Ok(())
    }

    async fn handle_chat_natural_language(&mut self, input: &str) -> Result<()> {
        let lower = input.to_ascii_lowercase();
        if lower.contains("brownfield") || lower.contains("context build") {
            self.run_brownfield_flow(input, None).await?;
            return Ok(());
        }
        if lower.contains("resume protocol") || lower.contains("continue protocol") {
            self.resume_selected_protocol().await?;
            return Ok(());
        }
        if lower.contains("start protocol") {
            self.start_selected_protocol().await?;
            return Ok(());
        }
        if lower.contains("run qa") || lower == "qa" {
            self.run_qa_latest().await?;
            self.state
                .push_chat_message(ChatMessageKind::Flow, "QA requested for the selected step.");
            return Ok(());
        }

        self.state.push_chat_message(
            ChatMessageKind::Agent,
            "I can route this through an existing flow, but I need a clearer intent. Try `/flow list`, `/flow run brownfield <request>`, `/flow resume`, or `/agent use <id>`.",
        );
        Ok(())
    }

    async fn handle_chat_command(&mut self, input: &str) -> Result<()> {
        let trimmed = input.trim();
        let mut parts = trimmed.split_whitespace();
        let command = parts.next().unwrap_or_default();
        match command {
            "/help" => self.chat_help(),
            "/flow" => self.handle_flow_command(parts.collect::<Vec<_>>()).await?,
            "/agent" => self.handle_agent_command(parts.collect::<Vec<_>>()).await?,
            "/project" => {
                self.handle_project_command(parts.collect::<Vec<_>>())
                    .await?
            }
            "/protocol" => {
                self.handle_protocol_command(parts.collect::<Vec<_>>())
                    .await?
            }
            "/step" => self.handle_step_command(parts.collect::<Vec<_>>()).await?,
            "/run" => self.handle_run_command(parts.collect::<Vec<_>>()).await?,
            "/logs" => self.handle_logs_command(parts.collect::<Vec<_>>()).await?,
            _ => self
                .state
                .push_chat_message(ChatMessageKind::Warn, format!("Unknown command: {trimmed}")),
        }
        Ok(())
    }

    async fn handle_flow_command(&mut self, args: Vec<&str>) -> Result<()> {
        if args.is_empty() || args[0] == "list" {
            self.state.push_chat_message(
                ChatMessageKind::Agent,
                "Available flows: brownfield, protocol, protocol_resume, protocol_cancel, retry, qa, approve, spec_init, spec_generate, agent_test",
            );
            return Ok(());
        }

        match args[0] {
            "run" => match args.get(1).copied().unwrap_or_default() {
                "brownfield" => {
                    let request = args
                        .get(2..)
                        .map(|parts| parts.join(" "))
                        .unwrap_or_default();
                    if request.trim().is_empty() {
                        self.state.push_chat_message(
                            ChatMessageKind::Warn,
                            "Usage: /flow run brownfield <feature request>",
                        );
                    } else {
                        self.run_brownfield_flow(&request, None).await?;
                    }
                }
                "protocol" => {
                    self.start_selected_protocol().await?;
                }
                "spec_init" => {
                    self.run_spec_init().await?;
                }
                "spec_generate" => {
                    let request = args
                        .get(2..)
                        .map(|parts| parts.join(" "))
                        .unwrap_or_default();
                    if request.trim().is_empty() {
                        self.state.push_chat_message(
                            ChatMessageKind::Warn,
                            "Usage: /flow run spec_generate <feature request>",
                        );
                    } else {
                        self.run_spec_generate(&request).await?;
                    }
                }
                "agent_test" => {
                    self.run_agent_test().await?;
                    self.state.push_chat_message(
                        ChatMessageKind::Check,
                        "Agent test executed for the selected agent.",
                    );
                }
                other => self
                    .state
                    .push_chat_message(ChatMessageKind::Warn, format!("Unknown flow: {other}")),
            },
            "resume" => self.resume_selected_protocol().await?,
            "cancel" => self.cancel_selected_protocol().await?,
            "retry" => {
                self.retry_latest().await?;
                self.state
                    .push_chat_message(ChatMessageKind::Flow, "Retry requested.");
            }
            "qa" => {
                self.run_qa_latest().await?;
                self.state
                    .push_chat_message(ChatMessageKind::Flow, "QA requested.");
            }
            "approve" => {
                self.approve_latest().await?;
                self.state
                    .push_chat_message(ChatMessageKind::Check, "Approval requested.");
            }
            _ => self.state.push_chat_message(
                ChatMessageKind::Warn,
                format!("Unsupported /flow command: {}", args.join(" ")),
            ),
        }
        Ok(())
    }

    async fn handle_agent_command(&mut self, args: Vec<&str>) -> Result<()> {
        match args.as_slice() {
            ["use", token] => {
                if self.select_agent_from_token(token) {
                    self.schedule_selection_refresh(format!("Loading agent {token}..."));
                    self.state.push_chat_message(
                        ChatMessageKind::Agent,
                        format!("Selected agent {token}."),
                    );
                } else {
                    self.state.push_chat_message(
                        ChatMessageKind::Warn,
                        format!("Agent not found: {token}"),
                    );
                }
            }
            ["show", token] => {
                if self.select_agent_from_token(token) {
                    self.load_selected_agent_detail().await?;
                    self.state.push_chat_message(
                        ChatMessageKind::Tool,
                        format!("Fetching agent details for {token}."),
                    );
                } else {
                    self.state.push_chat_message(
                        ChatMessageKind::Warn,
                        format!("Agent not found: {token}"),
                    );
                }
            }
            _ => self.state.push_chat_message(
                ChatMessageKind::Warn,
                "Usage: /agent use <id> | /agent show <id>",
            ),
        }
        Ok(())
    }

    async fn handle_project_command(&mut self, args: Vec<&str>) -> Result<()> {
        match args.as_slice() {
            ["use", token] => {
                if self.select_project_from_token(token) {
                    self.schedule_selection_refresh(format!("Loading project {token}..."));
                    self.state.push_chat_message(
                        ChatMessageKind::Agent,
                        format!("Selected project {token}."),
                    );
                } else {
                    self.state.push_chat_message(
                        ChatMessageKind::Warn,
                        format!("Project not found: {token}"),
                    );
                }
            }
            ["show", token] => {
                if self.select_project_from_token(token) {
                    self.schedule_selection_refresh(format!("Loading project {token}..."));
                    self.state.push_chat_message(
                        ChatMessageKind::Tool,
                        format!("Loading project summary for {token}."),
                    );
                } else {
                    self.state.push_chat_message(
                        ChatMessageKind::Warn,
                        format!("Project not found: {token}"),
                    );
                }
            }
            _ => self.state.push_chat_message(
                ChatMessageKind::Warn,
                "Usage: /project use <id|name> | /project show <id|name>",
            ),
        }
        Ok(())
    }

    async fn handle_protocol_command(&mut self, args: Vec<&str>) -> Result<()> {
        match args.as_slice() {
            ["use", token] | ["show", token] => {
                if let Ok(protocol_id) = token.parse::<i64>() {
                    self.state.select_protocol_by_id(protocol_id);
                    self.schedule_selection_refresh(format!("Loading protocol {protocol_id}..."));
                    self.state.push_chat_message(
                        ChatMessageKind::Tool,
                        format!("Selected protocol {protocol_id}."),
                    );
                } else {
                    self.state.push_chat_message(
                        ChatMessageKind::Warn,
                        "Protocol selection currently supports numeric protocol IDs.",
                    );
                }
            }
            _ => self.state.push_chat_message(
                ChatMessageKind::Warn,
                "Usage: /protocol use <id> | /protocol show <id>",
            ),
        }
        Ok(())
    }

    async fn handle_step_command(&mut self, args: Vec<&str>) -> Result<()> {
        match args.as_slice() {
            ["show", token] => match token.parse::<i64>() {
                Ok(step_id) => {
                    self.state.select_step_by_id(step_id);
                    self.schedule_selection_refresh(format!("Loading step {step_id}..."));
                    self.state.push_chat_message(
                        ChatMessageKind::Tool,
                        format!("Selected step {step_id}."),
                    );
                }
                Err(_) => self.state.push_chat_message(
                    ChatMessageKind::Warn,
                    "Step selection currently supports numeric step IDs.",
                ),
            },
            _ => self
                .state
                .push_chat_message(ChatMessageKind::Warn, "Usage: /step show <id>"),
        }
        Ok(())
    }

    async fn handle_run_command(&mut self, args: Vec<&str>) -> Result<()> {
        match args.as_slice() {
            ["show", run_id] => {
                self.select_run_from_token(run_id);
                self.state
                    .push_chat_message(ChatMessageKind::Tool, format!("Selected run {run_id}."));
                self.load_run_workspace().await?;
            }
            _ => self
                .state
                .push_chat_message(ChatMessageKind::Warn, "Usage: /run show <run_id>"),
        }
        Ok(())
    }

    async fn handle_logs_command(&mut self, args: Vec<&str>) -> Result<()> {
        match args.as_slice() {
            ["run", run_id] => {
                self.select_run_from_token(run_id);
                self.load_run_workspace().await?;
                self.state.push_chat_message(
                    ChatMessageKind::Tool,
                    format!("Loaded logs for run {run_id}."),
                );
            }
            _ => self
                .state
                .push_chat_message(ChatMessageKind::Warn, "Usage: /logs run <run_id>"),
        }
        Ok(())
    }

    fn chat_help(&mut self) {
        self.state.push_chat_message(
            ChatMessageKind::Agent,
            "Commands: /flow list, /flow run brownfield <request>, /flow run protocol, /flow resume, /flow cancel, /flow retry, /flow qa, /flow approve, /agent use <id>, /project use <id>, /protocol show <id>, /step show <id>, /run show <id>",
        );
    }

    async fn run_brownfield_flow(
        &mut self,
        feature_request: &str,
        feature_name: Option<String>,
    ) -> Result<()> {
        let Some(project_id) = self.state.selected_project_id() else {
            self.state.push_chat_message(
                ChatMessageKind::Warn,
                "Select a project first with /project use <id> before starting brownfield flow.",
            );
            return Ok(());
        };
        let owner_agent = self.state.selected_agent_id().map(str::to_string);
        self.state.push_chat_message(
            ChatMessageKind::Agent,
            format!(
                "Starting brownfield flow for project {} using {}.",
                self.state
                    .selected_project()
                    .map(|project| project.name.as_str())
                    .unwrap_or("-"),
                owner_agent.as_deref().unwrap_or("default agent")
            ),
        );
        match self
            .client
            .start_brownfield_run(project_id, feature_request, feature_name, owner_agent)
            .await
        {
            Ok(result) => {
                self.state.last_brownfield_run = Some(result.clone());
                if let Some(protocol) = result.protocol.clone() {
                    self.state
                        .protocols
                        .retain(|existing| existing.id != protocol.id);
                    self.state.protocols.insert(0, protocol.clone());
                    self.state.select_protocol_by_id(protocol.id);
                    if let Some(step_id) = result.next_work_item_id {
                        self.state.select_step_by_id(step_id);
                    }
                    self.state.active_flow = Some(ChatFlowState {
                        kind: "brownfield".into(),
                        label: protocol.protocol_name.clone(),
                        status: protocol.status.clone().unwrap_or_else(|| "queued".into()),
                        stage: Some("queued".into()),
                        protocol_id: Some(protocol.id),
                        step_id: result.next_work_item_id,
                        run_id: None,
                        summary: Some(
                            result
                                .tasks_path
                                .clone()
                                .unwrap_or_else(|| "Brownfield bootstrap queued".into()),
                        ),
                        last_tool: Some("POST /projects/{id}/brownfield/run".into()),
                        artifact_hint: result.spec_path.clone().or(result.plan_path.clone()),
                        waiting_on: Some("queue".into()),
                        operator_hint: Some(
                            "Flow is queued. Wait for bootstrap events or use /protocol show <id>."
                                .into(),
                        ),
                        last_event: Some("brownfield bootstrap queued".into()),
                        updated_at: protocol.updated_at.clone(),
                    });
                    self.state.push_chat_message(
                        ChatMessageKind::Flow,
                        format!(
                            "brownfield_feature queued • protocol={} • next_step={}",
                            protocol.id,
                            result
                                .next_work_item_id
                                .map(|value| value.to_string())
                                .unwrap_or_else(|| "-".into())
                        ),
                    );
                } else {
                    self.state.push_chat_message(
                        ChatMessageKind::Flow,
                        "brownfield_feature queued without protocol payload",
                    );
                }
                for warning in result.warnings {
                    self.state.push_chat_message(ChatMessageKind::Warn, warning);
                }
                self.schedule_refresh("Refreshing brownfield flow...");
            }
            Err(err) => {
                self.set_error(err);
                self.state.push_chat_message(
                    ChatMessageKind::Warn,
                    self.state
                        .last_error
                        .clone()
                        .unwrap_or_else(|| "Brownfield run failed".into()),
                );
            }
        }
        Ok(())
    }

    async fn start_selected_protocol(&mut self) -> Result<()> {
        if let Some(protocol_id) = self.state.selected_protocol_id() {
            self.protocol_action("start", "Planning enqueued.").await?;
            self.state.active_flow = Some(ChatFlowState {
                kind: "protocol".into(),
                label: self
                    .state
                    .protocols
                    .iter()
                    .find(|protocol| protocol.id == protocol_id)
                    .map(|protocol| protocol.protocol_name.clone())
                    .unwrap_or_else(|| format!("protocol-{protocol_id}")),
                status: "starting".into(),
                stage: Some("starting".into()),
                protocol_id: Some(protocol_id),
                step_id: self.state.selected_step_id(),
                run_id: None,
                summary: Some("Protocol start requested".into()),
                last_tool: Some("POST /protocols/{id}/actions/start".into()),
                artifact_hint: None,
                waiting_on: Some("queue".into()),
                operator_hint: Some(
                    "Protocol start requested. Waiting for backend progress.".into(),
                ),
                last_event: Some("protocol start requested".into()),
                updated_at: None,
            });
            self.state.push_chat_message(
                ChatMessageKind::Flow,
                format!("Protocol {protocol_id} start requested."),
            );
        } else {
            self.state
                .push_chat_message(ChatMessageKind::Warn, "Select a protocol first.");
        }
        Ok(())
    }

    async fn resume_selected_protocol(&mut self) -> Result<()> {
        if let Some(protocol_id) = self.state.selected_protocol_id() {
            self.protocol_action("resume", "Protocol resumed.").await?;
            if let Some(flow) = self.state.active_flow.as_mut() {
                flow.status = "running".into();
                flow.protocol_id = Some(protocol_id);
            }
            self.state.push_chat_message(
                ChatMessageKind::Flow,
                format!("Protocol {protocol_id} resumed."),
            );
        } else {
            self.state
                .push_chat_message(ChatMessageKind::Warn, "Select a protocol first.");
        }
        Ok(())
    }

    async fn cancel_selected_protocol(&mut self) -> Result<()> {
        if let Some(protocol_id) = self.state.selected_protocol_id() {
            self.protocol_action("cancel", "Protocol cancelled.")
                .await?;
            if let Some(flow) = self.state.active_flow.as_mut() {
                flow.status = "cancelled".into();
                flow.protocol_id = Some(protocol_id);
            }
            self.state.push_chat_message(
                ChatMessageKind::Warn,
                format!("Protocol {protocol_id} cancelled."),
            );
        } else {
            self.state
                .push_chat_message(ChatMessageKind::Warn, "Select a protocol first.");
        }
        Ok(())
    }

    async fn run_spec_init(&mut self) -> Result<()> {
        if let Some(project_id) = self.state.selected_project_id() {
            match self.client.speckit_init(project_id).await {
                Ok(result) => {
                    self.state.push_chat_message(
                        if result.success {
                            ChatMessageKind::Check
                        } else {
                            ChatMessageKind::Warn
                        },
                        if result.success {
                            format!(
                                "SpecKit initialized {}",
                                result.path.unwrap_or_else(|| "-".into())
                            )
                        } else {
                            result.error.unwrap_or_else(|| "SpecKit init failed".into())
                        },
                    );
                    self.schedule_refresh("Refreshing project specs...");
                }
                Err(err) => {
                    self.set_error(err);
                    self.state.push_chat_message(
                        ChatMessageKind::Warn,
                        self.state
                            .last_error
                            .clone()
                            .unwrap_or_else(|| "SpecKit init failed".into()),
                    );
                }
            }
        } else {
            self.state
                .push_chat_message(ChatMessageKind::Warn, "Select a project first.");
        }
        Ok(())
    }

    async fn run_spec_generate(&mut self, request: &str) -> Result<()> {
        if let Some(project_id) = self.state.selected_project_id() {
            match self
                .client
                .speckit_specify(project_id, request, None, None)
                .await
            {
                Ok(result) => {
                    self.state.push_chat_message(
                        if result.success {
                            ChatMessageKind::Flow
                        } else {
                            ChatMessageKind::Warn
                        },
                        if result.success {
                            format!(
                                "Spec generated {}",
                                result.spec_path.unwrap_or_else(|| "-".into())
                            )
                        } else {
                            result
                                .error
                                .unwrap_or_else(|| "Spec generation failed".into())
                        },
                    );
                    self.schedule_refresh("Refreshing project specs...");
                }
                Err(err) => {
                    self.set_error(err);
                    self.state.push_chat_message(
                        ChatMessageKind::Warn,
                        self.state
                            .last_error
                            .clone()
                            .unwrap_or_else(|| "Spec generation failed".into()),
                    );
                }
            }
        } else {
            self.state
                .push_chat_message(ChatMessageKind::Warn, "Select a project first.");
        }
        Ok(())
    }

    fn metadata_str<'a>(metadata: &'a Value, key: &str) -> Option<&'a str> {
        metadata.get(key).and_then(Value::as_str)
    }

    pub(crate) fn refresh_active_flow_status_from_state(&mut self) {
        let Some(flow) = self.state.active_flow.as_mut() else {
            return;
        };

        let protocol = flow.protocol_id.and_then(|protocol_id| {
            self.state
                .protocol_detail
                .as_ref()
                .filter(|protocol| protocol.id == protocol_id)
                .or_else(|| {
                    self.state
                        .protocols
                        .iter()
                        .find(|protocol| protocol.id == protocol_id)
                })
        });

        if let Some(protocol) = protocol {
            flow.label = protocol.protocol_name.clone();
            flow.status = protocol.status.clone().unwrap_or_else(|| "unknown".into());
            flow.updated_at = protocol.updated_at.clone();

            if let Some(metadata) = protocol.speckit_metadata.as_ref() {
                let bootstrap_stage =
                    Self::metadata_str(metadata, "brownfield_bootstrap_stage").map(str::to_string);
                let bootstrap_status =
                    Self::metadata_str(metadata, "brownfield_bootstrap_status").map(str::to_string);
                let bootstrap_error =
                    Self::metadata_str(metadata, "brownfield_bootstrap_error").map(str::to_string);
                if bootstrap_stage.is_some() {
                    flow.stage = bootstrap_stage.clone();
                }
                if flow.kind == "brownfield" {
                    if let Some(error) = bootstrap_error {
                        flow.status = "failed".into();
                        flow.waiting_on = Some("error".into());
                        flow.summary = Some(error);
                        flow.operator_hint =
                            Some("Flow failed. Inspect recent events and artifacts.".into());
                    } else if let Some(stage) = bootstrap_stage {
                        match bootstrap_status.as_deref() {
                            Some("running") => {
                                flow.status = format!("{stage} running");
                                flow.waiting_on = Some("agent".into());
                                flow.summary = Some(format!(
                                    "Agent is executing brownfield bootstrap stage `{stage}`."
                                ));
                                flow.operator_hint = Some(
                                    "Work is in progress. Wait for the next event or inspect logs."
                                        .into(),
                                );
                            }
                            Some("queued") => {
                                flow.status = format!("{stage} queued");
                                flow.waiting_on = Some("queue".into());
                                flow.summary = Some(format!(
                                    "Brownfield bootstrap stage `{stage}` is queued."
                                ));
                                flow.operator_hint = Some(
                                    "Waiting for backend worker to pick up the next stage.".into(),
                                );
                            }
                            Some("completed") => {
                                flow.status = "completed".into();
                                flow.waiting_on = None;
                                flow.summary = Some("Brownfield bootstrap completed.".into());
                                flow.operator_hint = Some(
                                    "Bootstrap finished. Continue with protocol execution.".into(),
                                );
                            }
                            Some("failed") => {
                                flow.status = "failed".into();
                                flow.waiting_on = Some("error".into());
                                flow.operator_hint = Some(
                                    "Bootstrap failed. Inspect events for the failing stage."
                                        .into(),
                                );
                            }
                            _ => {}
                        }
                    }
                }
            }
        }

        if !self.state.protocol_clarifications.is_empty() {
            flow.waiting_on = Some("you".into());
            flow.operator_hint = Some(
                "Protocol has open clarifications. Answer them before work can continue.".into(),
            );
            if flow.summary.is_none() {
                flow.summary = Some("Waiting for operator clarification.".into());
            }
        }

        if let Some(event) = self
            .state
            .recent_events
            .iter()
            .filter(|event| event.protocol_run_id == flow.protocol_id)
            .max_by(|a, b| a.created_at.cmp(&b.created_at))
        {
            flow.last_event = Some(format!("{}: {}", event.event_type, event.message));
        }
    }

    pub(crate) fn sync_chat_events(&mut self) {
        self.ensure_chat_seeded();
        let active_protocol_id = self
            .state
            .active_flow
            .as_ref()
            .and_then(|flow| flow.protocol_id)
            .or_else(|| self.state.selected_protocol_id());

        let mut additions = Vec::new();
        for event in &self.state.recent_events {
            let relevant = active_protocol_id
                .map(|protocol_id| event.protocol_run_id == Some(protocol_id))
                .unwrap_or_else(|| event.message.to_ascii_lowercase().contains("brownfield"));
            if !relevant {
                continue;
            }
            let key = format!(
                "{}:{}:{}",
                event.created_at, event.event_type, event.message
            );
            if self
                .state
                .seen_chat_event_keys
                .iter()
                .any(|seen| seen == &key)
            {
                continue;
            }
            additions.push((key, event.event_type.clone(), event.message.clone()));
        }

        for (key, event_type, message) in additions {
            let kind = if event_type.contains("failed") {
                ChatMessageKind::Warn
            } else if event_type.contains("qa") {
                ChatMessageKind::Check
            } else if event_type.contains("step") {
                ChatMessageKind::Step
            } else {
                ChatMessageKind::Flow
            };
            self.state
                .push_chat_message(kind, format!("[{event_type}] {message}"));
            self.state.seen_chat_event_keys.push(key);
            if let Some(flow) = self.state.active_flow.as_mut() {
                flow.last_event = Some(format!("{event_type}: {message}"));
                if event_type.contains("failed") {
                    flow.status = "failed".into();
                    flow.waiting_on = Some("error".into());
                    flow.operator_hint =
                        Some("Flow failed. Inspect the latest event and artifacts.".into());
                    flow.summary = Some(message.clone());
                } else if event_type.contains("clarif") {
                    flow.waiting_on = Some("you".into());
                    flow.operator_hint =
                        Some("Flow is waiting for your clarification before continuing.".into());
                    flow.summary = Some(message.clone());
                } else if event_type.contains("started") {
                    flow.waiting_on = Some("agent".into());
                    flow.operator_hint =
                        Some("Agent is actively working on the current stage.".into());
                    flow.summary = Some(message.clone());
                } else if event_type.contains("completed") {
                    flow.summary = Some(message.clone());
                }
            }
        }
        if self.state.seen_chat_event_keys.len() > 300 {
            let overflow = self.state.seen_chat_event_keys.len().saturating_sub(300);
            self.state.seen_chat_event_keys.drain(0..overflow);
        }
        self.refresh_active_flow_status_from_state();
    }

    fn select_project_from_token(&mut self, token: &str) -> bool {
        if let Ok(project_id) = token.parse::<i64>() {
            self.state.select_project_by_id(project_id);
            return self.state.project_index.is_some();
        }
        let needle = token.to_ascii_lowercase();
        self.state.project_index = self
            .state
            .projects
            .iter()
            .position(|project| project.name.to_ascii_lowercase().contains(&needle));
        self.state.project_index.is_some()
    }

    fn select_agent_from_token(&mut self, token: &str) -> bool {
        self.state.select_agent_by_id(token);
        if self.state.agent_index.is_some() {
            return true;
        }
        let needle = token.to_ascii_lowercase();
        self.state.agent_index = self.state.agents.iter().position(|agent| {
            agent.id.to_ascii_lowercase().contains(&needle)
                || agent.name.to_ascii_lowercase().contains(&needle)
        });
        self.state.agent_index.is_some()
    }

    fn select_run_from_token(&mut self, token: &str) {
        self.state.run_index = self
            .state
            .runs
            .iter()
            .position(|run| run.run_id == token || run.run_id.starts_with(token));
        if self.state.run_index.is_none() {
            self.state.runs.insert(
                0,
                crate::models::JobRun {
                    run_id: token.to_string(),
                    ..Default::default()
                },
            );
            self.state.run_index = Some(0);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        api::ApiClient,
        models::{AgentInfo, Project},
    };
    use std::{
        io::{Read, Write},
        net::TcpListener,
        thread,
        time::Duration,
    };

    fn spawn_brownfield_chat_server() -> (String, thread::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind test server");
        let addr = listener.local_addr().expect("local addr");
        let handle = thread::spawn(move || {
            for _ in 0..2 {
                let (mut stream, _) = listener.accept().expect("accept");
                let mut buf = [0_u8; 8192];
                let read = stream.read(&mut buf).expect("read request");
                let req = String::from_utf8_lossy(&buf[..read]);
                let request_line = req.lines().next().unwrap_or_default();
                let body = if request_line.starts_with("POST /projects/11/brownfield/run ") {
                    serde_json::json!({
                        "success": true,
                        "project_id": 11,
                        "output_mode": "task_cycle",
                        "spec_run_id": 901,
                        "spec_path": ".specify/specs/db-integration/spec.md",
                        "plan_path": ".specify/specs/db-integration/plan.md",
                        "tasks_path": ".specify/specs/db-integration/tasks.md",
                        "protocol": {
                            "id": 88,
                            "project_id": 11,
                            "protocol_name": "db-integration",
                            "status": "queued",
                            "summary": "Brownfield bootstrap queued"
                        },
                        "next_work_item_id": 331,
                        "warnings": []
                    })
                    .to_string()
                } else if request_line.starts_with("GET /events?limit=50 ") {
                    serde_json::json!([
                        {
                            "id": 1,
                            "protocol_run_id": 88,
                            "step_run_id": 331,
                            "event_type": "step_started",
                            "message": "step 331 started",
                            "created_at": "2026-04-01T12:00:00Z"
                        },
                        {
                            "id": 2,
                            "protocol_run_id": 88,
                            "step_run_id": 331,
                            "event_type": "qa_failed",
                            "message": "QA failed on database migration checks",
                            "created_at": "2026-04-01T12:00:05Z"
                        }
                    ])
                    .to_string()
                } else {
                    serde_json::json!({"error": request_line}).to_string()
                };
                let response = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    body.len(),
                    body
                );
                stream
                    .write_all(response.as_bytes())
                    .expect("write response");
            }
        });
        (format!("http://{}", addr), handle)
    }

    #[tokio::test]
    async fn chat_runs_brownfield_flow_and_appends_status_events() {
        let (base_url, server) = spawn_brownfield_chat_server();
        let client = ApiClient::new(base_url, None, None).expect("client");
        let mut app = App::new(client, Duration::from_secs(10));

        app.state.projects = vec![Project {
            id: 11,
            name: "telegram-bot-browser-test-copy".into(),
            base_branch: Some("main".into()),
            ..Default::default()
        }];
        app.state.project_index = Some(0);
        app.state.agents = vec![AgentInfo {
            id: "claude-code".into(),
            name: "Claude Code".into(),
            kind: "cli".into(),
            enabled: Some(true),
            default_model: Some("claude-sonnet-4-20250514".into()),
            ..Default::default()
        }];
        app.state.agent_index = Some(0);

        app.state.composer_input =
            "/flow run brownfield create a new task flow for db integration".into();
        app.submit_chat_input().await.expect("submit brownfield");

        assert!(app
            .state
            .chat_messages
            .iter()
            .any(|msg| msg.text.contains("Starting brownfield flow for project")));
        assert!(app
            .state
            .chat_messages
            .iter()
            .any(|msg| msg.text.contains("brownfield_feature queued")));

        let active_flow = app.state.active_flow.as_ref().expect("active flow");
        assert_eq!(active_flow.kind, "brownfield");
        assert_eq!(active_flow.protocol_id, Some(88));
        assert_eq!(active_flow.step_id, Some(331));

        app.load_recent_events().await.expect("recent events");
        app.sync_chat_events();

        assert!(app
            .state
            .chat_messages
            .iter()
            .any(|msg| msg.kind == Some(ChatMessageKind::Step)
                && msg.text.contains("[step_started] step 331 started")));
        assert!(app
            .state
            .chat_messages
            .iter()
            .any(|msg| msg.kind == Some(ChatMessageKind::Warn)
                && msg
                    .text
                    .contains("[qa_failed] QA failed on database migration checks")));

        server.join().expect("server joined");
    }
}
