use crate::{
    api::ApiClient,
    state::{AppState, Page},
    ui,
};
use anyhow::Result;
use crossterm::{
    event::{Event, EventStream},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use futures::StreamExt;
use ratatui::{backend::CrosstermBackend, Terminal};
use std::time::{Duration, Instant};
use std::{env, io};
use tokio::{sync::mpsc, task::JoinHandle};

mod actions;
mod background;
mod chat;
mod loaders;
mod modals;
mod navigation;
mod search;

pub struct App {
    pub state: AppState,
    pub client: ApiClient,
    pub refresh_interval: Duration,
    pending_refresh: bool,
    pending_selection_refresh: bool,
    background_handle: Option<JoinHandle<()>>,
    background_request_id: u64,
    background_tx: mpsc::UnboundedSender<background::BackgroundResult>,
    background_rx: mpsc::UnboundedReceiver<background::BackgroundResult>,
    modal: Option<Modal>,
    screen: Screen,
    pub auto_login: bool,
    login_form: LoginForm,
    menu_index: usize,
    welcome_index: usize,
    last_interaction_at: Instant,
}

#[derive(Debug, Clone)]
pub(crate) struct InputField {
    pub label: String,
    pub value: String,
    pub is_secret: bool,
}

#[derive(Debug, Clone)]
pub(crate) enum Modal {
    Form {
        title: String,
        fields: Vec<InputField>,
        focus: usize,
        action: ModalAction,
    },
    Confirm {
        title: String,
        message: String,
        action: ModalAction,
    },
    Palette {
        items: Vec<QuickAction>,
        index: usize,
    },
}

#[derive(Debug, Clone, Copy)]
pub(crate) enum ModalAction {
    CreateProject,
    CreateProtocol,
    SpecAudit,
    Search,
    SpecInit,
    SpecGenerate,
    SpecPlan,
    SpecTasks,
    SpecClarify,
    SpecChecklist,
    SpecAnalyze,
    SpecImplement,
    SpecCleanup,
    AgentAssign,
    AgentConfig,
    ImportCodeMachine,
    TokenConfig,
    DeleteBranch,
    ArchiveProject,
    UnarchiveProject,
    DeleteProject,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Screen {
    Welcome,
    Login,
    Menu,
    SettingsInfo,
    Help,
    Version,
    Dashboard,
}

#[derive(Debug, Clone)]
pub(crate) struct LoginForm {
    pub fields: Vec<InputField>,
    pub focus: usize,
}

#[derive(Debug, Clone, Copy)]
pub(crate) enum QuickAction {
    TestAgent,
    CreateProject,
    CreateProtocol,
    RunNext,
    RetryLatest,
    RunQa,
    Approve,
    OpenPr,
    StartProtocol,
    PauseProtocol,
    ResumeProtocol,
    CancelProtocol,
    ImportCodeMachine,
    SpecAudit,
    Search,
    SpecInit,
    SpecGenerate,
    SpecPlan,
    SpecTasks,
    SpecClarify,
    SpecChecklist,
    SpecAnalyze,
    SpecImplement,
    SpecCleanup,
    OpenLink,
    CopyLink,
    DuplicateProject,
    AssignAgent,
    Configure,
    Menu,
}

impl App {
    pub fn new(client: ApiClient, refresh_interval: Duration) -> Self {
        let auto_login = env::var("DEVGODZILLA_TUI_AUTOLOGIN")
            .ok()
            .map(|v| v != "0" && v.to_lowercase() != "false")
            .unwrap_or(true);
        let login_form = LoginForm {
            fields: vec![
                InputField {
                    label: "API base".into(),
                    value: client.base_url().to_string(),
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
        };
        let (background_tx, background_rx) = mpsc::unbounded_channel();
        Self {
            state: AppState {
                status: "Ready".to_string(),
                saved_filters: search::load_saved_filters(),
                ..Default::default()
            },
            client,
            refresh_interval,
            pending_refresh: false,
            pending_selection_refresh: false,
            background_handle: None,
            background_request_id: 0,
            background_tx,
            background_rx,
            modal: None,
            screen: Screen::Welcome,
            auto_login,
            login_form,
            menu_index: 0,
            welcome_index: 0,
            last_interaction_at: Instant::now(),
        }
    }

    fn page_refresh_debounce(&self) -> Duration {
        match self.state.page {
            Page::Chat
            | Page::Projects
            | Page::Protocols
            | Page::Steps
            | Page::Runs
            | Page::Quality
            | Page::Policy
            | Page::Agents
            | Page::Events
            | Page::Queues
            | Page::Settings => Duration::from_millis(100),
            _ => Duration::ZERO,
        }
    }

    fn selection_refresh_debounce(&self) -> Duration {
        match self.state.page {
            Page::Projects
            | Page::Protocols
            | Page::Steps
            | Page::Runs
            | Page::Policy
            | Page::Agents => Duration::from_millis(150),
            _ => Duration::ZERO,
        }
    }

    fn pending_debounce_delay(&self) -> Option<Duration> {
        if self.pending_refresh {
            let debounce = self.page_refresh_debounce();
            let elapsed = self.last_interaction_at.elapsed();
            if elapsed < debounce {
                return Some(debounce - elapsed);
            }
        }
        if self.pending_selection_refresh {
            let debounce = self.selection_refresh_debounce();
            let elapsed = self.last_interaction_at.elapsed();
            if elapsed < debounce {
                return Some(debounce - elapsed);
            }
        }
        None
    }

    pub async fn run(&mut self) -> Result<()> {
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        execute!(stdout, EnterAlternateScreen)?;
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;
        terminal.clear()?;

        let mut reader = EventStream::new();
        let mut ticker = tokio::time::interval(self.refresh_interval);
        if self.screen == Screen::Dashboard {
            let _ = self.refresh_all().await;
        }

        loop {
            self.apply_background_updates();
            terminal.draw(|f| {
                ui::draw(
                    f,
                    self,
                    self.modal.as_ref(),
                    self.screen,
                    &self.login_form,
                    self.menu_index,
                    self.welcome_index,
                )
            })?;
            if self.pending_refresh && self.pending_debounce_delay().is_none() {
                self.pending_refresh = false;
                if !self.dispatch_background_refresh().await? {
                    self.refresh_all().await?;
                }
                continue;
            }
            if self.pending_selection_refresh && self.pending_debounce_delay().is_none() {
                self.pending_selection_refresh = false;
                if !self.dispatch_background_selection_refresh().await? {
                    self.refresh_selection().await?;
                }
                continue;
            }
            let pending_delay = self.pending_debounce_delay();
            tokio::select! {
                maybe_event = reader.next() => {
                    if let Some(Ok(evt)) = maybe_event {
                        if self.handle_event(evt).await? {
                            break;
                        }
                    }
                }
                _ = ticker.tick() => {
                    self.refresh_scoped().await?;
                }
                _ = tokio::time::sleep(pending_delay.unwrap_or(Duration::ZERO)), if pending_delay.is_some() => {
                }
            }
        }

        disable_raw_mode()?;
        execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
        terminal.show_cursor()?;
        Ok(())
    }

    async fn handle_event(&mut self, evt: Event) -> Result<bool> {
        match evt {
            Event::Key(key) => {
                self.last_interaction_at = Instant::now();
                if self.handle_modal_key(&key).await? {
                    return Ok(false);
                }
                if self.screen == Screen::Welcome {
                    return self.handle_welcome_key(key).await;
                }
                if matches!(
                    self.screen,
                    Screen::SettingsInfo | Screen::Help | Screen::Version
                ) {
                    return self.handle_info_key(key).await;
                }
                if self.screen == Screen::Login {
                    return self.handle_login_key(key).await;
                }
                if self.screen == Screen::Menu {
                    return self.handle_menu_key(key).await;
                }
                if self.handle_key(key).await? {
                    return Ok(true);
                }
            }
            _ => {}
        }
        Ok(false)
    }
}
