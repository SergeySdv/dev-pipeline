use crate::app::App;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Style},
    text::Line,
    widgets::{Block, Borders, List, ListItem},
    Frame,
};

use super::{render_list_block, render_paragraph_block};

pub(super) fn draw_agents(f: &mut Frame<'_>, area: Rect, app: &App) {
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
    draw_agent_list(f, cols[0], app);
    draw_agents_chat(f, cols[1], app);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(56), Constraint::Percentage(44)].as_ref())
        .split(cols[2]);
    draw_agents_inspector(f, right[0], app);
    draw_agents_results(f, right[1], app);
}

fn draw_agent_list(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .state
        .agents
        .iter()
        .map(|agent| ListItem::new(format!("{} [{}]", agent.id, agent.status)))
        .collect();
    let mut list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title("Agents"))
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    if let Some(idx) = app.state.agent_index {
        list = list.highlight_symbol("➤ ");
        f.render_stateful_widget(list, area, &mut super::make_state(idx));
    } else {
        f.render_widget(list, area);
    }
}

fn draw_agents_chat(f: &mut Frame<'_>, area: Rect, app: &App) {
    let lines = if let Some(agent) = &app.state.agent_detail {
        vec![
            Line::from(format!("You> /agent show {}", agent.id)),
            Line::from(""),
            Line::from(format!(
                "Agent> Agent {} loaded. kind={} model={}",
                agent.id,
                agent.kind,
                agent.default_model.as_deref().unwrap_or("-")
            )),
            Line::from("[tool ] fetched health, metrics, assignments, and prompts"),
            Line::from(""),
            Line::from("Press c to edit the selected agent config."),
        ]
    } else {
        vec![Line::from(
            "Select an agent to inspect configuration and health.",
        )]
    };
    render_paragraph_block(f, area, "Chat / Transcript", lines);
}

fn draw_agents_inspector(f: &mut Frame<'_>, area: Rect, app: &App) {
    let lines = if let Some(agent) = &app.state.agent_detail {
        let health = app
            .state
            .agent_health
            .iter()
            .find(|health| health.agent_id == agent.id);
        let metrics = app
            .state
            .agent_metrics
            .iter()
            .find(|metrics| metrics.agent_id == agent.id);
        let test_result = app
            .state
            .agent_test_result
            .as_ref()
            .filter(|result| result.agent_id == agent.id);
        vec![
            Line::from(format!("name: {}", agent.name)),
            Line::from(format!("kind: {}", agent.kind)),
            Line::from(format!(
                "health: {}",
                health
                    .map(|health| if health.available {
                        "healthy"
                    } else {
                        "unavailable"
                    })
                    .unwrap_or("-")
            )),
            Line::from(format!(
                "total steps: {}",
                metrics.map(|metrics| metrics.total_steps).unwrap_or(0)
            )),
            Line::from(format!(
                "last test: {}",
                test_result
                    .map(|result| if result.ok { "passed" } else { "failed" })
                    .unwrap_or("-")
            )),
            Line::from(format!("capabilities: {}", agent.capabilities.join(", "))),
            Line::from(format!(
                "model: {}",
                agent.default_model.as_deref().unwrap_or("-")
            )),
            Line::from(format!(
                "reasoning: {}",
                agent.reasoning_effort.as_deref().unwrap_or("-")
            )),
            Line::from(format!(
                "timeout: {}s",
                agent
                    .timeout_seconds
                    .map(|value| value.to_string())
                    .unwrap_or_else(|| "-".into())
            )),
        ]
    } else {
        vec![Line::from("No agent selected.")]
    };
    render_paragraph_block(f, area, "Agent Inspector", lines);
}

fn draw_agents_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(54), Constraint::Percentage(46)].as_ref())
        .split(area);
    let assignment_lines = app
        .state
        .agent_assignments
        .as_ref()
        .map(|assignments| {
            assignments
                .assignments
                .iter()
                .map(|(process, assignment)| {
                    format!(
                        "{} -> {}",
                        process,
                        assignment
                            .agent_id
                            .clone()
                            .unwrap_or_else(|| "-".to_string())
                    )
                })
                .collect()
        })
        .unwrap_or_else(|| vec!["No assignments.".to_string()]);
    render_list_block(f, chunks[0], "Results / Assignments", assignment_lines);
    render_list_block(
        f,
        chunks[1],
        "Results / Prompts",
        app.state
            .agent_prompts
            .iter()
            .take(12)
            .map(|prompt| {
                format!(
                    "{} [{}]",
                    prompt.name,
                    prompt.source.as_deref().unwrap_or("-")
                )
            })
            .collect(),
    );
}
