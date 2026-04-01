use crate::app::{App, LoginForm, Modal, QuickAction, Screen};
use crate::state::Page;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Tabs, Wrap},
    Frame,
};
use serde_json::Value;
use std::fmt::Write as _;

#[path = "ui/agents.rs"]
mod agents;
#[path = "ui/chat.rs"]
mod chat;
mod event_detail;
#[path = "ui/ops.rs"]
mod ops;
#[path = "ui/overlays.rs"]
mod overlays;
#[path = "ui/policy.rs"]
mod policy;
#[path = "ui/projects.rs"]
mod projects;
#[path = "ui/protocols.rs"]
mod protocols;
#[path = "ui/quality.rs"]
mod quality;
#[path = "ui/runs.rs"]
mod runs;
#[path = "ui/settings.rs"]
mod settings;
#[path = "ui/steps.rs"]
mod steps;

pub fn draw(
    f: &mut Frame<'_>,
    app: &App,
    modal: Option<&Modal>,
    screen: Screen,
    login_form: &LoginForm,
    menu_index: usize,
    welcome_index: usize,
) {
    let size = f.size();
    match screen {
        Screen::Welcome => overlays::draw_welcome(f, size, welcome_index, app),
        Screen::Login => overlays::draw_login(f, size, login_form, app),
        Screen::Menu => overlays::draw_menu(f, size, menu_index, app),
        Screen::SettingsInfo => overlays::draw_settings_info(f, size, app),
        Screen::Help => overlays::draw_help(f, size, app),
        Screen::Version => overlays::draw_version(f, size, app),
        Screen::Dashboard => {
            let chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints(
                    [
                        Constraint::Length(3),
                        Constraint::Length(3),
                        Constraint::Min(0),
                        Constraint::Length(2),
                    ]
                    .as_ref(),
                )
                .split(size);

            draw_tabs(f, chunks[0], app);
            draw_action_bar(f, chunks[1], app.state.page);
            draw_body(f, chunks[2], app);
            draw_status(f, chunks[3], app);
            if let Some(modal) = modal {
                overlays::draw_modal(f, size, modal, app);
            }
        }
    }
}

fn draw_tabs(f: &mut Frame<'_>, area: Rect, app: &App) {
    let titles = [
        "Chat",
        "Dashboard",
        "Projects",
        "Protocols",
        "Steps",
        "Runs",
        "Quality",
        "Policy",
        "Agents",
        "Events",
        "Queues",
        "Settings",
    ]
    .into_iter()
    .map(|t| Line::from(Span::styled(t, Style::default().fg(Color::Cyan))))
    .collect::<Vec<_>>();
    let idx = match app.state.page {
        Page::Chat => 0,
        Page::Dashboard => 1,
        Page::Projects => 2,
        Page::Protocols => 3,
        Page::Steps => 4,
        Page::Runs => 5,
        Page::Quality => 6,
        Page::Policy => 7,
        Page::Agents => 8,
        Page::Events => 9,
        Page::Queues => 10,
        Page::Settings => 11,
    };
    let tabs = Tabs::new(titles)
        .block(Block::default().borders(Borders::ALL).title("Pages"))
        .select(idx)
        .highlight_style(
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        );
    f.render_widget(tabs, area);
}

fn draw_body(f: &mut Frame<'_>, area: Rect, app: &App) {
    match app.state.page {
        Page::Chat => chat::draw_chat(f, area, app),
        Page::Dashboard => ops::draw_dashboard(f, area, app),
        Page::Projects => projects::draw_projects(f, area, app),
        Page::Protocols => protocols::draw_protocols(f, area, app),
        Page::Steps => steps::draw_steps(f, area, app),
        Page::Runs => runs::draw_runs(f, area, app),
        Page::Quality => quality::draw_quality(f, area, app),
        Page::Policy => policy::draw_policy(f, area, app),
        Page::Agents => agents::draw_agents(f, area, app),
        Page::Events => ops::draw_events(f, area, app),
        Page::Queues => ops::draw_queues(f, area, app),
        Page::Settings => settings::draw_settings(f, area, app),
    }
}

