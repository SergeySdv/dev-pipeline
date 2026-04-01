use crate::app::App;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    text::Line,
    Frame,
};

use super::{render_list_block, render_paragraph_block};

pub(super) fn draw_quality(f: &mut Frame<'_>, area: Rect, app: &App) {
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
    draw_quality_nav(f, cols[0], app);
    draw_quality_chat(f, cols[1], app);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)].as_ref())
        .split(cols[2]);
    draw_quality_inspector(f, right[0], app);
    draw_quality_results(f, right[1], app);
}

fn draw_quality_nav(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items = vec![
        format!(
            "Protocols: {}",
            app.state
                .quality_dashboard
                .as_ref()
                .map(|d| d.overview.total_protocols)
                .unwrap_or(0)
        ),
        format!(
            "Passed: {}",
            app.state
                .quality_dashboard
                .as_ref()
                .map(|d| d.overview.passed)
                .unwrap_or(0)
        ),
        format!(
            "Warnings: {}",
            app.state
                .quality_dashboard
                .as_ref()
                .map(|d| d.overview.warnings)
                .unwrap_or(0)
        ),
        format!(
            "Failed: {}",
            app.state
                .quality_dashboard
                .as_ref()
                .map(|d| d.overview.failed)
                .unwrap_or(0)
        ),
    ];
    render_list_block(f, area, "Quality Views", items);
}

fn draw_quality_chat(f: &mut Frame<'_>, area: Rect, app: &App) {
    let lines = if let Some(dashboard) = &app.state.quality_dashboard {
        vec![
            Line::from("You> show me current quality failures"),
            Line::from(""),
            Line::from(format!(
                "Agent> Quality overview loaded. fail={} warn={} pass={}",
                dashboard.overview.failed, dashboard.overview.warnings, dashboard.overview.passed
            )),
            Line::from("[tool ] fetched dashboard and recent findings"),
        ]
    } else {
        vec![Line::from("Quality dashboard unavailable.")]
    };
    render_paragraph_block(f, area, "Chat / Transcript", lines);
}

fn draw_quality_inspector(f: &mut Frame<'_>, area: Rect, app: &App) {
    let lines = if let Some(dashboard) = &app.state.quality_dashboard {
        let mut lines = vec![
            Line::from(format!(
                "average score: {}",
                dashboard.overview.average_score
            )),
            Line::from(format!(
                "recent findings: {}",
                dashboard.recent_findings.len()
            )),
            Line::from(format!(
                "constitutional gates: {}",
                dashboard.constitutional_gates.len()
            )),
        ];
        if let Some(summary) = &app.state.metrics_summary {
            lines.push(Line::from(format!("job runs: {}", summary.total_job_runs)));
            lines.push(Line::from(format!(
                "protocol success: {}%",
                summary.success_rate
            )));
        }
        lines
    } else {
        vec![Line::from("No dashboard loaded.")]
    };
    render_paragraph_block(f, area, "Quality Summary", lines);
}

fn draw_quality_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(55), Constraint::Percentage(45)].as_ref())
        .split(area);
    render_list_block(
        f,
        chunks[0],
        "Results / Findings",
        app.state
            .quality_dashboard
            .as_ref()
            .map(|dashboard| {
                dashboard
                    .recent_findings
                    .iter()
                    .map(|finding| {
                        format!(
                            "{} [{}] {}",
                            finding.project_name, finding.severity, finding.message
                        )
                    })
                    .collect()
            })
            .unwrap_or_else(|| vec!["No findings.".to_string()]),
    );
    render_list_block(
        f,
        chunks[1],
        "Results / Constitutional Gates",
        app.state
            .quality_dashboard
            .as_ref()
            .map(|dashboard| {
                dashboard
                    .constitutional_gates
                    .iter()
                    .map(|gate| format!("{} [{}] checks={}", gate.name, gate.status, gate.checks))
                    .collect()
            })
            .unwrap_or_else(|| vec!["No constitutional gates.".to_string()]),
    );
}
