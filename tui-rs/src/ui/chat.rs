use crate::app::App;
use crate::state::ChatMessageKind;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame,
};

use super::{make_state, render_list_block, render_paragraph_block, short_hash};

pub(super) fn draw_chat(f: &mut Frame<'_>, area: Rect, app: &App) {
    let rows = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(10), Constraint::Length(3)].as_ref())
        .split(area);
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
        .split(rows[0]);

    draw_chat_navigator(f, cols[0], app);
    draw_chat_transcript(f, cols[1], app);

    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(56), Constraint::Percentage(44)].as_ref())
        .split(cols[2]);
    draw_chat_inspector(f, right[0], app);
    draw_chat_results(f, right[1], app);
    draw_chat_composer(f, rows[1], app);
}

fn draw_chat_navigator(f: &mut Frame<'_>, area: Rect, app: &App) {
    let rows = Layout::default()
        .direction(Direction::Vertical)
        .constraints(
            [
                Constraint::Percentage(44),
                Constraint::Percentage(30),
                Constraint::Percentage(26),
            ]
            .as_ref(),
        )
        .split(area);

    let project_items: Vec<ListItem> = app
        .state
        .projects
        .iter()
        .map(|project| {
            let branch = project.base_branch.clone().unwrap_or_else(|| "-".into());
            ListItem::new(format!("{} • {} ({branch})", project.id, project.name))
        })
        .collect();
    let mut project_list = List::new(project_items)
        .block(Block::default().borders(Borders::ALL).title("Project"))
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    if let Some(idx) = app.state.project_index {
        project_list = project_list.highlight_symbol("➤ ");
        f.render_stateful_widget(project_list, rows[0], &mut make_state(idx));
    } else {
        f.render_widget(project_list, rows[0]);
    }

    let agent_items: Vec<ListItem> = app
        .state
        .agents
        .iter()
        .map(|agent| {
            let status = if agent.enabled.unwrap_or(false) {
                "configured"
            } else {
                "disabled"
            };
            ListItem::new(format!("{} [{status}]", agent.id))
        })
        .collect();
    let mut agent_list = List::new(agent_items)
        .block(Block::default().borders(Borders::ALL).title("Agent"))
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    if let Some(idx) = app.state.agent_index {
        agent_list = agent_list.highlight_symbol("➤ ");
        f.render_stateful_widget(agent_list, rows[1], &mut make_state(idx));
    } else {
        f.render_widget(agent_list, rows[1]);
    }

    render_list_block(
        f,
        rows[2],
        "Saved Flows",
        vec![
            "brownfield_feature".into(),
            "protocol_execute".into(),
            "spec_generate".into(),
            "qa_repair".into(),
            "agent_test".into(),
        ],
    );
}

fn draw_chat_transcript(f: &mut Frame<'_>, area: Rect, app: &App) {
    let lines = if app.state.chat_messages.is_empty() {
        vec![Line::from(
            "Chat is ready. Type a message or command below.",
        )]
    } else {
        app.state
            .chat_messages
            .iter()
            .rev()
            .take(area.height.saturating_sub(2) as usize)
            .rev()
            .flat_map(message_lines)
            .collect::<Vec<_>>()
    };
    render_paragraph_block(f, area, "Chat / Transcript", lines);
}

fn message_lines(message: &crate::state::ChatMessage) -> Vec<Line<'static>> {
    let (prefix, color) = match message.kind.unwrap_or(ChatMessageKind::Agent) {
        ChatMessageKind::User => ("You>", Color::Cyan),
        ChatMessageKind::Agent => ("Agent>", Color::Yellow),
        ChatMessageKind::Flow => ("[flow ]", Color::Green),
        ChatMessageKind::Step => ("[step ]", Color::LightBlue),
        ChatMessageKind::Tool => ("[tool ]", Color::Magenta),
        ChatMessageKind::Check => ("[check]", Color::Green),
        ChatMessageKind::Warn => ("[warn ]", Color::Red),
    };

    let mut lines = Vec::new();
    for (idx, line) in message.text.lines().enumerate() {
        if idx == 0 {
            lines.push(Line::from(vec![
                Span::styled(
                    prefix.to_string(),
                    Style::default().fg(color).add_modifier(Modifier::BOLD),
                ),
                Span::raw(" "),
                Span::raw(line.to_string()),
            ]));
        } else {
            lines.push(Line::from(format!("       {line}")));
        }
    }
    if lines.is_empty() {
        lines.push(Line::from(prefix.to_string()));
    }
    lines
}

