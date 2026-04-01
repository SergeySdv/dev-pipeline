use crate::app::App;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Style},
    text::Line,
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap},
    Frame,
};

use super::{
    event_detail::draw_event_detail, format_value, render_list_block, render_paragraph_block,
    yes_no,
};

pub(super) fn draw_dashboard(f: &mut Frame<'_>, area: Rect, app: &App) {
    let cols = Layout::default()
        .direction(Direction::Horizontal)
        .constraints(
            [
                Constraint::Percentage(30),
                Constraint::Percentage(30),
                Constraint::Percentage(40),
            ]
            .as_ref(),
        )
        .split(area);

    super::projects::draw_project_list(f, cols[0], app);
    super::protocols::draw_protocol_list(f, cols[1], app);

    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(60), Constraint::Percentage(40)].as_ref())
        .split(cols[2]);

    super::steps::draw_step_list(f, right[0], app);
    draw_event_list(f, right[1], app, false);
}

pub(super) fn draw_events(f: &mut Frame<'_>, area: Rect, app: &App) {
    let rows = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(70), Constraint::Percentage(30)].as_ref())
        .split(area);
    let layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)].as_ref())
        .split(rows[0]);
    draw_event_list(f, layout[0], app, true);
    draw_recent_events(f, layout[1], app);
    let lower = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(58), Constraint::Percentage(42)].as_ref())
        .split(rows[1]);
    draw_event_detail(f, lower[0], app);
    let metrics_lines = app
        .state
        .metrics_summary
        .as_ref()
        .map(|summary| {
            let mut lines = vec![
                Line::from(format!("success rate: {}%", summary.success_rate)),
                Line::from(format!("recent events: {}", summary.recent_events_count)),
                Line::from(format!("job runs: {}", summary.total_job_runs)),
                Line::from(format!("degraded: {}", yes_no(summary.degraded))),
            ];
            if let Some(filter) = &app.state.event_filter {
                lines.push(Line::from(format!("event filter: {filter}")));
            }
            lines
        })
        .unwrap_or_else(|| vec![Line::from("Metrics unavailable.")]);
    render_paragraph_block(f, lower[1], "Ops / Metrics", metrics_lines);
}

pub(super) fn draw_queues(f: &mut Frame<'_>, area: Rect, app: &App) {
    let outer = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(34), Constraint::Percentage(66)].as_ref())
        .split(area);
    let stats_text = format_value(&app.state.queue_stats);
    let stats = Paragraph::new(stats_text)
        .block(Block::default().borders(Borders::ALL).title("Queue stats"))
        .wrap(Wrap { trim: true });
    f.render_widget(stats, outer[0]);

    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(60), Constraint::Percentage(40)].as_ref())
        .split(outer[1]);

    let items: Vec<ListItem> = app
        .state
        .queue_jobs
        .iter()
        .map(|job| {
            let label = format!(
                "{} [{}]",
                job.job_id.clone().unwrap_or_else(|| "-".to_string()),
                job.status.clone().unwrap_or_else(|| "-".to_string())
            );
            ListItem::new(label)
        })
        .collect();
    let list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title(format!(
            "Queue jobs ({})",
            app.state
                .job_status_filter
                .clone()
                .unwrap_or_else(|| "all".into())
        )))
        .highlight_style(Style::default().bg(Color::Blue));
    if app.state.queue_jobs.is_empty() {
        f.render_widget(list, right[0]);
    } else {
        let mut state = ListState::default();
        state.select(app.state.queue_job_index);
        let list = list.highlight_symbol("➤ ");
        f.render_stateful_widget(list, right[0], &mut state);
    }

    let lower = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(56), Constraint::Percentage(44)].as_ref())
        .split(right[1]);

    let job_lines = app
        .state
        .selected_queue_job()
        .map(|job| {
            let mut lines = vec![
                format!(
                    "job: {}",
                    job.job_id.clone().unwrap_or_else(|| "-".to_string())
                ),
                format!(
                    "status: {}",
                    job.status.clone().unwrap_or_else(|| "-".to_string())
                ),
                format!(
                    "type: {}",
                    job.job_type.clone().unwrap_or_else(|| "-".to_string())
                ),
            ];
            if let Some(enqueued_at) = job.enqueued_at.as_deref() {
                lines.push(format!("enqueued: {enqueued_at}"));
            }
            if let Some(started_at) = job.started_at.as_deref() {
                lines.push(format!("started: {started_at}"));
            }
            if let Some(ended_at) = job.ended_at.as_deref() {
                lines.push(format!("ended: {ended_at}"));
            }
            lines
        })
        .unwrap_or_else(|| vec!["Select a queue job.".to_string()]);
    render_list_block(f, lower[0], "Queue Job Detail", job_lines);

    let ops_lines = app
        .state
        .metrics_summary
        .as_ref()
        .map(|summary| {
            summary
                .job_type_metrics
                .iter()
                .take(6)
                .map(|metric| {
                    format!(
                        "{} count={} avg={}s",
                        metric.job_type,
                        metric.count,
                        metric
                            .avg_duration_seconds
                            .map(|v| format!("{v:.1}"))
                            .unwrap_or_else(|| "-".into())
                    )
                })
                .collect()
        })
        .unwrap_or_else(|| vec!["No metrics loaded.".to_string()]);
    render_list_block(f, lower[1], "Ops / Job Types", ops_lines);
}

pub(super) fn draw_event_list(f: &mut Frame<'_>, area: Rect, app: &App, scoped: bool) {
    let events = if scoped {
        &app.state.events
    } else {
        &app.state.recent_events
    };
    let items: Vec<ListItem> = events
        .iter()
        .rev()
        .take(30)
        .map(|e| ListItem::new(format!("{}: {}", e.event_type, e.message)))
        .collect();
    let block = Block::default().borders(Borders::ALL).title("Events");
    if scoped {
        let mut list = List::new(items)
            .block(block)
            .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
        if let Some(idx) = app.state.event_index {
            let mut state = ListState::default();
            state.select(Some((events.len().saturating_sub(1)).saturating_sub(idx)));
            list = list.highlight_symbol("➤ ");
            f.render_stateful_widget(list, area, &mut state);
            return;
        }
        f.render_widget(list, area);
    } else {
        let list = List::new(items).block(block);
        f.render_widget(list, area);
    }
}

fn draw_recent_events(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .state
        .recent_events
        .iter()
        .take(30)
        .map(|e| ListItem::new(format!("{}: {}", e.event_type, e.message)))
        .collect();
    let block = Block::default()
        .borders(Borders::ALL)
        .title("Recent events");
    let mut list = List::new(items).block(block);
    if let Some(idx) = app.state.recent_event_index {
        let mut state = ListState::default();
        state.select(Some(idx));
        list = list.highlight_symbol("➤ ");
        f.render_stateful_widget(list, area, &mut state);
    } else {
        f.render_widget(list, area);
    }
}
