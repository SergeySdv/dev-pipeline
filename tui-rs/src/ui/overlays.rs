use crate::app::{App, LoginForm, Modal};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::Line,
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph, Wrap},
    Frame,
};

use super::{centered_rect, format_quick_action, heading_line, shrink};

pub(super) fn draw_login(f: &mut Frame<'_>, area: Rect, login: &LoginForm, app: &App) {
    let panel = centered_rect(70, 70, area);
    let block = Block::default()
        .borders(Borders::ALL)
        .title("Connect to DevGodzilla");
    f.render_widget(Clear, panel);
    f.render_widget(block.clone(), panel);
    let inner = shrink(panel, 1);
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints(
            [
                Constraint::Length(6),
                Constraint::Length(3),
                Constraint::Length(6),
                Constraint::Length(3),
                Constraint::Min(0),
            ]
            .as_ref(),
        )
        .split(inner);
    let banner = Paragraph::new(vec![
        Line::from("████████╗ █████╗ ███████╗██╗  ██╗███████╗ ██████╗ "),
        Line::from("╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔═══██╗"),
        Line::from("   ██║   ███████║███████╗█████╔╝ ███████╗██║   ██║"),
        Line::from("   ██║   ██╔══██║╚════██║██╔═██╗ ╚════██║██║   ██║"),
        Line::from("   ██║   ██║  ██║███████║██║  ██╗███████║╚██████╔╝"),
        Line::from("   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ "),
    ])
    .style(Style::default().fg(Color::Cyan))
    .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(banner, layout[0]);

    let title = Paragraph::new("DevGodzilla TUI — Login")
        .style(
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )
        .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(title, layout[1]);

    let mut lines: Vec<Line> = Vec::new();
    for (idx, field) in login.fields.iter().enumerate() {
        let mut label = format!("{}: ", field.label);
        if idx == login.focus {
            label.insert_str(0, "> ");
        } else {
            label.insert_str(0, "  ");
        }
        let value = if field.is_secret {
            "******".to_string()
        } else {
            field.value.clone()
        };
        lines.push(Line::from(format!("{label}{value}")));
    }
    let form = Paragraph::new(lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("API connection"),
        )
        .wrap(Wrap { trim: true });
    f.render_widget(form, layout[2]);

    let help = Paragraph::new("Tab/Shift-Tab move • Enter connect • Esc quit (tokens optional)")
        .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(help, layout[3]);

    let status = Paragraph::new(format!("Status: {}", app.state.status))
        .block(Block::default().borders(Borders::ALL).title("Status"));
    f.render_widget(status, layout[4]);
}

pub(super) fn draw_welcome(f: &mut Frame<'_>, area: Rect, welcome_index: usize, app: &App) {
    let panel = centered_rect(80, 70, area);
    let block = Block::default()
        .borders(Borders::ALL)
        .title("Welcome to DevGodzilla");
    f.render_widget(Clear, panel);
    f.render_widget(block.clone(), panel);
    let inner = shrink(panel, 1);
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints(
            [
                Constraint::Length(7),
                Constraint::Length(4),
                Constraint::Length(9),
                Constraint::Length(3),
                Constraint::Length(3),
            ]
            .as_ref(),
        )
        .split(inner);

    let banner = Paragraph::new(vec![
        Line::from("████████╗ █████╗ ███████╗██╗  ██╗███████╗ ██████╗ "),
        Line::from("╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔═══██╗"),
        Line::from("   ██║   ███████║███████╗█████╔╝ ███████╗██║   ██║"),
        Line::from("   ██║   ██╔══██║╚════██║██╔═██╗ ╚════██║██║   ██║"),
        Line::from("   ██║   ██║  ██║███████║██║  ██╗███████║╚██████╔╝"),
        Line::from("   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ "),
    ])
    .style(Style::default().fg(Color::Cyan))
    .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(banner, layout[0]);

    let subtitle = Paragraph::new(format!(
        "Fast terminal UI for orchestrator — v{}",
        env!("CARGO_PKG_VERSION")
    ))
    .style(Style::default().fg(Color::Yellow))
    .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(subtitle, layout[1]);

    let items = ["Start DevGodzilla", "Settings", "Help", "Version", "Quit"];
    let list_items: Vec<ListItem> = items
        .iter()
        .enumerate()
        .map(|(idx, item)| {
            let prefix = if idx == welcome_index { "➤ " } else { "  " };
            ListItem::new(format!("{prefix}{item}"))
        })
        .collect();
    let list = List::new(list_items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Choose an option"),
        )
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    f.render_widget(list, layout[2]);

    let help = Paragraph::new("Up/Down/Tab select • Enter confirm • 1/2/3/4 shortcuts • q quit")
        .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(help, layout[3]);

    let status = Paragraph::new(format!("Status: {}", app.state.status))
        .block(Block::default().borders(Borders::ALL).title("Status"));
    f.render_widget(status, layout[4]);
}

