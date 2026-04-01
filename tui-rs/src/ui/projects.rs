use crate::app::App;
use crate::state::ProjectWorkspaceTab;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame,
};

use super::{make_state, render_paragraph_block, short_hash, trunc_lines, yes_no};

pub(super) fn draw_projects(f: &mut Frame<'_>, area: Rect, app: &App) {
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
    draw_project_list(f, cols[0], app);
    draw_project_chat(f, cols[1], app);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(56), Constraint::Percentage(44)].as_ref())
        .split(cols[2]);
    draw_project_inspector(f, right[0], app);
    draw_project_results(f, right[1], app);
}

pub(super) fn draw_project_list(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .state
        .projects
        .iter()
        .map(|p| {
            let branch = p.base_branch.clone().unwrap_or_else(|| "-".into());
            ListItem::new(format!("{} • {} ({branch})", p.id, p.name))
        })
        .collect();
    let mut list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title("Projects"))
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    if let Some(idx) = app.state.project_index {
        list = list.highlight_symbol("➤ ");
        f.render_stateful_widget(list, area, &mut make_state(idx));
    } else {
        f.render_widget(list, area);
    }
}

fn draw_project_chat(f: &mut Frame<'_>, area: Rect, app: &App) {
    let project = app
        .state
        .project_detail
        .as_ref()
        .or_else(|| app.state.selected_project());
    let Some(project) = project else {
        let para = Paragraph::new("Select a project to open its workspace.")
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .title("Chat / Transcript"),
            )
            .wrap(Wrap { trim: true });
        f.render_widget(para, area);
        return;
    };

    let branch_count = app.state.branches.len();
    let open_clarifications = app.state.project_clarifications.len();
    let policy_findings = app.state.project_policy_findings.len();
    let protocols = app.state.protocols.len();
    let specs = app.state.project_specs.len();
    let pulls = app.state.project_pulls.len();
    let worktrees = app.state.project_worktrees.len();
    let status = project.status.as_deref().unwrap_or("unknown");
    let repo = project
        .git_url
        .as_deref()
        .or(project.effective_repo_path.as_deref())
        .unwrap_or("-");
    let next_action = match app.state.project_workspace_tab {
        ProjectWorkspaceTab::Summary => "Inspect specs, policy, or branches on the right.",
        ProjectWorkspaceTab::Specs => "Review the spec list and pick the next work item.",
        ProjectWorkspaceTab::Branches => "Check branches, PRs, and worktrees before cleanup.",
        ProjectWorkspaceTab::Clarifications => "Resolve blocking questions before continuing.",
        ProjectWorkspaceTab::Policy => "Review findings and decide whether to patch or override.",
        ProjectWorkspaceTab::Settings => "Confirm repo mode and storage paths before mutations.",
        ProjectWorkspaceTab::Onboarding => "Track onboarding progress and discovery output.",
    };

    let lines = vec![
        Line::from(format!("You> /project show {}", project.id)),
        Line::from(""),
        Line::from(format!("Agent> Project {} loaded.", project.name)),
        Line::from(format!(
            "       status={status}  protocols={protocols}  specs={specs}"
        )),
        Line::from(format!(
            "       branches={branch_count}  pulls={pulls}  worktrees={worktrees}"
        )),
        Line::from(format!(
            "       clarifications={open_clarifications}  policy_findings={policy_findings}"
        )),
        Line::from(format!("       repo={repo}")),
        Line::from(""),
        Line::from(
            "[tool ] fetched overview, specs, policy, clarifications, branches, and onboarding",
        ),
        Line::from(format!(
            "[hint ] active project tab: {}",
            app.state.project_workspace_tab.label()
        )),
        Line::from(""),
        Line::from(format!("Next actions: {next_action}")),
    ];

    let para = Paragraph::new(lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Chat / Transcript"),
        )
        .wrap(Wrap { trim: true });
    f.render_widget(para, area);
}

