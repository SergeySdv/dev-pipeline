import { expect, type Page, type Route,test } from "@playwright/test";

const PROJECT_ID = 4;
const PROTOCOL_RUN_ID = 19;
const WORK_ITEM_ID = 55;
const APP_BASE_PATH = "/console";

interface MockArtifactRefs {
  task_dir: string;
  context_pack_json: string;
  context_pack_md: string;
  plan_pack_json: string;
  plan_pack_md: string;
  review_report_json: string;
  review_report_md: string;
  test_report_json: string;
  test_report_md: string;
  pr_ready_report_json: string;
  pr_ready_report_md: string;
  rework_pack_json: string;
  step_artifacts_dir: string;
}

interface MockWorkItem {
  id: number;
  project_id: number;
  protocol_run_id: number;
  title: string;
  status: string;
  lifecycle_state: string;
  lifecycle_reason: string | null;
  context_status: string;
  plan_status: string;
  review_status: string;
  qa_status: string;
  refactor_status: string;
  owner_agent: string | null;
  helper_agents: string[];
  task_dir: string;
  artifact_refs: MockArtifactRefs;
  depends_on: number[];
  pr_ready: boolean;
  blocking_clarifications: number;
  blocking_policy_findings: number;
  iteration_count: number;
  max_iterations: number;
  summary: string | null;
  active_stage: string | null;
  active_stage_label: string | null;
  active_stage_status: string | null;
  latest_completed_stage: string | null;
  latest_artifact_summary: string | null;
  blocking_reason: string | null;
  progress_summary: string | null;
}

interface MockRuntimeArtifact {
  id: string;
  key: string;
  stage_id: string;
  name: string;
  type: string;
  path: string;
  source: "work_item" | "step";
  exists: boolean;
  size: number;
  created_at: string | null;
  content_source: "work_item" | "step" | null;
  content_id: string | null;
}

interface MockRuntimeStage {
  stage_id: string;
  stage_name: string;
  order: number;
  status: string;
  mode?: string | null;
  summary?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  agent_assignments: Array<{
    agent_id: string;
    role: string;
    status: string;
  }>;
  artifacts: MockRuntimeArtifact[];
  blocking_reasons: string[];
  windmill_job_id?: string | null;
  windmill_module_id?: string | null;
  run_ids: string[];
}

interface MockRuntime {
  work_item: MockWorkItem;
  active_stage: string;
  active_stage_label: string;
  active_stage_status: string;
  latest_completed_stage: string | null;
  progress_summary: string | null;
  blocking_reasons: string[];
  active_agents: Array<{
    agent_id: string;
    role: string;
    status: string;
  }>;
  stage_runs: MockRuntimeStage[];
  latest_artifacts: MockRuntimeArtifact[];
  activity: Array<{
    id: string;
    kind: string;
    stage_id?: string | null;
    status?: string | null;
    message: string;
    created_at?: string | null;
    artifact_key?: string | null;
  }>;
  windmill: null;
}

interface MockState {
  workItem: MockWorkItem;
  runtime: MockRuntime;
  requests: {
    markPrReady: Array<Record<string, unknown>>;
  };
}

function appPath(path: string) {
  return `${APP_BASE_PATH}${path}`;
}

