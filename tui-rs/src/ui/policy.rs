use crate::app::App;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Style},
    text::Line,
    widgets::{Block, Borders, List, ListItem},
    Frame,
};

use super::{pretty_json_lines, render_paragraph_block};

pub(super) fn draw_policy(f: &mut Frame<'_>, area: Rect, app: &App) {
    let cols = Layout::default()
        .direction(Direction::Horizontal)
        .constraints(
            [
                Constraint::Percentage(24),
                Constraint::Percentage(41),
                Constraint::Percentage(35),
            ]
            .as_ref(),
        )
        .split(area);
    draw_policy_pack_list(f, cols[0], app);
    draw_policy_chat(f, cols[1], app);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(56), Constraint::Percentage(44)].as_ref())
        .split(cols[2]);
    draw_policy_inspector(f, right[0], app);
    draw_policy_results(f, right[1], app);
}

fn draw_policy_pack_list(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .state
        .policy_packs
        .iter()
        .map(|pack| ListItem::new(format!("{} {} [{}]", pack.key, pack.version, pack.status)))
        .collect();
    let mut list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title("Policy Packs"))
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    if let Some(idx) = app.state.policy_pack_index {
        list = list.highlight_symbol("➤ ");
        f.render_stateful_widget(list, area, &mut super::make_state(idx));
    } else {
        f.render_widget(list, area);
    }
}

fn draw_policy_chat(f: &mut Frame<'_>, area: Rect, app: &App) {
    let lines = if let Some(pack) = &app.state.policy_pack_detail {
        vec![
            Line::from(format!("You> /policy show {}", pack.key)),
            Line::from(""),
            Line::from(format!(
                "Agent> Policy pack {} loaded. version={} status={}",
                pack.key, pack.version, pack.status
            )),
        ]
    } else {
        vec![Line::from("Select a policy pack to inspect it.")]
    };
    render_paragraph_block(f, area, "Chat / Transcript", lines);
}

fn draw_policy_inspector(f: &mut Frame<'_>, area: Rect, app: &App) {
    let lines = if let Some(pack) = &app.state.policy_pack_detail {
        vec![
            Line::from(format!("name: {}", pack.name)),
            Line::from(format!("version: {}", pack.version)),
            Line::from(format!("status: {}", pack.status)),
            Line::from(format!(
                "description: {}",
                pack.description.clone().unwrap_or_else(|| "-".into())
            )),
        ]
    } else {
        vec![Line::from("No policy pack selected.")]
    };
    render_paragraph_block(f, area, "Policy Pack", lines);
}

fn draw_policy_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let lines = app
        .state
        .policy_pack_detail
        .as_ref()
        .map(|pack| pretty_json_lines(&pack.pack))
        .unwrap_or_else(|| vec![Line::from("No policy pack content loaded.")]);
    render_paragraph_block(f, area, "Results / Pack", lines);
}
