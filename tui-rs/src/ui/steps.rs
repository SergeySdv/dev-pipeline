use crate::app::App;
use crate::state::StepWorkspaceTab;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Style},
    text::Line,
    widgets::{Block, Borders, List, ListItem},
    Frame,
};
use serde_json::Value;

use super::{render_list_block, render_paragraph_block, review_links_lines, tabs_line};

pub(super) fn draw_steps(f: &mut Frame<'_>, area: Rect, app: &App) {
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
    draw_step_list(f, cols[0], app);
    draw_step_chat(f, cols[1], app);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(56), Constraint::Percentage(44)].as_ref())
        .split(cols[2]);
    draw_step_inspector(f, right[0], app);
    draw_step_results(f, right[1], app);
}

pub(super) fn draw_step_list(f: &mut Frame<'_>, area: Rect, app: &App) {
    let filter_label = app
        .state
        .step_filter
        .clone()
        .unwrap_or_else(|| "all".into());
    let items: Vec<ListItem> = app
        .state
        .steps
        .iter()
        .map(|s| {
            let status = s.status.clone();
            ListItem::new(format!(
                "{}: {} [{status}] (r={})",
                s.step_index, s.step_name, s.retries
            ))
        })
        .collect();
    let mut list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(format!("Steps (filter: {filter_label})")),
        )
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    if let Some(idx) = app.state.step_index {
        list = list.highlight_symbol("➤ ");
        f.render_stateful_widget(list, area, &mut super::make_state(idx));
    } else {
        f.render_widget(list, area);
    }
}

fn draw_step_chat(f: &mut Frame<'_>, area: Rect, app: &App) {
    let step = app.state.step_detail.as_ref().or_else(|| {
        app.state
            .step_index
            .and_then(|idx| app.state.steps.get(idx))
    });
    let Some(step) = step else {
        render_paragraph_block(
            f,
            area,
            "Chat / Transcript",
            vec![Line::from("Select a step to inspect it.")],
        );
        return;
    };
    let lines = vec![
        Line::from(format!("You> /step show {}", step.id)),
        Line::from(""),
        Line::from(format!("Agent> Step {} loaded.", step.step_name)),
        Line::from(format!(
            "       status={}  engine={}  model={}",
            step.status,
            step.engine_id.as_deref().unwrap_or("-"),
            step.model.as_deref().unwrap_or("-")
        )),
        Line::from(format!(
            "       runs={}  artifacts={}  policy_findings={}",
            app.state.step_runs.len(),
            app.state.step_artifacts.len(),
            app.state.step_policy_findings.len()
        )),
    ];
    render_paragraph_block(f, area, "Chat / Transcript", lines);
}

fn draw_step_inspector(f: &mut Frame<'_>, area: Rect, app: &App) {
    let step = app.state.step_detail.as_ref().or_else(|| {
        app.state
            .step_index
            .and_then(|idx| app.state.steps.get(idx))
    });
    let title = step
        .map(|step| format!("Step {} · {}", step.id, step.step_name))
        .unwrap_or_else(|| "Step".to_string());
    let mut lines = vec![
        step_workspace_tabs_line(app.state.step_workspace_tab),
        Line::from(""),
    ];
    lines.extend(match app.state.step_workspace_tab {
        StepWorkspaceTab::Summary => vec![
            Line::from(format!(
                "status: {}",
                step.map(|s| s.status.clone()).unwrap_or_else(|| "-".into())
            )),
            Line::from(format!(
                "agent: {}",
                step.and_then(|s| s.assigned_agent.clone())
                    .unwrap_or_else(|| "-".into())
            )),
            Line::from(format!(
                "retries: {}",
                step.map(|s| s.retries).unwrap_or_default()
            )),
        ],
        StepWorkspaceTab::Runs => vec![
            Line::from(format!("runs: {}", app.state.step_runs.len())),
            Line::from(format!("latest run: {}", latest_step_run_id(app))),
        ],
        StepWorkspaceTab::Artifacts => vec![
            Line::from(format!("artifacts: {}", app.state.step_artifacts.len())),
            Line::from("step artifacts include logs, reports, and patches"),
        ],
        StepWorkspaceTab::Quality => step_quality_summary_lines(app),
        StepWorkspaceTab::Policy => vec![
            Line::from(format!(
                "policy findings: {}",
                app.state.step_policy_findings.len()
            )),
            Line::from("review blocking findings before approve"),
        ],
        StepWorkspaceTab::Runtime => vec![
            Line::from(format!(
                "runtime keys: {}",
                step.and_then(|s| s
                    .runtime_state
                    .as_ref()
                    .and_then(Value::as_object)
                    .map(|m| m.len()))
                    .unwrap_or(0)
            )),
            Line::from(format!(
                "summary: {}",
                step.and_then(|s| s.summary.clone())
                    .unwrap_or_else(|| "-".into())
            )),
        ],
    });
    lines.push(Line::from(""));
    lines.extend(review_links_lines(app, 3));
    render_paragraph_block(f, area, &title, lines);
}