fn draw_chat_inspector(f: &mut Frame<'_>, area: Rect, app: &App) {
    let mut lines = Vec::new();
    if let Some(flow) = &app.state.active_flow {
        lines.push(Line::from(Span::styled(
            "Active Flow",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )));
        lines.push(Line::from(format!("kind: {}", flow.kind)));
        lines.push(Line::from(format!("label: {}", flow.label)));
        lines.push(Line::from(format!("status: {}", flow.status)));
        if let Some(protocol_id) = flow.protocol_id {
            lines.push(Line::from(format!("protocol: {protocol_id}")));
        }
        if let Some(step_id) = flow.step_id {
            lines.push(Line::from(format!("step: {step_id}")));
        }
        if let Some(run_id) = &flow.run_id {
            lines.push(Line::from(format!("run: {run_id}")));
        }
        if let Some(summary) = &flow.summary {
            lines.push(Line::from(format!("summary: {summary}")));
        }
        if let Some(artifact_hint) = &flow.artifact_hint {
            lines.push(Line::from(format!("artifact: {artifact_hint}")));
        }
        lines.push(Line::from(""));
    }

    if let Some(project) = app.state.selected_project() {
        lines.push(Line::from(Span::styled(
            "Context",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )));
        lines.push(Line::from(format!(
            "project: {} ({})",
            project.name, project.id
        )));
    }
    if let Some(protocol) = app.state.protocol_detail.as_ref().or_else(|| {
        app.state
            .protocol_index
            .and_then(|idx| app.state.protocols.get(idx))
    }) {
        lines.push(Line::from(format!(
            "protocol: {} [{}]",
            protocol.protocol_name,
            protocol.status.as_deref().unwrap_or("-")
        )));
    }
    if let Some(step) = app.state.step_detail.as_ref().or_else(|| {
        app.state
            .step_index
            .and_then(|idx| app.state.steps.get(idx))
    }) {
        lines.push(Line::from(format!(
            "step: {} [{}]",
            step.step_name, step.status
        )));
        if let Some(agent) = &step.assigned_agent {
            lines.push(Line::from(format!("assigned_agent: {agent}")));
        }
    }
    if let Some(agent) = app.state.agent_detail.as_ref().or_else(|| {
        app.state
            .agent_index
            .and_then(|idx| app.state.agents.get(idx))
    }) {
        lines.push(Line::from(format!("agent: {} ({})", agent.name, agent.id)));
        lines.push(Line::from(format!("kind: {}", agent.kind)));
        if let Some(model) = &agent.default_model {
            lines.push(Line::from(format!("model: {model}")));
        }
    }
    if lines.is_empty() {
        lines.push(Line::from("Select a project and agent to start."));
    }
    render_paragraph_block(f, area, "Active Flow", lines);
}

fn draw_chat_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let lines = if let Some(logs) = &app.state.run_logs {
        let mut lines = vec![Line::from(format!("run: {}", short_hash(&logs.id)))];
        lines.extend(
            logs.content
                .lines()
                .take(area.height.saturating_sub(3) as usize)
                .map(|line| Line::from(line.to_string())),
        );
        lines
    } else if !app.state.recent_events.is_empty() {
        app.state
            .recent_events
            .iter()
            .rev()
            .take(area.height.saturating_sub(2) as usize)
            .map(|event| Line::from(format!("{}: {}", event.event_type, event.message)))
            .collect()
    } else if let Some(flow) = &app.state.active_flow {
        let mut lines = Vec::new();
        if let Some(tool) = &flow.last_tool {
            lines.push(Line::from(tool.clone()));
        }
        if let Some(artifact_hint) = &flow.artifact_hint {
            lines.push(Line::from(format!("artifact: {artifact_hint}")));
        }
        if lines.is_empty() {
            vec![Line::from("No results yet.")]
        } else {
            lines
        }
    } else {
        vec![Line::from("No data.")]
    };
    render_paragraph_block(f, area, "Results / Logs", lines);
}

fn draw_chat_composer(f: &mut Frame<'_>, area: Rect, app: &App) {
    let value = if app.state.composer_input.is_empty() {
        "Type a message or /command..."
    } else {
        app.state.composer_input.as_str()
    };
    let style = if app.state.composer_input.is_empty() {
        Style::default().fg(Color::DarkGray)
    } else {
        Style::default().fg(Color::White)
    };
    let para = Paragraph::new(value)
        .style(style)
        .block(Block::default().borders(Borders::ALL).title("Composer"))
        .wrap(Wrap { trim: true });
    f.render_widget(para, area);
}
