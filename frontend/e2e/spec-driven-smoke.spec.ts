import { expect, test, type Page, type Route } from "@playwright/test";

const PROJECT_ID = 9;
const SPEC_RUN_ID = 77;
const APP_BASE_PATH = "/console";
const SPEC_PATH = "specs/001-auth-flow/spec.md";
const PLAN_PATH = "specs/001-auth-flow/plan.md";
const TASKS_PATH = "specs/001-auth-flow/tasks.md";
const IMPLEMENT_PATH = "specs/001-auth-flow/_runtime";
const IMPLEMENT_METADATA_PATH = "specs/001-auth-flow/_runtime/implement-bootstrap.json";

interface MockSpec {
  id: number;
  name: string;
  path: string;
  spec_path: string | null;
  plan_path: string | null;
  tasks_path: string | null;
  checklist_path: string | null;
  analysis_path: string | null;
  implement_path: string | null;
  has_spec: boolean;
  has_plan: boolean;
  has_tasks: boolean;
  status: string;
  spec_run_id: number;
  worktree_path: string;
  branch_name: string;
  base_branch: string;
  spec_number: number;
  feature_name: string;
}

interface MockState {
  initialized: boolean;
  specs: MockSpec[];
  requests: {
    init: Array<Record<string, unknown>>;
    specify: Array<Record<string, unknown>>;
    plan: Array<Record<string, unknown>>;
    tasks: Array<Record<string, unknown>>;
    implement: Array<Record<string, unknown>>;
  };
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

function buildProjectSpec(spec: MockSpec) {
  return {
    id: spec.id,
    spec_run_id: spec.spec_run_id,
    path: spec.path,
    spec_path: spec.spec_path,
    plan_path: spec.plan_path,
    tasks_path: spec.tasks_path,
    checklist_path: spec.checklist_path,
    analysis_path: spec.analysis_path,
    implement_path: spec.implement_path,
    title: spec.feature_name,
    project_id: PROJECT_ID,
    project_name: "Demo Project",
    status: spec.status,
    created_at: "2026-03-08T12:00:00Z",
    worktree_path: spec.worktree_path,
    branch_name: spec.branch_name,
    base_branch: spec.base_branch,
    feature_name: spec.feature_name,
    spec_number: spec.spec_number,
    tasks_generated: spec.has_tasks,
    has_plan: spec.has_plan,
    has_tasks: spec.has_tasks,
    protocol_id: spec.implement_path ? 42 : null,
    sprint_id: null,
    sprint_name: null,
    linked_tasks: spec.has_tasks ? 3 : 0,
    completed_tasks: 0,
    story_points: 0,
  };
}

function appPath(path: string) {
  return `${APP_BASE_PATH}${path}`;
}

async function installApiMocks(page: Page) {
  const state: MockState = {
    initialized: false,
    specs: [],
    requests: {
      init: [],
      specify: [],
      plan: [],
      tasks: [],
      implement: [],
    },
  };

  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const { pathname, searchParams } = url;
    const isApiRequest = !!request.headerValue("x-request-id");

    if (
      request.resourceType() === "document" ||
      !isApiRequest ||
      (!pathname.startsWith("/projects") &&
        !pathname.startsWith("/speckit") &&
        pathname !== "/specifications")
    ) {
      await route.continue();
      return;
    }

    if (request.method() === "GET" && pathname === `/projects/${PROJECT_ID}`) {
      await json(route, {
        id: PROJECT_ID,
        name: "Demo Project",
        git_url: "https://github.com/example/demo-project",
        local_path: "/tmp/demo-project",
        base_branch: "main",
        project_classification: null,
        created_at: "2026-03-08T12:00:00Z",
        updated_at: "2026-03-08T12:00:00Z",
        policy_pack_key: null,
        policy_pack_version: null,
        policy_overrides: null,
        policy_repo_local_enabled: true,
        policy_effective_hash: null,
        policy_enforcement_mode: null,
        status: "active",
        constitution_version: state.initialized ? "1" : null,
      });
      return;
    }

    if (request.method() === "GET" && pathname === `/projects/${PROJECT_ID}/onboarding`) {
      await json(route, {
        project_id: PROJECT_ID,
        status: "completed",
        stages: [],
        events: [],
        blocking_clarifications: 0,
      });
      return;
    }

    if (request.method() === "GET" && pathname === `/projects/${PROJECT_ID}/protocols`) {
      await json(route, []);
      return;
    }

    if (request.method() === "GET" && pathname === `/projects/${PROJECT_ID}/sprints`) {
      await json(route, []);
      return;
    }

    if (request.method() === "GET" && pathname === `/speckit/status/${PROJECT_ID}`) {
      await json(route, {
        initialized: state.initialized,
        constitution_hash: state.initialized ? "constitution-hash" : null,
        constitution_version: state.initialized ? "1" : null,
        spec_count: state.specs.length,
        specs: state.specs,
      });
      return;
    }

    if (request.method() === "GET" && pathname === `/speckit/specs/${PROJECT_ID}`) {
      await json(route, state.specs);
      return;
    }

    if (request.method() === "GET" && pathname === "/specifications" && searchParams.get("project_id") === String(PROJECT_ID)) {
      const specs = state.specs.map(buildProjectSpec);
      await json(route, {
        items: specs,
        total: specs.length,
        filters_applied: { project_id: PROJECT_ID },
      });
      return;
    }

    if (request.method() === "POST" && pathname === `/projects/${PROJECT_ID}/speckit/init`) {
      const body = requestBody(route);
      state.requests.init.push(body);
      state.initialized = true;
      await json(route, {
        success: true,
        path: "/tmp/demo-project/.specify",
        constitution_hash: "constitution-hash",
        error: null,
        warnings: [],
      });
      return;
    }

    if (request.method() === "POST" && pathname === `/projects/${PROJECT_ID}/speckit/specify`) {
      const body = requestBody(route);
      state.requests.specify.push(body);
      state.initialized = true;
      state.specs = [
        {
          id: 1,
          name: "001-auth-flow",
          path: "specs/001-auth-flow",
          spec_path: SPEC_PATH,
          plan_path: null,
          tasks_path: null,
          checklist_path: null,
          analysis_path: null,
          implement_path: null,
          has_spec: true,
          has_plan: false,
          has_tasks: false,
          status: "specified",
          spec_run_id: SPEC_RUN_ID,
          worktree_path: "/tmp/demo-project",
          branch_name: "spec/001-auth-flow",
          base_branch: "main",
          spec_number: 1,
          feature_name: "Auth Flow",
        },
      ];
      await json(route, {
        success: true,
        spec_path: SPEC_PATH,
        spec_number: 1,
        feature_name: "Auth Flow",
        spec_run_id: SPEC_RUN_ID,
        worktree_path: "/tmp/demo-project",
        branch_name: "spec/001-auth-flow",
        base_branch: "main",
        spec_root: "specs/001-auth-flow",
        error: null,
      });
      return;
    }

    if (request.method() === "POST" && pathname === `/projects/${PROJECT_ID}/speckit/plan`) {
      const body = requestBody(route);
      state.requests.plan.push(body);
      state.specs = state.specs.map((spec) => ({
        ...spec,
        plan_path: PLAN_PATH,
        has_plan: true,
        status: "planned",
      }));
      await json(route, {
        success: true,
        plan_path: PLAN_PATH,
        data_model_path: "specs/001-auth-flow/data-model.md",
        contracts_path: "specs/001-auth-flow/contracts",
        spec_run_id: SPEC_RUN_ID,
        worktree_path: "/tmp/demo-project",
        error: null,
      });
      return;
    }

    if (request.method() === "POST" && pathname === `/projects/${PROJECT_ID}/speckit/tasks`) {
      const body = requestBody(route);
      state.requests.tasks.push(body);
      state.specs = state.specs.map((spec) => ({
        ...spec,
        tasks_path: TASKS_PATH,
        has_tasks: true,
        status: "tasks",
      }));
      await json(route, {
        success: true,
        tasks_path: TASKS_PATH,
        task_count: 3,
        parallelizable_count: 1,
        spec_run_id: SPEC_RUN_ID,
        worktree_path: "/tmp/demo-project",
        error: null,
      });
      return;
    }

    if (request.method() === "POST" && pathname === `/projects/${PROJECT_ID}/speckit/implement`) {
      const body = requestBody(route);
      state.requests.implement.push(body);
      state.specs = state.specs.map((spec) => ({
        ...spec,
        implement_path: IMPLEMENT_PATH,
        status: "implemented",
      }));
      await json(route, {
        success: true,
        run_path: IMPLEMENT_PATH,
        metadata_path: IMPLEMENT_METADATA_PATH,
        protocol_id: 42,
        protocol_root: IMPLEMENT_PATH,
        step_count: 3,
        spec_run_id: SPEC_RUN_ID,
        worktree_path: "/tmp/demo-project",
        error: null,
      });
      return;
    }

    await json(route, {
      error: `Unhandled mock request for ${request.method()} ${pathname}`,
    }, 500);
  });

  return state;
}