pub(super) fn draw_settings_info(f: &mut Frame<'_>, area: Rect, app: &App) {
    let panel = centered_rect(70, 70, area);
    let block = Block::default().borders(Borders::ALL).title("Settings");
    f.render_widget(Clear, panel);
    f.render_widget(block.clone(), panel);
    let inner = shrink(panel, 1);
    let text = vec![
        Line::from(format!("API base: {}", app.client.base_url())),
        Line::from(format!(
            "API token: {}",
            if app.client.has_token() { "set" } else { "-" }
        )),
        Line::from(format!(
            "Project token: {}",
            if app.client.has_project_token() {
                "set"
            } else {
                "-"
            }
        )),
        Line::from(format!(
            "Refresh interval: {}s",
            app.refresh_interval.as_secs()
        )),
        Line::from(format!(
            "Autologin: {}",
            if app.auto_login {
                "enabled"
            } else {
                "disabled"
            }
        )),
        Line::from(""),
        Line::from("Enter → open dashboard settings tab"),
        Line::from("c → configure API/token • m → main menu • q/Esc → back"),
    ];
    let para = Paragraph::new(text)
        .alignment(ratatui::layout::Alignment::Left)
        .block(block);
    f.render_widget(para, inner);
}

pub(super) fn draw_help(f: &mut Frame<'_>, area: Rect, _app: &App) {
    let panel = centered_rect(80, 75, area);
    let block = Block::default().borders(Borders::ALL).title("Help");
    f.render_widget(Clear, panel);
    f.render_widget(block.clone(), panel);
    let inner = shrink(panel, 1);
    let text = vec![
        heading_line("Navigation"),
        Line::from(" tab/shift-tab or ←/→ cycle pages • 1-7 jump • ↑↓/j k move • m main menu • w welcome • q/Esc back"),
        Line::from(""),
        heading_line("Pages"),
        Line::from(" Dashboard, Projects, Protocols, Steps, Events, Queues, Settings"),
        Line::from(" Dashboard = projects+protocols+steps+events; Steps/Events show scoped events; Queues show stats/jobs."),
        Line::from(""),
        heading_line("Actions"),
        Line::from(" Enter quick actions • n run next • t retry • y QA • a approve • o open PR"),
        Line::from(" s start • p pause • e resume • x cancel • f step filter • J job filter • [/] branch • r refresh"),
        Line::from(""),
        heading_line("Modals & CRUD"),
        Line::from(" g new project • R new protocol • i import CodeMachine • A spec audit • c configure tokens"),
        Line::from(" b reload branches • d delete branch (selected)"),
        Line::from(""),
        heading_line("Welcome / Menu"),
        Line::from(" Welcome: Start DevGodzilla, Settings, Help, Version, Quit"),
        Line::from(" Main menu: Dashboard, Configure API/token, Quit"),
        Line::from(""),
        heading_line("Environment"),
        Line::from(" DEVGODZILLA_API_BASE | DEVGODZILLA_API_TOKEN | DEVGODZILLA_PROJECT_TOKEN"),
        Line::from(" DEVGODZILLA_TUI_AUTOLOGIN (default 1) | DEVGODZILLA_TUI_REFRESH_SECS (default 4)"),
        Line::from(""),
        Line::from("Enter → dashboard • m → main menu • w → welcome • q/Esc → back"),
    ];
    let para = Paragraph::new(text)
        .alignment(ratatui::layout::Alignment::Left)
        .block(block);
    f.render_widget(para, inner);
}

