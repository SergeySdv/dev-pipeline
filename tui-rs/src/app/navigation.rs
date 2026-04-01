use super::{App, Screen};
use crate::{
    api::ApiClient,
    state::{Page, ProjectWorkspaceTab},
};
use anyhow::Result;
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

impl App {
    pub(crate) fn schedule_refresh(&mut self, status: impl Into<String>) {
        self.invalidate_background_requests();
        self.pending_refresh = true;
        self.state.refreshing = true;
        self.state.last_error = None;
        self.state.status = status.into();
    }

    pub(crate) fn schedule_selection_refresh(&mut self, status: impl Into<String>) {
        self.invalidate_background_requests();
        self.pending_selection_refresh = true;
        self.state.refreshing = true;
        self.state.last_error = None;
        self.state.status = status.into();
    }

    pub(crate) fn open_dashboard(&mut self, page: Option<Page>, status: impl Into<String>) {
        self.screen = Screen::Dashboard;
        if let Some(page) = page {
            self.state.page = page;
        }
        self.schedule_refresh(status);
    }

    pub(crate) fn switch_page(&mut self, page: Page) {
        self.state.page = page;
        self.schedule_refresh(format!("Loading {}...", self.page_label(page)));
    }

    pub(crate) fn page_label(&self, page: Page) -> &'static str {
        match page {
            Page::Chat => "chat",
            Page::Dashboard => "dashboard",
            Page::Projects => "projects",
            Page::Protocols => "protocols",
            Page::Steps => "steps",
            Page::Runs => "runs",
            Page::Quality => "quality",
            Page::Policy => "policy",
            Page::Agents => "agents",
            Page::Events => "events",
            Page::Queues => "queues",
            Page::Settings => "settings",
        }
    }

    pub(crate) async fn handle_key(&mut self, key: KeyEvent) -> Result<bool> {
        if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
            return Ok(true);
        }
        if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('k') {
            self.open_search_modal();
            return Ok(false);
        }
        if self.handle_chat_key(&key).await? {
            return Ok(false);
        }
        if self.handle_workspace_key(&key).await? {
            return Ok(false);
        }
        match key.code {
            KeyCode::Char('q') => return Ok(true),
            KeyCode::Char(' ') if matches!(self.state.page, Page::Events | Page::Queues) => {
                self.state.stream_paused = !self.state.stream_paused;
                self.state.status = if self.state.stream_paused {
                    "Stream refresh paused".into()
                } else {
                    "Stream refresh resumed".into()
                };
            }
            KeyCode::Char('r') if !key.modifiers.contains(KeyModifiers::SHIFT) => {
                self.schedule_refresh("Refreshing...");
            }
            KeyCode::Char('m') => {
                self.screen = Screen::Menu;
                self.menu_index = 0;
            }
            KeyCode::Char('h') | KeyCode::Char('?') => {
                self.state.status = "Keys: enter send/palette • tab/shift+tab/←/→ pages • arrows/j/k move • ctrl+j/k chat agent • ctrl+k search • O open link • C copy link • r refresh • space pause streams • ctrl+c quit • n run next • t retry • y QA • a approve • o open PR • s start • p pause • e resume • x cancel • g new project • R new protocol • i import CM • A spec audit • c config • b reload page workspace • d delete branch • J cycle queue filter • Y duplicate project • U assign agent • [/] workspace tabs".into();
            }
            KeyCode::Char('g') => self.open_project_modal(),
            KeyCode::Char('R') => self.open_protocol_modal(),
            KeyCode::Char('c') => {
                if self.state.page == Page::Agents {
                    self.open_agent_config_modal();
                } else {
                    self.open_token_modal();
                }
            }
            KeyCode::Char('i') => self.open_cm_modal(),
            KeyCode::Char('A') => self.open_spec_audit_modal(),
            KeyCode::Char('/') => self.open_search_modal(),
            KeyCode::Char('O') => self.open_best_link()?,
            KeyCode::Char('C') => self.copy_best_link()?,
            KeyCode::Char('Y') if self.state.page == Page::Projects => {
                self.open_duplicate_project_modal();
            }
            KeyCode::Char('U') if self.state.page == Page::Agents => {
                self.open_agent_assignment_modal();
            }
            KeyCode::Char('w') => {
                self.screen = Screen::Welcome;
                self.welcome_index = 0;
            }
            KeyCode::Enter => self.open_action_palette(),
            KeyCode::Char('b') => match self.state.page {
                Page::Projects => self.load_project_workspace().await?,
                Page::Protocols => self.load_protocol_workspace().await?,
                Page::Steps => self.load_step_workspace().await?,
                Page::Runs => self.load_run_workspace().await?,
                _ => self.load_branches().await?,
            },
            KeyCode::Char('d') => self.open_delete_branch_modal(),
            KeyCode::Char('z') if self.state.page == Page::Projects => {
                self.open_archive_project_modal();
            }
            KeyCode::Char('u') if self.state.page == Page::Projects => {
                self.open_unarchive_project_modal();
            }
            KeyCode::Char('D') if self.state.page == Page::Projects => {
                self.open_delete_project_modal();
            }
            KeyCode::Char('T') if self.state.page == Page::Agents => {
                self.run_agent_test().await?;
            }
            KeyCode::Char('J') => {
                self.cycle_job_filter().await?;
            }
            KeyCode::Tab | KeyCode::Right => {
                self.switch_page(self.state.page.next());
            }
            KeyCode::BackTab | KeyCode::Left => {
                self.switch_page(self.state.page.prev());
            }
            KeyCode::Char('1') => self.switch_page(Page::Chat),
            KeyCode::Char('2') => self.switch_page(Page::Dashboard),
            KeyCode::Char('3') => self.switch_page(Page::Projects),
            KeyCode::Char('4') => self.switch_page(Page::Protocols),
            KeyCode::Char('5') => self.switch_page(Page::Steps),
            KeyCode::Char('6') => self.switch_page(Page::Runs),
            KeyCode::Char('7') => self.switch_page(Page::Quality),
            KeyCode::Char('8') => self.switch_page(Page::Policy),
            KeyCode::Char('9') => self.switch_page(Page::Agents),
            KeyCode::Char('0') => self.switch_page(Page::Events),
            KeyCode::Char('-') => self.switch_page(Page::Queues),
            KeyCode::Char('=') => self.switch_page(Page::Settings),
            KeyCode::Down | KeyCode::Char('j') => {
                if self.handle_down() {
                    self.schedule_selection_refresh("Updating selection...");
                }
            }
            KeyCode::Up | KeyCode::Char('k') => {
                if self.handle_up() {
                    self.schedule_selection_refresh("Updating selection...");
                }
            }
            KeyCode::Char('f') => {
                self.cycle_step_filter().await?;
            }
            KeyCode::Char('n') => self.run_next().await?,
            KeyCode::Char('t') => self.retry_latest().await?,
            KeyCode::Char('y') => self.run_qa_latest().await?,
            KeyCode::Char('a') => self.approve_latest().await?,
            KeyCode::Char('o') => self.open_pr().await?,
            KeyCode::Char('s') => self.protocol_action("start", "Planning enqueued.").await?,
            KeyCode::Char('p') => self.protocol_action("pause", "Protocol paused.").await?,
            KeyCode::Char('e') => self.protocol_action("resume", "Protocol resumed.").await?,
            KeyCode::Char('x') => {
                self.protocol_action("cancel", "Protocol cancelled.")
                    .await?
            }
            _ => {}
        }
        Ok(false)
    }

    pub(crate) async fn handle_workspace_key(&mut self, key: &KeyEvent) -> Result<bool> {
        match key.code {
            KeyCode::Char('[') => {
                match self.state.page {
                    Page::Projects => {
                        self.state.project_workspace_tab = self.state.project_workspace_tab.prev();
                        self.state.status =
                            format!("Project tab: {}", self.state.project_workspace_tab.label());
                    }
                    Page::Protocols => {
                        self.state.protocol_workspace_tab =
                            self.state.protocol_workspace_tab.prev();
                        self.state.status = format!(
                            "Protocol tab: {}",
                            self.state.protocol_workspace_tab.label()
                        );
                    }
                    Page::Steps => {
                        self.state.step_workspace_tab = self.state.step_workspace_tab.prev();
                        self.state.status =
                            format!("Step tab: {}", self.state.step_workspace_tab.label());
                    }
                    Page::Settings => {
                        self.state.settings_tab = self.state.settings_tab.prev();
                        self.state.status =
                            format!("Settings tab: {}", self.state.settings_tab.label());
                    }
                    _ => {
                        self.state.select_branch(-1);
                    }
                }
                return Ok(true);
            }
            KeyCode::Char(']') => {
                match self.state.page {
                    Page::Projects => {
                        self.state.project_workspace_tab = self.state.project_workspace_tab.next();
                        self.state.status =
                            format!("Project tab: {}", self.state.project_workspace_tab.label());
                    }
                    Page::Protocols => {
                        self.state.protocol_workspace_tab =
                            self.state.protocol_workspace_tab.next();
                        self.state.status = format!(
                            "Protocol tab: {}",
                            self.state.protocol_workspace_tab.label()
                        );
                    }
                    Page::Steps => {
                        self.state.step_workspace_tab = self.state.step_workspace_tab.next();
                        self.state.status =
                            format!("Step tab: {}", self.state.step_workspace_tab.label());
                    }
                    Page::Settings => {
                        self.state.settings_tab = self.state.settings_tab.next();
                        self.state.status =
                            format!("Settings tab: {}", self.state.settings_tab.label());
                    }
                    _ => {
                        self.state.select_branch(1);
                    }
                }
                return Ok(true);
            }
            _ => {}
        }

        if !key.modifiers.contains(KeyModifiers::CONTROL) {
            return Ok(false);
        }

        if self.state.page == Page::Projects
            && self.state.project_workspace_tab == ProjectWorkspaceTab::Branches
        {
            match key.code {
                KeyCode::Char('j') | KeyCode::Down => {
                    self.state.select_branch(1);
                    return Ok(true);
                }
                KeyCode::Char('k') | KeyCode::Up => {
                    self.state.select_branch(-1);
                    return Ok(true);
                }
                _ => {}
            }
        }
        if self.state.page == Page::Projects
            && self.state.project_workspace_tab == ProjectWorkspaceTab::Specs
        {
            match key.code {
                KeyCode::Char('j') | KeyCode::Down => {
                    self.state.select_project_spec(1);
                    self.schedule_selection_refresh("Loading spec content...");
                    return Ok(true);
                }
                KeyCode::Char('k') | KeyCode::Up => {
                    self.state.select_project_spec(-1);
                    self.schedule_selection_refresh("Loading spec content...");
                    return Ok(true);
                }
                _ => {}
            }
        }
        Ok(false)
    }

    pub(crate) async fn handle_welcome_key(&mut self, key: KeyEvent) -> Result<bool> {
        let items = ["Start DevGodzilla", "Settings", "Help", "Version", "Quit"];
        match key.code {
            KeyCode::Up | KeyCode::Char('k') => {
                if self.welcome_index == 0 {
                    self.welcome_index = items.len().saturating_sub(1);
                } else {
                    self.welcome_index -= 1;
                }
            }
            KeyCode::Down | KeyCode::Char('j') | KeyCode::Tab => {
                self.welcome_index = (self.welcome_index + 1) % items.len();
            }
            KeyCode::BackTab => {
                if self.welcome_index == 0 {
                    self.welcome_index = items.len().saturating_sub(1);
                } else {
                    self.welcome_index -= 1;
                }
            }
            KeyCode::Char('1') => self.welcome_index = 0,
            KeyCode::Char('2') => self.welcome_index = 1,
            KeyCode::Char('3') => self.welcome_index = 2,
            KeyCode::Char('4') => self.welcome_index = 3,
            KeyCode::Char('5') => self.welcome_index = 4,
            KeyCode::Enter => match self.welcome_index {
                0 => {
                    if self.auto_login {
                        self.open_dashboard(None, "Connecting to API...");
                    } else {
                        self.screen = Screen::Login;
                    }
                }
                1 => {
                    self.screen = Screen::SettingsInfo;
                }
                2 => {
                    self.screen = Screen::Help;
                }
                3 => {
                    self.screen = Screen::Version;
                }
                4 => return Ok(true),
                _ => {}
            },
            KeyCode::Esc | KeyCode::Char('q') => return Ok(true),
            _ => {}
        }
        Ok(false)
    }

    pub(crate) async fn handle_login_key(&mut self, key: KeyEvent) -> Result<bool> {
        match key.code {
            KeyCode::Tab => {
                self.login_form.focus = (self.login_form.focus + 1) % self.login_form.fields.len();
            }
            KeyCode::BackTab => {
                if self.login_form.focus == 0 {
                    self.login_form.focus = self.login_form.fields.len() - 1;
                } else {
                    self.login_form.focus -= 1;
                }
            }
            KeyCode::Enter => {
                let base = self.login_form.fields[0].value.trim();
                if base.is_empty() {
                    self.state.status = "API base required".into();
                    return Ok(false);
                }
                let token = self.login_form.fields[1].value.trim();
                let project_token = self.login_form.fields[2].value.trim();
                self.client = ApiClient::new(
                    base.to_string(),
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
                self.state.status = format!("Connected to {base}");
                self.screen = Screen::Menu;
                self.menu_index = 0;
            }
            KeyCode::Esc => return Ok(true),
            KeyCode::Backspace => {
                if let Some(field) = self.login_form.fields.get_mut(self.login_form.focus) {
                    field.value.pop();
                }
            }
            KeyCode::Char(c) => {
                if let Some(field) = self.login_form.fields.get_mut(self.login_form.focus) {
                    field.value.push(c);
                }
            }
            _ => {}
        }
        Ok(false)
    }

    pub(crate) async fn handle_menu_key(&mut self, key: KeyEvent) -> Result<bool> {
        let items = ["Dashboard", "Configure API/token", "Quit"];
        match key.code {
            KeyCode::Up => {
                if self.menu_index == 0 {
                    self.menu_index = items.len() - 1;
                } else {
                    self.menu_index -= 1;
                }
            }
            KeyCode::Down | KeyCode::Tab | KeyCode::Char('j') => {
                self.menu_index = (self.menu_index + 1) % items.len();
            }
            KeyCode::BackTab | KeyCode::Char('k') => {
                if self.menu_index == 0 {
                    self.menu_index = items.len() - 1;
                } else {
                    self.menu_index -= 1;
                }
            }
            KeyCode::Char('1') => {
                self.menu_index = 0;
                self.open_dashboard(None, "Loading dashboard...");
            }
            KeyCode::Char('2') => {
                self.menu_index = 1;
                self.open_token_modal();
            }
            KeyCode::Char('3') => return Ok(true),
            KeyCode::Enter => match self.menu_index {
                0 => {
                    self.open_dashboard(None, "Loading dashboard...");
                }
                1 => {
                    self.open_token_modal();
                }
                2 => return Ok(true),
                _ => {}
            },
            KeyCode::Char('q') => return Ok(true),
            KeyCode::Esc => {
                self.screen = Screen::Login;
            }
            _ => {}
        }
        Ok(false)
    }

    pub(crate) async fn handle_info_key(&mut self, key: KeyEvent) -> Result<bool> {
        match self.screen {
            Screen::SettingsInfo => match key.code {
                KeyCode::Char('c') => {
                    self.open_token_modal();
                }
                KeyCode::Enter => {
                    self.open_dashboard(Some(Page::Settings), "Loading settings...");
                }
                KeyCode::Esc | KeyCode::Char('q') | KeyCode::Char('w') => {
                    self.screen = Screen::Welcome;
                }
                KeyCode::Char('m') => {
                    self.screen = Screen::Menu;
                    self.menu_index = 0;
                }
                _ => {}
            },
            Screen::Help => match key.code {
                KeyCode::Enter => {
                    self.open_dashboard(None, "Loading dashboard...");
                }
                KeyCode::Esc | KeyCode::Char('q') | KeyCode::Char('w') => {
                    self.screen = Screen::Welcome;
                }
                KeyCode::Char('m') => {
                    self.screen = Screen::Menu;
                    self.menu_index = 0;
                }
                _ => {}
            },
            Screen::Version => match key.code {
                KeyCode::Esc | KeyCode::Char('q') | KeyCode::Char('w') => {
                    self.screen = Screen::Welcome;
                }
                KeyCode::Char('m') => {
                    self.screen = Screen::Menu;
                    self.menu_index = 0;
                }
                _ => {}
            },
            _ => {}
        }
        Ok(false)
    }

    pub(crate) fn handle_down(&mut self) -> bool {
        let before = (
            self.state.project_index,
            self.state.project_spec_index,
            self.state.protocol_index,
            self.state.step_index,
            self.state.run_index,
            self.state.policy_pack_index,
            self.state.agent_index,
            self.state.event_index,
            self.state.queue_job_index,
            self.state.branch_index,
        );
        match self.state.page {
            Page::Dashboard | Page::Projects => self.state.select_project(1),
            Page::Protocols => self.state.select_protocol(1),
            Page::Steps => self.state.select_step(1),
            Page::Runs => self.state.select_run(1),
            Page::Policy => self.state.select_policy_pack(1),
            Page::Agents => self.state.select_agent(1),
            Page::Events => self.state.select_event(1),
            Page::Queues => {
                self.state.select_queue_job(1);
            }
            _ => {}
        }
        before
            != (
                self.state.project_index,
                self.state.project_spec_index,
                self.state.protocol_index,
                self.state.step_index,
                self.state.run_index,
                self.state.policy_pack_index,
                self.state.agent_index,
                self.state.event_index,
                self.state.queue_job_index,
                self.state.branch_index,
            )
    }

    pub(crate) fn handle_up(&mut self) -> bool {
        let before = (
            self.state.project_index,
            self.state.project_spec_index,
            self.state.protocol_index,
            self.state.step_index,
            self.state.run_index,
            self.state.policy_pack_index,
            self.state.agent_index,
            self.state.event_index,
            self.state.queue_job_index,
            self.state.branch_index,
        );
        match self.state.page {
            Page::Dashboard | Page::Projects => self.state.select_project(-1),
            Page::Protocols => self.state.select_protocol(-1),
            Page::Steps => self.state.select_step(-1),
            Page::Runs => self.state.select_run(-1),
            Page::Policy => self.state.select_policy_pack(-1),
            Page::Agents => self.state.select_agent(-1),
            Page::Events => self.state.select_event(-1),
            Page::Queues => {
                self.state.select_queue_job(-1);
            }
            _ => {}
        }
        before
            != (
                self.state.project_index,
                self.state.project_spec_index,
                self.state.protocol_index,
                self.state.step_index,
                self.state.run_index,
                self.state.policy_pack_index,
                self.state.agent_index,
                self.state.event_index,
                self.state.queue_job_index,
                self.state.branch_index,
            )
    }
}