test("drives the deterministic SpecKit happy path", async ({ page }) => {
  const state = await installApiMocks(page);

  await page.goto(appPath(`/projects/${PROJECT_ID}?tab=spec`));
  await expect(page.getByRole("button", { name: /initialize speckit/i })).toBeVisible();
  await page.getByRole("button", { name: /initialize speckit/i }).click();
  await expect.poll(() => state.requests.init.length).toBe(1);

  await page.goto(appPath(`/projects/${PROJECT_ID}?wizard=generate-specs&tab=spec`));
  await page.getByLabel(/feature name/i).fill("Auth Flow");
  await page.getByLabel(/^description/i).fill(
    "Build a deterministic authentication onboarding flow for the smoke test."
  );
  await page.getByRole("button", { name: /^Next$/ }).click();
  await page.getByLabel(/functional requirements/i).fill(
    "Users can sign in, sign out, and see an authenticated dashboard."
  );
  await page.getByLabel(/constraints/i).fill("Reuse existing auth tables and routes.");
  await page.getByRole("button", { name: /^Next$/ }).click();
  await page.getByRole("button", { name: /generate specification/i }).click();
  await expect.poll(() => state.requests.specify.length).toBe(1);
  await expect.poll(() => state.specs[0]?.spec_path).toBe(SPEC_PATH);
  await expect(page.getByText(/001-auth-flow/i).first()).toBeVisible();

  await page.goto(appPath(`/projects/${PROJECT_ID}?wizard=design-solution&tab=spec`));
  await page.getByRole("combobox").click();
  await page.getByRole("option", { name: /001-auth-flow/i }).click();
  await page
    .getByPlaceholder(/specific implementation preferences/i)
    .fill("Prefer existing auth tables and avoid schema changes.");
  await page.getByRole("button", { name: /generate implementation plan/i }).click();
  await expect.poll(() => state.requests.plan.length).toBe(1);
  await expect.poll(() => state.specs[0]?.plan_path).toBe(PLAN_PATH);

  await page.goto(appPath(`/projects/${PROJECT_ID}?wizard=implement-feature&tab=spec`));
  await page.getByRole("combobox").first().click();
  await page.getByRole("option", { name: /001-auth-flow/i }).click();
  await page.getByRole("button", { name: /generate tasks/i }).click();
  await expect.poll(() => state.requests.tasks.length).toBe(1);
  await expect.poll(() => state.specs[0]?.tasks_path).toBe(TASKS_PATH);

  await page.goto(appPath(`/projects/${PROJECT_ID}?tab=spec`));
  await page.getByRole("button", { name: /^Implement$/ }).first().click();
  await expect.poll(() => state.requests.implement.length).toBe(1);

  expect(state.requests.init[0]).toEqual({});
  expect(state.requests.specify[0]).toMatchObject({
    feature_name: "Auth Flow",
  });
  expect(state.requests.plan[0]).toMatchObject({
    spec_path: SPEC_PATH,
    context: "Prefer existing auth tables and avoid schema changes.",
  });
  expect(state.requests.tasks[0]).toMatchObject({
    plan_path: PLAN_PATH,
  });
  expect(state.requests.implement[0]).toMatchObject({
    spec_path: SPEC_PATH,
  });
});