function requestBody(route: Route): Record<string, unknown> {
  const raw = route.request().postData();
  return raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function artifactRefs(): MockArtifactRefs {
  return {
    task_dir: "/tmp/task-cycle/work-item-55",
    context_pack_json: "/tmp/task-cycle/work-item-55/context_pack.json",
    context_pack_md: "/tmp/task-cycle/work-item-55/context_pack.md",
    plan_pack_json: "/tmp/task-cycle/work-item-55/plan_pack.json",
    plan_pack_md: "/tmp/task-cycle/work-item-55/plan_pack.md",
    review_report_json: "/tmp/task-cycle/work-item-55/review_report.json",
    review_report_md: "/tmp/task-cycle/work-item-55/review_report.md",
    test_report_json: "/tmp/task-cycle/work-item-55/test_report.json",
    test_report_md: "/tmp/task-cycle/work-item-55/test_report.md",
    pr_ready_report_json: "/tmp/task-cycle/work-item-55/pr_ready_report.json",
    pr_ready_report_md: "/tmp/task-cycle/work-item-55/pr_ready_report.md",
    rework_pack_json: "/tmp/task-cycle/work-item-55/rework_pack.json",
    step_artifacts_dir: "/tmp/task-cycle/work-item-55/artifacts",
  };
}

function readyForPrWorkItem(): MockWorkItem {
  return {
    id: WORK_ITEM_ID,
    project_id: PROJECT_ID,
    protocol_run_id: PROTOCOL_RUN_ID,
    title: "step-01-023-db-for-user-metadata",
    status: "ready_for_pr",
    lifecycle_state: "active",
    lifecycle_reason: null,
    context_status: "ready",
    plan_status: "ready",
    review_status: "passed",
    qa_status: "passed",
    refactor_status: "not_needed",
    owner_agent: "opencode",
    helper_agents: [],
    task_dir: "/tmp/task-cycle/work-item-55",
    artifact_refs: artifactRefs(),
    depends_on: [],
    pr_ready: false,
    blocking_clarifications: 0,
    blocking_policy_findings: 0,
    iteration_count: 2,
    max_iterations: 5,
    summary: "Persist telegram user metadata in the brownfield database layer",
    active_stage: "pr_ready",
    active_stage_label: "PR Ready",
    active_stage_status: "pending",
    latest_completed_stage: "QA",
    latest_artifact_summary: "QA: test_report.md",
    blocking_reason: null,
    progress_summary: "QA passed; PR readiness checks are available",
  };
}

function reworkWorkItem(): MockWorkItem {
  return {
    ...readyForPrWorkItem(),
    status: "needs_rework",
    pr_ready: false,
    active_stage: "implement",
    active_stage_label: "Implement",
    active_stage_status: "pending",
    latest_completed_stage: "QA",
    blocking_reason: "PR-ready validation failed; rework required",
    progress_summary: "Pre-commit failed; reuse the rework pack and rerun implementation",
    latest_artifact_summary: "PR Ready: pr_ready_report.md",
  };
}

function buildRuntime(workItem: MockWorkItem): MockRuntime {
  const prReadyArtifacts: MockRuntimeArtifact[] = [
    {
      id: "pr_ready_report_md",
      key: "pr_ready_report_md",
      stage_id: "pr_ready",
      name: "pr_ready_report.md",
      type: "text",
      path: workItem.artifact_refs.pr_ready_report_md,
      source: "work_item",
      exists: true,
      size: 214,
      created_at: "2026-03-22T12:00:00Z",
      content_source: "work_item",
      content_id: "pr_ready_report_md",
    },
    {
      id: "pr_ready_report_json",
      key: "pr_ready_report_json",
      stage_id: "pr_ready",
      name: "pr_ready_report.json",
      type: "json",
      path: workItem.artifact_refs.pr_ready_report_json,
      source: "work_item",
      exists: true,
      size: 312,
      created_at: "2026-03-22T12:00:00Z",
      content_source: "work_item",
      content_id: "pr_ready_report_json",
    },
  ];

  return {
    work_item: workItem,
    active_stage: workItem.active_stage ?? "implement",
    active_stage_label: workItem.active_stage_label ?? "Implement",
    active_stage_status: workItem.active_stage_status ?? "pending",
    latest_completed_stage: workItem.latest_completed_stage,
    progress_summary: workItem.progress_summary,
    blocking_reasons: workItem.blocking_reason ? [workItem.blocking_reason] : [],
    active_agents: [
      {
        agent_id: "opencode",
        role: "owner",
        status: "pending",
      },
    ],
    stage_runs: [
      {
        stage_id: "build_context",
        stage_name: "Build Context",
        order: 1,
        status: "completed",
        summary: "Context ready",
        started_at: "2026-03-22T10:00:00Z",
        finished_at: "2026-03-22T10:02:00Z",
        agent_assignments: [],
        artifacts: [],
        blocking_reasons: [],
        run_ids: [],
      },
      {
        stage_id: "plan",
        stage_name: "Plan",
        order: 2,
        status: "completed",
        summary: "Plan generated",
        started_at: "2026-03-22T10:03:00Z",
        finished_at: "2026-03-22T10:04:00Z",
        agent_assignments: [],
        artifacts: [],
        blocking_reasons: [],
        run_ids: [],
      },
      {
        stage_id: "review",
        stage_name: "Review",
        order: 3,
        status: "completed",
        summary: "Review passed",
        started_at: "2026-03-22T10:05:00Z",
        finished_at: "2026-03-22T10:06:00Z",
        agent_assignments: [],
        artifacts: [],
        blocking_reasons: [],
        run_ids: [],
      },
      {
        stage_id: "qa",
        stage_name: "QA",
        order: 4,
        status: "completed",
        summary: "Deterministic QA passed",
        started_at: "2026-03-22T10:07:00Z",
        finished_at: "2026-03-22T10:08:00Z",
        agent_assignments: [],
        artifacts: [],
        blocking_reasons: [],
        run_ids: [],
      },
      {
        stage_id: "pr_ready",
        stage_name: "PR Ready",
        order: 5,
        status: "failed",
        summary: "pre-commit validation failed before PR creation",
        started_at: "2026-03-22T12:00:00Z",
        finished_at: "2026-03-22T12:00:30Z",
        agent_assignments: [
          {
            agent_id: "opencode",
            role: "owner",
            status: "failed",
          },
        ],
        artifacts: prReadyArtifacts,
        blocking_reasons: ["PR-ready validation failed; rework required"],
        run_ids: [],
      },
    ],
    latest_artifacts: prReadyArtifacts,
    activity: [
      {
        id: "activity-pr-ready-failure",
        kind: "blocker",
        stage_id: "pr_ready",
        status: "failed",
        message: "pre-commit failed; work item returned to rework",
        created_at: "2026-03-22T12:00:30Z",
        artifact_key: "pr_ready_report_md",
      },
    ],
    windmill: null,
  };
}

async function installApiMocks(page: Page) {
  const state: MockState = {
    workItem: readyForPrWorkItem(),
    runtime: buildRuntime(reworkWorkItem()),
    requests: {
      markPrReady: [],
    },
  };

  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const { pathname } = url;
    const isApiRequest = !!request.headerValue("x-request-id");

    if (request.resourceType() === "document" || !isApiRequest) {
      await route.continue();
      return;
    }

    if (pathname.includes("/_next/")) {
      await route.continue();
      return;
    }

    if (request.method() === "GET" && pathname.endsWith(`/projects/${PROJECT_ID}`)) {
      await json(route, {
        id: PROJECT_ID,
        name: "Telegram Bot",
        git_url: "https://github.com/example/telegram-bot",
        local_path: "/tmp/telegram-bot",
        base_branch: "main",
        project_classification: null,
        created_at: "2026-03-21T12:00:00Z",
        updated_at: "2026-03-22T12:00:00Z",
        policy_pack_key: null,
        policy_pack_version: null,
        policy_overrides: null,
        policy_repo_local_enabled: true,
        policy_effective_hash: null,
        policy_enforcement_mode: null,
        status: "active",
        constitution_version: "1",
      });
      return;
    }

    if (request.method() === "GET" && pathname.endsWith(`/projects/${PROJECT_ID}/onboarding`)) {
      await json(route, {
        project_id: PROJECT_ID,
        status: "completed",
        stages: [],
        events: [],
        blocking_clarifications: 0,
      });
      return;
    }

    if (request.method() === "GET" && pathname.endsWith(`/projects/${PROJECT_ID}/protocols`)) {
      await json(route, [
        {
          id: PROTOCOL_RUN_ID,
          project_id: PROJECT_ID,
          protocol_name: "023-db-for-user-metadata",
          status: "running",
          base_branch: "main",
          worktree_path: "/tmp/telegram-bot",
          protocol_root: "/tmp/telegram-bot/specs/023-db-for-user-metadata/_runtime",
          description: "Brownfield user metadata flow",
          template_config: null,
          template_source: null,
          summary: null,
          windmill_flow_id: null,
          speckit_metadata: null,
          policy_pack_key: null,
          policy_pack_version: null,
          policy_effective_hash: null,
          policy_effective_json: null,
          linked_sprint_id: null,
          created_at: "2026-03-22T10:00:00Z",
          updated_at: "2026-03-22T12:00:00Z",
        },
      ]);
      return;
    }

    if (request.method() === "GET" && pathname.endsWith(`/projects/${PROJECT_ID}/task-cycle`)) {
      await json(route, [state.workItem]);
      return;
    }

    if (request.method() === "GET" && pathname.endsWith("/agents")) {
      await json(route, [
        {
          id: "opencode",
          name: "OpenCode",
          enabled: true,
        },
      ]);
      return;
    }

    if (
      request.method() === "POST" &&
      pathname.endsWith(`/work-items/${WORK_ITEM_ID}/actions/mark-pr-ready`)
    ) {
      state.requests.markPrReady.push(requestBody(route));
      state.workItem = reworkWorkItem();
      state.runtime = buildRuntime(state.workItem);
      await json(route, state.workItem);
      return;
    }

    if (request.method() === "GET" && pathname.endsWith(`/work-items/${WORK_ITEM_ID}/runtime`)) {
      await json(route, state.runtime);
      return;
    }

    if (
      request.method() === "GET" &&
      pathname.endsWith(`/work-items/${WORK_ITEM_ID}/artifacts/pr_ready_report_md/content`)
    ) {
      await json(route, {
        id: "pr_ready_report_md",
        name: "pr_ready_report.md",
        type: "text",
        truncated: false,
        content: [
          "# PR Ready Report",
          "",
          "Status: failed",
          "",
          "Pre-commit validation failed; rework is required before PR creation.",
          "",
          "Findings:",
          "- ruff.....................................................................Failed",
          "- README.md:1 unused import",
        ].join("\n"),
      });
      return;
    }

    if (
      request.method() === "GET" &&
      pathname.endsWith(`/work-items/${WORK_ITEM_ID}/artifacts/pr_ready_report_json/content`)
    ) {
      await json(route, {
        id: "pr_ready_report_json",
        name: "pr_ready_report.json",
        type: "json",
        truncated: false,
        content: JSON.stringify(
          {
            precommit: {
              status: "failed",
              summary: "Pre-commit validation failed; rework is required before PR creation",
              findings: ["README.md:1 unused import"],
            },
            pull_request: {
              status: "skipped",
            },
          },
          null,
          2
        ),
      });
      return;
    }

    await json(
      route,
      {
        error: `Unhandled mock request for ${request.method()} ${pathname}`,
      },
      500
    );
  });

  return state;
}