fn draw_project_inspector(f: &mut Frame<'_>, area: Rect, app: &App) {
    let project = app
        .state
        .project_detail
        .as_ref()
        .or_else(|| app.state.selected_project());
    let title = match project {
        Some(project) => format!("Project {} · {}", project.id, project.name),
        None => "Project".to_string(),
    };

    let mut lines = vec![
        project_workspace_tabs_line(app.state.project_workspace_tab),
        Line::from(""),
    ];
    lines.extend(match app.state.project_workspace_tab {
        ProjectWorkspaceTab::Summary => project_summary_lines(app),
        ProjectWorkspaceTab::Specs => project_specs_summary_lines(app),
        ProjectWorkspaceTab::Branches => project_branches_summary_lines(app),
        ProjectWorkspaceTab::Clarifications => project_clarifications_summary_lines(app),
        ProjectWorkspaceTab::Policy => project_policy_summary_lines(app),
        ProjectWorkspaceTab::Settings => project_settings_summary_lines(app),
        ProjectWorkspaceTab::Onboarding => project_onboarding_summary_lines(app),
    });

    let para = Paragraph::new(lines)
        .block(Block::default().borders(Borders::ALL).title(title))
        .wrap(Wrap { trim: true });
    f.render_widget(para, area);
}

fn draw_project_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    match app.state.project_workspace_tab {
        ProjectWorkspaceTab::Summary => draw_project_protocol_results(f, area, app),
        ProjectWorkspaceTab::Specs => draw_project_specs_results(f, area, app),
        ProjectWorkspaceTab::Branches => draw_project_branch_results(f, area, app),
        ProjectWorkspaceTab::Clarifications => draw_project_clarifications_results(f, area, app),
        ProjectWorkspaceTab::Policy => draw_project_policy_results(f, area, app),
        ProjectWorkspaceTab::Settings => draw_project_commit_results(f, area, app),
        ProjectWorkspaceTab::Onboarding => draw_project_onboarding_results(f, area, app),
    }
}

fn draw_project_protocol_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items: Vec<ListItem> = if app.state.protocols.is_empty() {
        vec![ListItem::new("No protocols for this project.")]
    } else {
        app.state
            .protocols
            .iter()
            .take(12)
            .map(|protocol| {
                let status = protocol.status.as_deref().unwrap_or("-");
                ListItem::new(format!(
                    "{} · {} [{status}]",
                    protocol.id, protocol.protocol_name
                ))
            })
            .collect()
    };
    let list = List::new(items).block(
        Block::default()
            .borders(Borders::ALL)
            .title("Results / Protocols"),
    );
    f.render_widget(list, area);
}

fn draw_project_specs_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(48), Constraint::Percentage(52)].as_ref())
        .split(area);
    let items: Vec<ListItem> = if app.state.project_specs.is_empty() {
        vec![ListItem::new("No specs found for this project.")]
    } else {
        app.state
            .project_specs
            .iter()
            .map(|spec| {
                let number = spec
                    .spec_number
                    .map(|n| format!("#{n}"))
                    .unwrap_or_else(|| "-".to_string());
                ListItem::new(format!(
                    "{number} {} [{}] plan={} tasks={}",
                    spec.title,
                    spec.status,
                    yes_no(spec.has_plan),
                    yes_no(spec.has_tasks)
                ))
            })
            .collect()
    };
    let mut list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Results / Specs"),
        )
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    if let Some(idx) = app.state.project_spec_index {
        list = list.highlight_symbol("➤ ");
        f.render_stateful_widget(list, chunks[0], &mut make_state(idx));
    } else {
        f.render_widget(list, chunks[0]);
    }
    let content_lines = app
        .state
        .project_spec_content
        .as_ref()
        .map(|content| {
            let source = content
                .spec_content
                .as_deref()
                .or(content.plan_content.as_deref())
                .or(content.tasks_content.as_deref())
                .or(content.checklist_content.as_deref())
                .or(content.analysis_content.as_deref())
                .unwrap_or("No spec content loaded.");
            trunc_lines(source, 14)
        })
        .unwrap_or_else(|| vec![Line::from("Select a spec and use Ctrl+j/k to inspect it.")]);
    render_paragraph_block(f, chunks[1], "Results / Selected Spec", content_lines);
}