fn draw_step_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    match app.state.step_workspace_tab {
        StepWorkspaceTab::Summary => {
            render_paragraph_block(f, area, "Results / Summary", step_runtime_lines(app))
        }
        StepWorkspaceTab::Runs => render_list_block(
            f,
            area,
            "Results / Runs",
            app.state
                .step_runs
                .iter()
                .take(12)
                .map(|run| format!("{} [{}] {}", run.run_id, run.status, run.job_type))
                .collect(),
        ),
        StepWorkspaceTab::Artifacts => render_list_block(
            f,
            area,
            "Results / Artifacts",
            app.state
                .step_artifacts
                .iter()
                .take(12)
                .map(|artifact| format!("{} [{}]", artifact.name, artifact.r#type))
                .collect(),
        ),
        StepWorkspaceTab::Quality => render_list_block(
            f,
            area,
            "Results / Quality",
            app.state
                .step_quality
                .as_ref()
                .map(|quality| {
                    quality
                        .gates
                        .iter()
                        .map(|gate| format!("{} [{}]", gate.name, gate.status))
                        .collect()
                })
                .unwrap_or_else(|| vec!["No QA summary.".to_string()]),
        ),
        StepWorkspaceTab::Policy => render_list_block(
            f,
            area,
            "Results / Policy",
            app.state
                .step_policy_findings
                .iter()
                .take(12)
                .map(|finding| {
                    format!(
                        "{} [{}] {}",
                        finding.code, finding.severity, finding.message
                    )
                })
                .collect(),
        ),
        StepWorkspaceTab::Runtime => {
            render_paragraph_block(f, area, "Results / Runtime", step_runtime_lines(app))
        }
    }
}

fn step_workspace_tabs_line(active: StepWorkspaceTab) -> Line<'static> {
    let tabs = [
        StepWorkspaceTab::Summary,
        StepWorkspaceTab::Runs,
        StepWorkspaceTab::Artifacts,
        StepWorkspaceTab::Quality,
        StepWorkspaceTab::Policy,
        StepWorkspaceTab::Runtime,
    ];
    tabs_line(
        tabs.iter()
            .map(|tab| (tab.label(), *tab == active))
            .collect(),
    )
}

fn latest_step_run_id(app: &App) -> String {
    app.state
        .step_runs
        .first()
        .map(|run| run.run_id.clone())
        .unwrap_or_else(|| "-".to_string())
}

fn step_quality_summary_lines(app: &App) -> Vec<Line<'static>> {
    let Some(quality) = &app.state.step_quality else {
        return vec![Line::from("No step quality summary.")];
    };
    vec![
        Line::from(format!("overall: {}", quality.overall_status)),
        Line::from(format!("score: {:.0}%", quality.score * 100.0)),
        Line::from(format!("blocking issues: {}", quality.blocking_issues)),
        Line::from(format!("warnings: {}", quality.warnings)),
    ]
}

fn step_runtime_lines(app: &App) -> Vec<Line<'static>> {
    let Some(step) = app.state.step_detail.as_ref() else {
        return vec![Line::from("No runtime data.")];
    };
    let mut lines = vec![
        Line::from(format!(
            "assigned agent: {}",
            step.assigned_agent
                .clone()
                .unwrap_or_else(|| "-".to_string())
        )),
        Line::from(format!(
            "parallel group: {}",
            step.parallel_group
                .clone()
                .unwrap_or_else(|| "-".to_string())
        )),
    ];
    if let Some(runtime) = &step.runtime_state {
        lines.extend(super::pretty_json_lines(runtime));
    } else {
        lines.push(Line::from("runtime_state: -"));
    }
    lines
}
