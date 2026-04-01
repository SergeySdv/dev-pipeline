use crate::app::App;
use crate::state::ProtocolWorkspaceTab;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Style},
    text::Line,
    widgets::{Block, Borders, List, ListItem},
    Frame,
};

use super::{render_list_block, render_paragraph_block, review_links_lines, tabs_line};

pub(super) fn draw_protocols(f: &mut Frame<'_>, area: Rect, app: &App) {
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
    draw_protocol_list(f, cols[0], app);
    draw_protocol_chat(f, cols[1], app);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(56), Constraint::Percentage(44)].as_ref())
        .split(cols[2]);
    draw_protocol_inspector(f, right[0], app);
    draw_protocol_results(f, right[1], app);
}

pub(super) fn draw_protocol_list(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .state
        .protocols
        .iter()
        .map(|r| {
            let status = r.status.clone().unwrap_or_else(|| "-".into());
            let branch = r.base_branch.clone().unwrap_or_else(|| "-".into());
            ListItem::new(format!(
                "{} • {} [{status}] ({branch})",
                r.id, r.protocol_name
            ))
        })
        .collect();
    let mut list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title("Protocols"))
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    if let Some(idx) = app.state.protocol_index {
        list = list.highlight_symbol("➤ ");
        f.render_stateful_widget(list, area, &mut super::make_state(idx));
    } else {
        f.render_widget(list, area);
    }
}

fn draw_protocol_chat(f: &mut Frame<'_>, area: Rect, app: &App) {
    let protocol = app.state.protocol_detail.as_ref().or_else(|| {
        app.state
            .protocol_index
            .and_then(|idx| app.state.protocols.get(idx))
    });
    let Some(protocol) = protocol else {
        render_paragraph_block(
            f,
            area,
            "Chat / Transcript",
            vec![Line::from("Select a protocol to open its workspace.")],
        );
        return;
    };
    let lines = vec![
        Line::from(format!("You> /protocol show {}", protocol.id)),
        Line::from(""),
        Line::from(format!(
            "Agent> Protocol {} loaded.",
            protocol.protocol_name
        )),
        Line::from(format!(
            "       status={}  steps={}  runs={}",
            protocol.status.as_deref().unwrap_or("-"),
            app.state.steps.len(),
            app.state.protocol_runs.len()
        )),
        Line::from(format!(
            "       clarifications={}  policy_findings={}  artifacts={}",
            app.state.protocol_clarifications.len(),
            app.state.protocol_policy_findings.len(),
            app.state.protocol_artifacts.len()
        )),
        Line::from("[tool ] fetched steps, runs, quality, policy, spec, artifacts, and feedback"),
        Line::from(format!(
            "[hint ] active protocol tab: {}",
            app.state.protocol_workspace_tab.label()
        )),
    ];
    render_paragraph_block(f, area, "Chat / Transcript", lines);
}

