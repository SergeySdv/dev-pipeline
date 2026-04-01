use crate::app::App;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Style},
    text::Line,
    widgets::{Block, Borders, List, ListItem},
    Frame,
};

use super::{render_list_block, render_paragraph_block, review_links_lines, trunc_lines};

pub(super) fn draw_runs(f: &mut Frame<'_>, area: Rect, app: &App) {
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
    draw_run_list(f, cols[0], app);
    draw_run_chat(f, cols[1], app);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(56), Constraint::Percentage(44)].as_ref())
        .split(cols[2]);
    draw_run_inspector(f, right[0], app);
    draw_run_results(f, right[1], app);
}

fn draw_run_list(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .state
        .runs
        .iter()
        .map(|run| ListItem::new(format!("{} [{}] {}", run.run_id, run.status, run.job_type)))
        .collect();
    let mut list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title("Runs"))
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    if let Some(idx) = app.state.run_index {
        list = list.highlight_symbol("➤ ");
        f.render_stateful_widget(list, area, &mut super::make_state(idx));
    } else {
        f.render_widget(list, area);
    }
}

fn draw_run_chat(f: &mut Frame<'_>, area: Rect, app: &App) {
    let run = app
        .state
        .run_detail
        .as_ref()
        .or_else(|| app.state.run_index.and_then(|idx| app.state.runs.get(idx)));
    let lines = if let Some(run) = run {
        vec![
            Line::from(format!("You> /run show {}", run.run_id)),
            Line::from(""),
            Line::from(format!(
                "Agent> Run {} loaded. status={} job_type={}",
                run.run_id, run.status, run.job_type
            )),
            Line::from(format!(
                "       protocol={}  step={}  attempt={}",
                run.protocol_run_id
                    .map(|v| v.to_string())
                    .unwrap_or_else(|| "-".into()),
                run.step_run_id
                    .map(|v| v.to_string())
                    .unwrap_or_else(|| "-".into()),
                run.attempt
                    .map(|v| v.to_string())
                    .unwrap_or_else(|| "-".into())
            )),
        ]
    } else {
        vec![Line::from("Select a run to inspect logs and artifacts.")]
    };
    render_paragraph_block(f, area, "Chat / Transcript", lines);
}

fn draw_run_inspector(f: &mut Frame<'_>, area: Rect, app: &App) {
    let run = app
        .state
        .run_detail
        .as_ref()
        .or_else(|| app.state.run_index.and_then(|idx| app.state.runs.get(idx)));
    let title = run
        .map(|run| format!("Run {}", run.run_id))
        .unwrap_or_else(|| "Run".to_string());
    let lines = if let Some(run) = run {
        let mut lines = vec![
            Line::from(format!("status: {}", run.status)),
            Line::from(format!(
                "kind: {}",
                run.run_kind.as_deref().unwrap_or(run.job_type.as_str())
            )),
            Line::from(format!(
                "protocol: {}",
                run.protocol_run_id
                    .map(|v| v.to_string())
                    .unwrap_or_else(|| "-".into())
            )),
            Line::from(format!(
                "step: {}",
                run.step_run_id
                    .map(|v| v.to_string())
                    .unwrap_or_else(|| "-".into())
            )),
            Line::from(format!(
                "tokens: {}",
                run.cost_tokens
                    .map(|v| v.to_string())
                    .unwrap_or_else(|| "-".into())
            )),
            Line::from(format!(
                "log path: {}",
                run.log_path.as_deref().unwrap_or("-")
            )),
        ];
        lines.push(Line::from(""));
        lines.extend(review_links_lines(app, 4));
        lines
    } else {
        vec![Line::from("No run selected.")]
    };
    render_paragraph_block(f, area, &title, lines);
}

fn draw_run_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(58), Constraint::Percentage(42)].as_ref())
        .split(area);
    let artifact_lines: Vec<String> = app
        .state
        .run_artifacts
        .iter()
        .take(10)
        .map(|artifact| format!("{} [{}]", artifact.name, artifact.r#type))
        .collect();
    render_list_block(f, chunks[0], "Results / Artifacts", artifact_lines);
    let log_lines = app
        .state
        .run_logs
        .as_ref()
        .map(|logs| trunc_lines(&logs.content, 12))
        .unwrap_or_else(|| vec![Line::from("No logs loaded.")]);
    render_paragraph_block(f, chunks[1], "Results / Logs", log_lines);
}