fn draw_action_bar(f: &mut Frame<'_>, area: Rect, page: Page) {
    let (primary, secondary) = match page {
        Page::Chat => (
            vec![
                ("Enter", "Send"),
                ("j/k", "Project"),
                ("Ctrl+j/k", "Agent"),
                ("Ctrl+K", "Search"),
                ("Tab", "Pages"),
            ],
            vec![
                ("/flow", "Run flow"),
                ("/agent", "Use agent"),
                ("Esc", "Clear"),
                ("m", "Menu"),
                ("Ctrl+C", "Quit"),
            ],
        ),
        Page::Dashboard => (
            vec![
                ("Enter", "Action palette"),
                ("g", "New project"),
                ("R", "New protocol"),
                ("n", "Run next"),
                ("t", "Retry"),
                ("y", "QA"),
                ("a", "Approve"),
                ("o", "Open PR"),
                ("s", "Start"),
                ("p", "Pause"),
                ("e", "Resume"),
                ("x", "Cancel"),
            ],
            vec![
                ("A", "Spec audit"),
                ("/", "Search"),
                ("f", "Step filter"),
                ("J", "Job filter"),
                ("[ / ]", "Branch"),
                ("r", "Refresh"),
                ("m", "Menu"),
                ("q", "Quit"),
            ],
        ),
        Page::Protocols => (
            vec![
                ("n", "Run next"),
                ("t", "Retry"),
                ("o", "Open PR"),
                ("O/C", "Links"),
                ("/", "Search"),
                ("s", "Start"),
                ("p", "Pause"),
                ("e", "Resume"),
                ("x", "Cancel"),
                ("[ / ]", "Protocol tab"),
            ],
            vec![("r", "Refresh"), ("m", "Menu"), ("q", "Quit")],
        ),
        Page::Steps => (
            vec![
                ("y", "QA"),
                ("a", "Approve"),
                ("f", "Step filter"),
                ("O/C", "Links"),
                ("/", "Search"),
                ("[ / ]", "Step tab"),
            ],
            vec![("r", "Refresh"), ("m", "Menu"), ("q", "Quit")],
        ),
        Page::Projects => (
            vec![
                ("g", "New project"),
                ("R", "New protocol"),
                ("i", "Import CM"),
                ("A", "Spec audit"),
                ("/", "Search"),
                ("O/C", "Links"),
                ("z/u/D", "Lifecycle"),
                ("Y", "Duplicate"),
                ("[ / ]", "Project tab"),
            ],
            vec![
                ("Enter", "Palette"),
                ("b", "Reload workspace"),
                ("d", "Delete branch"),
                ("Ctrl+j/k", "Branch/spec"),
                ("c", "Configure"),
                ("m", "Menu"),
                ("q", "Quit"),
            ],
        ),
        Page::Runs => (
            vec![
                ("b", "Reload run"),
                ("r", "Refresh"),
                ("/", "Search"),
                ("O/C", "Links"),
            ],
            vec![("m", "Menu"), ("q", "Quit")],
        ),
        Page::Quality => (
            vec![("r", "Refresh"), ("/", "Search")],
            vec![("m", "Menu"), ("q", "Quit")],
        ),
        Page::Policy => (
            vec![("r", "Refresh"), ("/", "Search"), ("O/C", "Links")],
            vec![("m", "Menu"), ("q", "Quit")],
        ),
        Page::Agents => (
            vec![
                ("T", "Test agent"),
                ("U", "Assign"),
                ("c", "Configure agent"),
                ("r", "Refresh"),
                ("/", "Search"),
            ],
            vec![("m", "Menu"), ("q", "Quit")],
        ),
        Page::Events => (
            vec![
                ("Enter", "Action palette"),
                ("j/k", "Select event"),
                ("Space", "Pause/live"),
                ("/", "Search"),
            ],
            vec![("r", "Refresh"), ("m", "Menu"), ("q", "Quit")],
        ),
        Page::Queues => (
            vec![
                ("j/k", "Select job"),
                ("J", "Cycle job filter"),
                ("Space", "Pause/live"),
                ("/", "Search"),
            ],
            vec![("r", "Refresh"), ("m", "Menu"), ("q", "Quit")],
        ),
        Page::Settings => (
            vec![
                ("c", "Configure API/token"),
                ("[ / ]", "Settings tab"),
                ("O/C", "Links"),
            ],
            vec![("m", "Menu"), ("q", "Quit")],
        ),
    };

    let primary_line = action_line(primary, true);
    let secondary_line = action_line(secondary, false);
    let para = Paragraph::new(vec![primary_line, secondary_line])
        .alignment(ratatui::layout::Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(format!("Actions — {}", page_label(page))),
        )
        .wrap(Wrap { trim: true });
    f.render_widget(para, area);
}