fn draw_project_branch_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let mut items: Vec<ListItem> = vec![ListItem::new("Branches")];
    if app.state.branches.is_empty() {
        items.push(ListItem::new("No branches available."));
    } else {
        items.extend(app.state.branches.iter().map(|branch| {
            let scope = if branch.is_remote { "remote" } else { "local" };
            ListItem::new(format!(
                "{} [{scope}] {}",
                branch.name,
                short_hash(&branch.sha)
            ))
        }));
    }
    items.push(ListItem::new(""));
    items.push(ListItem::new("Pull Requests"));
    if app.state.project_pulls.is_empty() {
        items.push(ListItem::new("No open pull requests."));
    } else {
        items.extend(
            app.state
                .project_pulls
                .iter()
                .take(5)
                .map(|pr| ListItem::new(format!("#{} {} [{}]", pr.id, pr.title, pr.checks))),
        );
    }
    items.push(ListItem::new(""));
    items.push(ListItem::new("Worktrees"));
    if app.state.project_worktrees.is_empty() {
        items.push(ListItem::new("No active worktrees."));
    } else {
        items.extend(app.state.project_worktrees.iter().take(5).map(|worktree| {
            let status = worktree.protocol_status.as_deref().unwrap_or("-");
            ListItem::new(format!("{} [{status}]", worktree.branch_name))
        }));
    }

    let mut list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Results / Git"),
        )
        .highlight_style(Style::default().bg(Color::Blue).fg(Color::White));
    if let Some(idx) = app.state.branch_index {
        list = list.highlight_symbol("➤ ");
        f.render_stateful_widget(list, area, &mut make_state(idx + 1));
    } else {
        f.render_widget(list, area);
    }
}

fn draw_project_clarifications_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items: Vec<ListItem> = if app.state.project_clarifications.is_empty() {
        vec![ListItem::new("No open clarifications.")]
    } else {
        app.state
            .project_clarifications
            .iter()
            .take(12)
            .map(|clarification| {
                let key = clarification.key.as_deref().unwrap_or("-");
                let blocking = if clarification.blocking.unwrap_or(false) {
                    "blocking"
                } else {
                    "optional"
                };
                ListItem::new(format!("{key} [{}] {}", blocking, clarification.question))
            })
            .collect()
    };
    let list = List::new(items).block(
        Block::default()
            .borders(Borders::ALL)
            .title("Results / Clarifications"),
    );
    f.render_widget(list, area);
}

fn draw_project_policy_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items: Vec<ListItem> = if app.state.project_policy_findings.is_empty() {
        vec![ListItem::new("No policy findings.")]
    } else {
        app.state
            .project_policy_findings
            .iter()
            .take(12)
            .map(|finding| {
                let location = finding.location.as_deref().unwrap_or("-");
                ListItem::new(format!(
                    "{} [{}] {} ({location})",
                    finding.code, finding.severity, finding.message
                ))
            })
            .collect()
    };
    let list = List::new(items).block(
        Block::default()
            .borders(Borders::ALL)
            .title("Results / Policy"),
    );
    f.render_widget(list, area);
}

fn draw_project_commit_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let items: Vec<ListItem> = if app.state.project_commits.is_empty() {
        vec![ListItem::new("No commits available.")]
    } else {
        app.state
            .project_commits
            .iter()
            .take(12)
            .map(|commit| {
                ListItem::new(format!(
                    "{} {} · {}",
                    short_hash(&commit.sha),
                    commit.message,
                    commit.author
                ))
            })
            .collect()
    };
    let list = List::new(items).block(
        Block::default()
            .borders(Borders::ALL)
            .title("Results / Commits"),
    );
    f.render_widget(list, area);
}