pub(super) fn draw_version(f: &mut Frame<'_>, area: Rect, _app: &App) {
    let panel = centered_rect(60, 50, area);
    let block = Block::default().borders(Borders::ALL).title("Version");
    f.render_widget(Clear, panel);
    f.render_widget(block.clone(), panel);
    let inner = shrink(panel, 1);
    let text = vec![
        Line::from(format!("DevGodzilla TUI v{}", env!("CARGO_PKG_VERSION"))),
        Line::from("Rust ratatui client for the orchestrator."),
        Line::from(""),
        Line::from("m → main menu • q/Esc → back"),
    ];
    let para = Paragraph::new(text)
        .alignment(ratatui::layout::Alignment::Center)
        .block(block);
    f.render_widget(para, inner);
}

pub(super) fn draw_menu(f: &mut Frame<'_>, area: Rect, menu_index: usize, app: &App) {
    let panel = centered_rect(60, 50, area);
    let block = Block::default().borders(Borders::ALL).title("DevGodzilla");
    f.render_widget(Clear, panel);
    f.render_widget(block.clone(), panel);
    let inner = shrink(panel, 1);
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints(
            [
                Constraint::Length(3),
                Constraint::Length(9),
                Constraint::Length(3),
                Constraint::Length(3),
            ]
            .as_ref(),
        )
        .split(inner);

    let title = Paragraph::new("Main menu")
        .style(
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )
        .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(title, layout[0]);

    let items = ["Dashboard", "Configure API/token", "Quit"];
    let list_items: Vec<ListItem> = items
        .iter()
        .enumerate()
        .map(|(idx, item)| {
            let prefix = if idx == menu_index { "➤ " } else { "  " };
            ListItem::new(format!("{prefix}{item}"))
        })
        .collect();
    let list = List::new(list_items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Select an option"),
        )
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    f.render_widget(list, layout[1]);

    let help =
        Paragraph::new("Up/Down/Tab select • Enter confirm • 1/2/3 shortcuts • Esc back • q quit")
            .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(help, layout[2]);

    let status = Paragraph::new(format!("Status: {}", app.state.status))
        .block(Block::default().borders(Borders::ALL).title("Status"));
    f.render_widget(status, layout[3]);
}