fn draw_protocol_inspector(f: &mut Frame<'_>, area: Rect, app: &App) {
    let protocol = app.state.protocol_detail.as_ref().or_else(|| {
        app.state
            .protocol_index
            .and_then(|idx| app.state.protocols.get(idx))
    });
    let title = protocol
        .map(|protocol| format!("Protocol {} · {}", protocol.id, protocol.protocol_name))
        .unwrap_or_else(|| "Protocol".to_string());
    let mut lines = vec![
        protocol_workspace_tabs_line(app.state.protocol_workspace_tab),
        Line::from(""),
    ];
    lines.extend(match app.state.protocol_workspace_tab {
        ProtocolWorkspaceTab::Summary => vec![
            Line::from(format!(
                "status: {}",
                protocol
                    .and_then(|p| p.status.clone())
                    .unwrap_or_else(|| "-".to_string())
            )),
            Line::from(format!("steps: {}", app.state.steps.len())),
            Line::from(format!("runs: {}", app.state.protocol_runs.len())),
            Line::from(format!(
                "branch: {}",
                protocol
                    .and_then(|p| p.base_branch.clone())
                    .unwrap_or_else(|| "-".to_string())
            )),
        ],
        ProtocolWorkspaceTab::Steps => vec![
            Line::from(format!(
                "step filter: {}",
                app.state
                    .step_filter
                    .clone()
                    .unwrap_or_else(|| "all".into())
            )),
            Line::from(format!("selected step: {}", selected_step_label(app))),
            Line::from("review step state before running or QA"),
        ],
        ProtocolWorkspaceTab::Runs => vec![
            Line::from(format!("job runs: {}", app.state.protocol_runs.len())),
            Line::from(format!("latest run: {}", latest_protocol_run_id(app))),
            Line::from("open the Runs page for deeper run inspection"),
        ],
        ProtocolWorkspaceTab::Events => vec![
            Line::from(format!("events: {}", app.state.events.len())),
            Line::from(format!("latest event: {}", latest_event_type(app))),
            Line::from("events stay scoped to the current protocol"),
        ],
        ProtocolWorkspaceTab::Quality => protocol_quality_summary_lines(app),
        ProtocolWorkspaceTab::Policy => vec![
            Line::from(format!(
                "pack: {}",
                app.state
                    .protocol_policy_snapshot
                    .as_ref()
                    .map(|p| p.pack_key.clone())
                    .unwrap_or_else(|| "-".to_string())
            )),
            Line::from(format!(
                "version: {}",
                app.state
                    .protocol_policy_snapshot
                    .as_ref()
                    .map(|p| p.pack_version.clone())
                    .unwrap_or_else(|| "-".to_string())
            )),
            Line::from(format!(
                "findings: {}",
                app.state.protocol_policy_findings.len()
            )),
        ],
        ProtocolWorkspaceTab::Clarify => vec![
            Line::from(format!(
                "open clarifications: {}",
                app.state.protocol_clarifications.len()
            )),
            Line::from(
                "answering is still API-driven; this view keeps the blocking context visible",
            ),
        ],
        ProtocolWorkspaceTab::Spec => vec![
            Line::from(format!(
                "spec run: {}",
                app.state
                    .protocol_spec
                    .as_ref()
                    .and_then(|s| s.spec_run_id)
                    .map(|id| id.to_string())
                    .unwrap_or_else(|| "-".to_string())
            )),
            Line::from(format!(
                "validation: {}",
                app.state
                    .protocol_spec
                    .as_ref()
                    .and_then(|s| s.validation_status.clone())
                    .unwrap_or_else(|| "-".to_string())
            )),
        ],
        ProtocolWorkspaceTab::Artifacts => vec![
            Line::from(format!("artifacts: {}", app.state.protocol_artifacts.len())),
            Line::from("protocol-level artifacts are aggregated from steps"),
        ],
        ProtocolWorkspaceTab::Feedback => vec![
            Line::from(format!(
                "feedback events: {}",
                app.state.protocol_feedback.len()
            )),
            Line::from("clarification feed doubles as the feedback stream"),
        ],
    });
    lines.push(Line::from(""));
    lines.extend(review_links_lines(app, 3));
    render_paragraph_block(f, area, &title, lines);
}

