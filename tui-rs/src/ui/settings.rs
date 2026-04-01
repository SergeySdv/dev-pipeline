use crate::app::App;
use crate::state::SettingsTab;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    text::Line,
    Frame,
};

use super::{render_list_block, render_paragraph_block, tabs_line};

pub(super) fn draw_settings(f: &mut Frame<'_>, area: Rect, app: &App) {
    let cols = Layout::default()
        .direction(Direction::Horizontal)
        .constraints(
            [
                Constraint::Percentage(22),
                Constraint::Percentage(43),
                Constraint::Percentage(35),
            ]
            .as_ref(),
        )
        .split(area);
    draw_settings_nav(f, cols[0], app);
    draw_settings_chat(f, cols[1], app);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(56), Constraint::Percentage(44)].as_ref())
        .split(cols[2]);
    draw_settings_inspector(f, right[0], app);
    draw_settings_results(f, right[1], app);
}

fn draw_settings_nav(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items = vec![
        format!(
            "{} connection",
            if app.state.settings_tab == SettingsTab::Connection {
                ">"
            } else {
                " "
            }
        ),
        format!(
            "{} profile",
            if app.state.settings_tab == SettingsTab::Profile {
                ">"
            } else {
                " "
            }
        ),
    ];
    render_list_block(f, area, "Settings", items);
}

fn draw_settings_chat(f: &mut Frame<'_>, area: Rect, app: &App) {
    let lines = match app.state.settings_tab {
        SettingsTab::Connection => vec![
            Line::from("You> /config show"),
            Line::from(""),
            Line::from("Agent> Connection settings loaded."),
        ],
        SettingsTab::Profile => {
            let profile_name = app
                .state
                .profile
                .as_ref()
                .map(|profile| profile.name.clone())
                .unwrap_or_else(|| "unknown".into());
            vec![
                Line::from("You> /profile show"),
                Line::from(""),
                Line::from(format!("Agent> Profile loaded for {}.", profile_name)),
            ]
        }
    };
    render_paragraph_block(f, area, "Chat / Transcript", lines);
}

fn draw_settings_inspector(f: &mut Frame<'_>, area: Rect, app: &App) {
    let mut lines = vec![settings_tabs_line(app.state.settings_tab), Line::from("")];
    match app.state.settings_tab {
        SettingsTab::Connection => {
            lines.extend(vec![
                Line::from(format!("API base: {}", app.client.base_url())),
                Line::from(format!(
                    "Token: {}",
                    if app.client.has_token() {
                        "configured"
                    } else {
                        "-"
                    }
                )),
                Line::from(format!(
                    "Project token: {}",
                    if app.client.has_project_token() {
                        "configured"
                    } else {
                        "-"
                    }
                )),
                Line::from(format!("Auto-refresh: {}s", app.refresh_interval.as_secs())),
            ]);
        }
        SettingsTab::Profile => {
            if let Some(profile) = &app.state.profile {
                lines.extend(vec![
                    Line::from(format!("name: {}", profile.name)),
                    Line::from(format!("email: {}", profile.email)),
                    Line::from(format!("role: {}", profile.role)),
                    Line::from(format!("member since: {}", profile.member_since)),
                ]);
            } else {
                lines.push(Line::from("No profile loaded."));
            }
        }
    }
    render_paragraph_block(f, area, "Settings Inspector", lines);
}

fn draw_settings_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    match app.state.settings_tab {
        SettingsTab::Connection => render_paragraph_block(
            f,
            area,
            "Results / Connection",
            vec![
                Line::from("Use `c` to reconfigure API base and tokens."),
                Line::from("The TUI remains Rust-only; these settings only change API access."),
            ],
        ),
        SettingsTab::Profile => render_list_block(
            f,
            area,
            "Results / Activity",
            app.state
                .profile
                .as_ref()
                .map(|profile| {
                    profile
                        .activity
                        .iter()
                        .map(|item| format!("{} · {}", item.action, item.target))
                        .collect()
                })
                .unwrap_or_else(|| vec!["No profile activity.".to_string()]),
        ),
    }
}

fn settings_tabs_line(active: SettingsTab) -> Line<'static> {
    let tabs = [SettingsTab::Connection, SettingsTab::Profile];
    tabs_line(
        tabs.iter()
            .map(|tab| (tab.label(), *tab == active))
            .collect(),
    )
}