fn draw_status(f: &mut Frame<'_>, area: Rect, app: &App) {
    let mut line = format!("Status: {}", app.state.status);
    if let Some(err) = &app.state.last_error {
        let _ = write!(line, " • Error: {}", err);
    }
    if let Some(query) = &app.state.global_query {
        let _ = write!(
            line,
            " • Search: {}:{} ({})",
            app.state.search_scope.label(),
            query,
            app.state.search_results.len()
        );
        if let Some(first) = app.state.search_results.first() {
            let _ = write!(line, " • Top: {} {}", first.label, first.detail);
        }
    }
    if let Some(saved) = app.state.saved_filters.last() {
        let _ = write!(
            line,
            " • Saved: {}={} ({})",
            saved.name,
            saved.query,
            saved.scope.label()
        );
    }
    if let Some(action) = &app.state.external_action_result {
        let _ = write!(line, " • Link: {}", action);
    }
    if matches!(app.state.page, Page::Events | Page::Queues) {
        let _ = write!(
            line,
            " • Stream: {}",
            if app.state.stream_paused {
                "paused"
            } else {
                "live"
            }
        );
    }
    let para = Paragraph::new(line)
        .style(Style::default().fg(Color::White))
        .block(Block::default().borders(Borders::ALL).title("Status"))
        .wrap(Wrap { trim: true });
    f.render_widget(para, area);
}

fn page_label(page: Page) -> &'static str {
    match page {
        Page::Chat => "Chat",
        Page::Dashboard => "Dashboard",
        Page::Projects => "Projects",
        Page::Protocols => "Protocols",
        Page::Steps => "Steps",
        Page::Runs => "Runs",
        Page::Quality => "Quality",
        Page::Policy => "Policy",
        Page::Agents => "Agents",
        Page::Events => "Events",
        Page::Queues => "Queues",
        Page::Settings => "Settings",
    }
}

pub(super) fn tabs_line(items: Vec<(&'static str, bool)>) -> Line<'static> {
    let mut spans = Vec::new();
    for (idx, (label, active)) in items.into_iter().enumerate() {
        if idx > 0 {
            spans.push(Span::raw(" "));
        }
        let style = if active {
            Style::default()
                .fg(Color::Black)
                .bg(Color::Yellow)
                .add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::Cyan)
        };
        spans.push(Span::styled(format!("[{}]", label), style));
    }
    Line::from(spans)
}

pub(super) fn render_paragraph_block(
    f: &mut Frame<'_>,
    area: Rect,
    title: &str,
    lines: Vec<Line<'static>>,
) {
    let para = Paragraph::new(lines)
        .block(Block::default().borders(Borders::ALL).title(title))
        .wrap(Wrap { trim: true });
    f.render_widget(para, area);
}

pub(super) fn render_list_block(f: &mut Frame<'_>, area: Rect, title: &str, items: Vec<String>) {
    let items: Vec<ListItem> = if items.is_empty() {
        vec![ListItem::new("No data.")]
    } else {
        items.into_iter().map(ListItem::new).collect()
    };
    let list = List::new(items).block(Block::default().borders(Borders::ALL).title(title));
    f.render_widget(list, area);
}

pub(super) fn action_line(items: Vec<(&str, &str)>, emphasize: bool) -> Line<'static> {
    let mut spans: Vec<Span> = Vec::new();
    for (idx, (key, label)) in items.into_iter().enumerate() {
        if idx > 0 {
            spans.push(Span::raw("  "));
        }
        spans.push(Span::styled(
            format!(" {key} "),
            Style::default()
                .bg(if emphasize { Color::Green } else { Color::Blue })
                .fg(Color::Black)
                .add_modifier(Modifier::BOLD),
        ));
        spans.push(Span::styled(
            format!(" {label}"),
            Style::default().fg(Color::Gray),
        ));
    }
    Line::from(spans)
}

pub(super) fn heading_line(text: &str) -> Line<'static> {
    Line::from(Span::styled(
        text.to_string(),
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD),
    ))
}