pub(super) fn draw_modal(f: &mut Frame<'_>, size: Rect, modal: &Modal, app: &App) {
    let area = centered_rect(60, 60, size);
    f.render_widget(Clear, area);
    match modal {
        Modal::Confirm { title, message, .. } => {
            let para = Paragraph::new(vec![
                Line::from(title.clone()),
                Line::from(""),
                Line::from(message.clone()),
                Line::from("Enter to confirm, Esc to cancel"),
            ])
            .block(Block::default().borders(Borders::ALL).title(title.clone()))
            .wrap(Wrap { trim: true });
            f.render_widget(para, area);
        }
        Modal::Form {
            title,
            fields,
            focus,
            ..
        } => {
            let mut lines: Vec<Line> = Vec::new();
            lines.push(Line::from(title.clone()));
            lines.push(Line::from(""));
            for (idx, field) in fields.iter().enumerate() {
                let mut label = format!("{}: ", field.label);
                if idx == *focus {
                    label.insert_str(0, "> ");
                } else {
                    label.insert_str(0, "  ");
                }
                let value = if field.is_secret {
                    "******".to_string()
                } else {
                    field.value.clone()
                };
                lines.push(Line::from(format!("{label}{value}")));
            }
            lines.push(Line::from(""));
            if title.starts_with("Configure agent") {
                lines.push(Line::from(
                    "Enter submit • Tab next • Up/Down or Ctrl+j/k cycle options • Ctrl+U clear • Esc cancel",
                ));
                if *focus == 3 {
                    let available_models = app
                        .state
                        .agent_detail
                        .as_ref()
                        .or_else(|| {
                            app.state
                                .agent_index
                                .and_then(|idx| app.state.agents.get(idx))
                        })
                        .map(|agent| {
                            agent
                                .available_models
                                .iter()
                                .filter_map(|model| match model {
                                    serde_json::Value::String(value) => Some(value.clone()),
                                    serde_json::Value::Object(map) => map
                                        .get("value")
                                        .and_then(serde_json::Value::as_str)
                                        .or_else(|| {
                                            map.get("name").and_then(serde_json::Value::as_str)
                                        })
                                        .map(str::to_string),
                                    _ => None,
                                })
                                .take(6)
                                .collect::<Vec<_>>()
                        })
                        .unwrap_or_default();
                    if !available_models.is_empty() {
                        lines.push(Line::from(""));
                        lines.push(Line::from("Available models:"));
                        for model in available_models {
                            lines.push(Line::from(format!("  - {model}")));
                        }
                    }
                } else if *focus == 4 {
                    let current_model = fields
                        .get(3)
                        .map(|field| field.value.trim())
                        .unwrap_or_default();
                    let available_reasoning = app
                        .state
                        .agent_detail
                        .as_ref()
                        .or_else(|| {
                            app.state
                                .agent_index
                                .and_then(|idx| app.state.agents.get(idx))
                        })
                        .and_then(|agent| {
                            agent.available_models.iter().find_map(|model| {
                                let model_obj = model.as_object()?;
                                let value = model_obj.get("value")?.as_str()?;
                                if value != current_model {
                                    return None;
                                }
                                Some(
                                    model_obj
                                        .get("reasoning_efforts")
                                        .and_then(serde_json::Value::as_array)
                                        .map(|items| {
                                            items
                                                .iter()
                                                .filter_map(|item| {
                                                    item.as_object()
                                                        .and_then(|map| map.get("value"))
                                                        .and_then(serde_json::Value::as_str)
                                                        .map(str::to_string)
                                                })
                                                .take(6)
                                                .collect::<Vec<_>>()
                                        })
                                        .unwrap_or_default(),
                                )
                            })
                        })
                        .unwrap_or_default();
                    if !available_reasoning.is_empty() {
                        lines.push(Line::from(""));
                        lines.push(Line::from("Available reasoning levels:"));
                        for reasoning in available_reasoning {
                            lines.push(Line::from(format!("  - {reasoning}")));
                        }
                    }
                }
            } else {
                lines.push(Line::from("Enter submit • Tab next • Esc cancel"));
            }
            let para = Paragraph::new(lines)
                .block(Block::default().borders(Borders::ALL).title(title.clone()))
                .wrap(Wrap { trim: true });
            f.render_widget(para, area);
        }
        Modal::Palette { items, index } => {
            let mut lines: Vec<Line> = Vec::new();
            lines.push(Line::from("Actions"));
            lines.push(Line::from(""));
            for (idx, item) in items.iter().enumerate() {
                let label = format!(
                    "{} {}",
                    if idx == *index { "➤" } else { " " },
                    format_quick_action(*item)
                );
                lines.push(Line::from(label));
            }
            lines.push(Line::from(""));
            lines.push(Line::from("Enter run • j/k move • Esc close"));
            let para = Paragraph::new(lines)
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .title("Action palette"),
                )
                .wrap(Wrap { trim: true });
            f.render_widget(para, area);
        }
    }
}