fn draw_protocol_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    match app.state.protocol_workspace_tab {
        ProtocolWorkspaceTab::Summary | ProtocolWorkspaceTab::Steps => {
            super::steps::draw_step_list(f, area, app)
        }
        ProtocolWorkspaceTab::Runs => render_list_block(
            f,
            area,
            "Results / Runs",
            app.state
                .protocol_runs
                .iter()
                .take(12)
                .map(|run| {
                    format!(
                        "{} [{}] {}",
                        run.run_id,
                        run.status,
                        run.run_kind.as_deref().unwrap_or(run.job_type.as_str())
                    )
                })
                .collect(),
        ),
        ProtocolWorkspaceTab::Events => super::ops::draw_event_list(f, area, app, true),
        ProtocolWorkspaceTab::Quality => render_list_block(
            f,
            area,
            "Results / Quality Gates",
            app.state
                .protocol_quality
                .as_ref()
                .map(|quality| {
                    quality
                        .gates
                        .iter()
                        .map(|gate| format!("{} [{}]", gate.name, gate.status))
                        .collect()
                })
                .unwrap_or_else(|| vec!["No quality summary.".to_string()]),
        ),
        ProtocolWorkspaceTab::Policy => render_list_block(
            f,
            area,
            "Results / Policy",
            app.state
                .protocol_policy_findings
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
        ProtocolWorkspaceTab::Clarify => render_list_block(
            f,
            area,
            "Results / Clarifications",
            app.state
                .protocol_clarifications
                .iter()
                .take(12)
                .map(|clarification| {
                    format!("{} [{}]", clarification.question, clarification.status)
                })
                .collect(),
        ),
        ProtocolWorkspaceTab::Spec => {
            render_paragraph_block(f, area, "Results / Spec", protocol_spec_lines(app))
        }
        ProtocolWorkspaceTab::Artifacts => render_list_block(
            f,
            area,
            "Results / Artifacts",
            app.state
                .protocol_artifacts
                .iter()
                .take(12)
                .map(|artifact| {
                    format!(
                        "{} · {} · step {}",
                        artifact.artifact.name, artifact.artifact.r#type, artifact.step_run_id
                    )
                })
                .collect(),
        ),
        ProtocolWorkspaceTab::Feedback => render_list_block(
            f,
            area,
            "Results / Feedback",
            app.state
                .protocol_feedback
                .iter()
                .take(12)
                .map(|event| format!("{} [{}]", event.action_taken, super::yes_no(event.resolved)))
                .collect(),
        ),
    }
}

fn protocol_workspace_tabs_line(active: ProtocolWorkspaceTab) -> Line<'static> {
    let tabs = [
        ProtocolWorkspaceTab::Summary,
        ProtocolWorkspaceTab::Steps,
        ProtocolWorkspaceTab::Runs,
        ProtocolWorkspaceTab::Events,
        ProtocolWorkspaceTab::Quality,
        ProtocolWorkspaceTab::Policy,
        ProtocolWorkspaceTab::Clarify,
        ProtocolWorkspaceTab::Spec,
        ProtocolWorkspaceTab::Artifacts,
        ProtocolWorkspaceTab::Feedback,
    ];
    tabs_line(
        tabs.iter()
            .map(|tab| (tab.label(), *tab == active))
            .collect(),
    )
}

fn latest_protocol_run_id(app: &App) -> String {
    app.state
        .protocol_runs
        .first()
        .map(|run| run.run_id.clone())
        .unwrap_or_else(|| "-".to_string())
}

fn latest_event_type(app: &App) -> String {
    app.state
        .events
        .last()
        .map(|event| event.event_type.clone())
        .unwrap_or_else(|| "-".to_string())
}

fn selected_step_label(app: &App) -> String {
    app.state
        .step_index
        .and_then(|idx| app.state.steps.get(idx))
        .map(|step| format!("{} · {}", step.id, step.step_name))
        .unwrap_or_else(|| "-".to_string())
}

fn protocol_quality_summary_lines(app: &App) -> Vec<Line<'static>> {
    let Some(quality) = &app.state.protocol_quality else {
        return vec![Line::from("No quality summary.")];
    };
    vec![
        Line::from(format!("overall: {}", quality.overall_status)),
        Line::from(format!("score: {:.0}%", quality.score * 100.0)),
        Line::from(format!("blocking issues: {}", quality.blocking_issues)),
        Line::from(format!("warnings: {}", quality.warnings)),
    ]
}

fn protocol_spec_lines(app: &App) -> Vec<Line<'static>> {
    let Some(spec) = &app.state.protocol_spec else {
        return vec![Line::from("No spec metadata loaded.")];
    };
    let mut lines = vec![
        Line::from(format!(
            "spec run id: {}",
            spec.spec_run_id
                .map(|id| id.to_string())
                .unwrap_or_else(|| "-".to_string())
        )),
        Line::from(format!(
            "spec hash: {}",
            spec.spec_hash.clone().unwrap_or_else(|| "-".to_string())
        )),
        Line::from(format!(
            "validation: {}",
            spec.validation_status
                .clone()
                .unwrap_or_else(|| "-".to_string())
        )),
    ];
    lines.extend(super::pretty_json_lines(&spec.spec));
    lines
}