pub(super) fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints(
            [
                Constraint::Percentage((100 - percent_y) / 2),
                Constraint::Percentage(percent_y),
                Constraint::Percentage((100 - percent_y) / 2),
            ]
            .as_ref(),
        )
        .split(r);
    let vertical = popup_layout[1];
    let horizontal = Layout::default()
        .direction(Direction::Horizontal)
        .constraints(
            [
                Constraint::Percentage((100 - percent_x) / 2),
                Constraint::Percentage(percent_x),
                Constraint::Percentage((100 - percent_x) / 2),
            ]
            .as_ref(),
        )
        .split(vertical);
    horizontal[1]
}

pub(super) fn shrink(area: Rect, padding: u16) -> Rect {
    Rect {
        x: area.x.saturating_add(padding),
        y: area.y.saturating_add(padding),
        width: area
            .width
            .saturating_sub(padding.saturating_mul(2).min(area.width)),
        height: area
            .height
            .saturating_sub(padding.saturating_mul(2).min(area.height)),
    }
}

pub(super) fn make_state(selected: usize) -> ListState {
    let mut state = ListState::default();
    state.select(Some(selected));
    state
}

pub(super) fn format_value(value: &Value) -> String {
    match value {
        Value::Null => "-".to_string(),
        _ => serde_json::to_string_pretty(value).unwrap_or_else(|_| "-".to_string()),
    }
}

pub(super) fn pretty_json_lines(value: &Value) -> Vec<Line<'static>> {
    serde_json::to_string_pretty(value)
        .map(|body| trunc_lines(&body, 18))
        .unwrap_or_else(|_| vec![Line::from("-")])
}

pub(super) fn trunc_lines(text: &str, max_lines: usize) -> Vec<Line<'static>> {
    let mut lines: Vec<Line<'static>> = text
        .lines()
        .take(max_lines)
        .map(|line| Line::from(line.to_string()))
        .collect();
    if lines.is_empty() {
        lines.push(Line::from("-"));
    }
    lines
}

pub(super) fn review_links_lines(app: &App, limit: usize) -> Vec<Line<'static>> {
    let links = app.review_links();
    if links.is_empty() {
        return vec![Line::from("links: none available")];
    }
    let mut lines = vec![Line::from("links: O open • C copy")];
    lines.extend(
        links
            .into_iter()
            .take(limit)
            .map(|(label, value)| Line::from(format!("{label}: {value}"))),
    );
    lines
}

pub(super) fn short_hash(value: &str) -> String {
    value.chars().take(8).collect()
}

pub(super) fn yes_no(value: bool) -> &'static str {
    if value {
        "yes"
    } else {
        "no"
    }
}

pub(super) fn format_quick_action(action: QuickAction) -> String {
    match action {
        QuickAction::TestAgent => "Test agent (T)",
        QuickAction::CreateProject => "Create project (g)",
        QuickAction::CreateProtocol => "Create protocol (R)",
        QuickAction::RunNext => "Run next (n)",
        QuickAction::RetryLatest => "Retry latest (t)",
        QuickAction::RunQa => "Run QA (y)",
        QuickAction::Approve => "Approve (a)",
        QuickAction::OpenPr => "Open PR (o)",
        QuickAction::StartProtocol => "Start protocol (s)",
        QuickAction::PauseProtocol => "Pause protocol (p)",
        QuickAction::ResumeProtocol => "Resume protocol (e)",
        QuickAction::CancelProtocol => "Cancel protocol (x)",
        QuickAction::ImportCodeMachine => "Import CodeMachine (i)",
        QuickAction::SpecAudit => "Spec audit (A)",
        QuickAction::Search => "Search (/)",
        QuickAction::SpecInit => "Spec init",
        QuickAction::SpecGenerate => "Spec generate",
        QuickAction::SpecPlan => "Spec plan",
        QuickAction::SpecTasks => "Spec tasks",
        QuickAction::SpecClarify => "Spec clarify",
        QuickAction::SpecChecklist => "Spec checklist",
        QuickAction::SpecAnalyze => "Spec analyze",
        QuickAction::SpecImplement => "Spec implement",
        QuickAction::SpecCleanup => "Spec cleanup",
        QuickAction::OpenLink => "Open best link (O)",
        QuickAction::CopyLink => "Copy best link (C)",
        QuickAction::DuplicateProject => "Duplicate project (Y)",
        QuickAction::AssignAgent => "Assign agent (U)",
        QuickAction::Configure => "Configure (c)",
        QuickAction::Menu => "Main menu (m)",
    }
    .to_string()
}