fn draw_project_onboarding_results(f: &mut Frame<'_>, area: Rect, app: &App) {
    let mut items: Vec<ListItem> = vec![ListItem::new("Stages")];
    if let Some(onboarding) = &app.state.project_onboarding {
        if onboarding.stages.is_empty() {
            items.push(ListItem::new("No onboarding stages."));
        } else {
            items.extend(
                onboarding
                    .stages
                    .iter()
                    .map(|stage| ListItem::new(format!("{} [{}]", stage.name, stage.status))),
            );
        }
        items.push(ListItem::new(""));
        items.push(ListItem::new("Recent Events"));
        if onboarding.events.is_empty() {
            items.push(ListItem::new("No onboarding events."));
        } else {
            items.extend(
                onboarding
                    .events
                    .iter()
                    .take(6)
                    .map(|event| ListItem::new(format!("{} {}", event.event_type, event.message))),
            );
        }
    } else {
        items.push(ListItem::new("Onboarding data unavailable."));
    }
    let list = List::new(items).block(
        Block::default()
            .borders(Borders::ALL)
            .title("Results / Onboarding"),
    );
    f.render_widget(list, area);
}

fn project_workspace_tabs_line(active: ProjectWorkspaceTab) -> Line<'static> {
    let tabs = [
        ProjectWorkspaceTab::Summary,
        ProjectWorkspaceTab::Specs,
        ProjectWorkspaceTab::Branches,
        ProjectWorkspaceTab::Clarifications,
        ProjectWorkspaceTab::Policy,
        ProjectWorkspaceTab::Settings,
        ProjectWorkspaceTab::Onboarding,
    ];
    let mut spans = Vec::new();
    for (idx, tab) in tabs.into_iter().enumerate() {
        if idx > 0 {
            spans.push(Span::raw(" "));
        }
        let style = if tab == active {
            Style::default()
                .fg(Color::Black)
                .bg(Color::Yellow)
                .add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::Cyan)
        };
        spans.push(Span::styled(format!("[{}]", tab.label()), style));
    }
    Line::from(spans)
}

fn project_summary_lines(app: &App) -> Vec<Line<'static>> {
    let project = app
        .state
        .project_detail
        .as_ref()
        .or_else(|| app.state.selected_project());
    let Some(project) = project else {
        return vec![Line::from("No project selected.")];
    };
    vec![
        Line::from(format!(
            "status: {}",
            project.status.as_deref().unwrap_or("unknown")
        )),
        Line::from(format!(
            "base branch: {}",
            project.base_branch.as_deref().unwrap_or("main")
        )),
        Line::from(format!("protocols: {}", app.state.protocols.len())),
        Line::from(format!("specs: {}", app.state.project_specs.len())),
        Line::from(format!(
            "git: {}",
            project.git_url.as_deref().unwrap_or("-")
        )),
        Line::from(format!(
            "local path: {}",
            project.local_path.as_deref().unwrap_or("-")
        )),
    ]
}

fn project_specs_summary_lines(app: &App) -> Vec<Line<'static>> {
    let ready = app
        .state
        .project_specs
        .iter()
        .filter(|spec| spec.has_plan && spec.has_tasks)
        .count();
    let latest = app
        .state
        .project_specs
        .first()
        .map(|spec| spec.title.clone())
        .unwrap_or_else(|| "-".to_string());
    let selected = app
        .state
        .selected_project_spec()
        .map(|spec| format!("{} [{}]", spec.title, spec.status))
        .unwrap_or_else(|| "-".to_string());
    vec![
        Line::from(format!("spec count: {}", app.state.project_specs.len())),
        Line::from(format!("ready for implementation: {ready}")),
        Line::from(format!("latest spec: {latest}")),
        Line::from(format!("selected: {selected}")),
        Line::from("Enter opens the spec command palette. Ctrl+j/k selects spec."),
    ]
}