test("returns a work item to rework when PR-ready pre-commit validation fails", async ({ page }) => {
  test.setTimeout(90_000);
  const state = await installApiMocks(page);

  await page.goto(appPath(`/projects/${PROJECT_ID}?tab=task_cycle`));

  await expect(page.getByRole("heading", { name: "Task Cycle" })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText("step-01-023-db-for-user-metadata")).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByRole("button", { name: /mark pr ready/i })).toBeEnabled();

  await page.getByRole("button", { name: /mark pr ready/i }).click();

  await expect.poll(() => state.requests.markPrReady.length).toBe(1);
  await expect(
    page.locator("#main-content").getByText("PR-ready validation failed; rework required")
  ).toBeVisible();
  await expect(page.getByText("needs_rework")).toBeVisible();
  await expect(
    page.getByText("Pre-commit failed; reuse the rework pack and rerun implementation")
  ).toBeVisible();

  await page.getByRole("button", { name: /^Runtime$/ }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Blocking Conditions")).toBeVisible();
  await expect(
    page.getByRole("dialog").getByText("PR-ready validation failed; rework required").last()
  ).toBeVisible();

  await page.getByRole("tab", { name: /^Artifacts$/ }).click();
  await expect(page.getByText("Artifacts by Stage")).toBeVisible();
  await page.getByRole("button", { name: /pr_ready_report\.md/i }).click();
  await expect(page.getByText("pr_ready_report.md · task-cycle artifact")).toBeVisible();
  await expect(
    page.getByText("Pre-commit validation failed; rework is required before PR creation.")
  ).toBeVisible();
  await expect(page.getByText("README.md:1 unused import")).toBeVisible();
});