fn project_branches_summary_lines(app: &App) -> Vec<Line<'static>> {
    let local = app
        .state
        .branches
        .iter()
        .filter(|branch| !branch.is_remote)
        .count();
    let remote = app
        .state
        .branches
        .iter()
        .filter(|branch| branch.is_remote)
        .count();
    let selected = app
        .state
        .branch_index
        .and_then(|idx| app.state.branches.get(idx))
        .map(|branch| branch.name.clone())
        .unwrap_or_else(|| "-".to_string());
    vec![
        Line::from(format!("selected branch: {selected}")),
        Line::from(format!("local branches: {local}")),
        Line::from(format!("remote branches: {remote}")),
        Line::from(format!("open PRs: {}", app.state.project_pulls.len())),
        Line::from(format!("worktrees: {}", app.state.project_worktrees.len())),
    ]
}

fn project_clarifications_summary_lines(app: &App) -> Vec<Line<'static>> {
    let blocking = app
        .state
        .project_clarifications
        .iter()
        .filter(|clarification| clarification.blocking.unwrap_or(false))
        .count();
    vec![
        Line::from(format!(
            "open clarifications: {}",
            app.state.project_clarifications.len()
        )),
        Line::from(format!("blocking clarifications: {blocking}")),
        Line::from(
            "use project clarifications before protocol execution when discovery is incomplete",
        ),
    ]
}

fn project_policy_summary_lines(app: &App) -> Vec<Line<'static>> {
    let policy = app.state.project_policy.as_ref();
    let effective = app.state.project_effective_policy.as_ref();
    vec![
        Line::from(format!(
            "pack: {}",
            policy
                .and_then(|p| p.policy_pack_key.clone())
                .or_else(|| effective.map(|p| p.pack_key.clone()))
                .unwrap_or_else(|| "-".to_string())
        )),
        Line::from(format!(
            "version: {}",
            policy
                .and_then(|p| p.policy_pack_version.clone())
                .or_else(|| effective.map(|p| p.pack_version.clone()))
                .unwrap_or_else(|| "-".to_string())
        )),
        Line::from(format!(
            "enforcement: {}",
            policy
                .map(|p| p.policy_enforcement_mode.clone())
                .unwrap_or_else(|| "warn".to_string())
        )),
        Line::from(format!(
            "effective hash: {}",
            effective
                .map(|p| p.hash.clone())
                .unwrap_or_else(|| "-".to_string())
        )),
        Line::from(format!(
            "findings: {}",
            app.state.project_policy_findings.len()
        )),
    ]
}

fn project_settings_summary_lines(app: &App) -> Vec<Line<'static>> {
    let project = app
        .state
        .project_detail
        .as_ref()
        .or_else(|| app.state.selected_project());
    let Some(project) = project else {
        return vec![Line::from("No project selected.")];
    };
    vec![
        Line::from(format!(
            "repo mode: {}",
            project.repo_mode.as_deref().unwrap_or("-")
        )),
        Line::from(format!(
            "effective repo path: {}",
            project.effective_repo_path.as_deref().unwrap_or("-")
        )),
        Line::from(format!(
            "worktrees root: {}",
            project.effective_worktrees_root.as_deref().unwrap_or("-")
        )),
        Line::from(format!(
            "artifacts root: {}",
            project.effective_artifacts_root.as_deref().unwrap_or("-")
        )),
        Line::from(format!(
            "task cycle autonomous: {}",
            yes_no(project.task_cycle_autonomous)
        )),
        Line::from(format!(
            "github token configured: {}",
            yes_no(project.github_token_configured)
        )),
    ]
}

fn project_onboarding_summary_lines(app: &App) -> Vec<Line<'static>> {
    let Some(onboarding) = &app.state.project_onboarding else {
        return vec![Line::from("Onboarding data unavailable.")];
    };
    let completed = onboarding
        .stages
        .iter()
        .filter(|stage| stage.status == "completed")
        .count();
    let failed = onboarding
        .stages
        .iter()
        .filter(|stage| stage.status == "failed")
        .count();
    vec![
        Line::from(format!("status: {}", onboarding.status)),
        Line::from(format!("stages: {}", onboarding.stages.len())),
        Line::from(format!("completed: {completed}")),
        Line::from(format!("failed: {failed}")),
        Line::from(format!(
            "blocking clarifications: {}",
            onboarding.blocking_clarifications
        )),
    ]
}
