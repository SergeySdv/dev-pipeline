import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SpecificationsPage from "@/app/specifications/page";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("@/lib/api", () => ({
  useSpecificationsWithMeta: () => ({
    data: {
      items: [
        {
          id: 77,
          spec_run_id: 77,
          path: "specs/001-auth-flow",
          spec_path: "specs/001-auth-flow/spec.md",
          plan_path: "specs/001-auth-flow/plan.md",
          tasks_path: "specs/001-auth-flow/tasks.md",
          checklist_path: "specs/001-auth-flow/checklist.md",
          analysis_path: "specs/001-auth-flow/analysis.md",
          implement_path: "specs/001-auth-flow/_runtime",
          title: "Auth Flow",
          project_id: 11,
          project_name: "Demo Project",
          status: "completed",
          created_at: "2026-03-08T12:00:00Z",
          worktree_path: "/tmp/demo-project",
          branch_name: "spec/001-auth-flow",
          base_branch: "main",
          feature_name: "Auth Flow",
          spec_number: 1,
          tasks_generated: true,
          has_plan: true,
          has_tasks: true,
          protocol_id: 42,
          sprint_id: 5,
          sprint_name: "Sprint 5",
          linked_tasks: 3,
          completed_tasks: 1,
          story_points: 8,
        },
      ],
      total: 1,
      filters_applied: {},
    },
    isLoading: false,
  }),
  useProjects: () => ({ data: [] }),
  useClarifySpec: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useGenerateChecklist: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useAnalyzeSpec: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useRunImplement: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useCreateProtocolFromSpec: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useCleanupSpecRun: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe("SpecificationsPage review entry links", () => {
  beforeEach(() => {
    pushMock.mockReset();
  });

  it("uses the review route as the primary specification entry point when review artifacts exist", () => {
    render(<SpecificationsPage />);

    expect(screen.getByRole("link", { name: /^review$/i }).getAttribute("href")).toBe(
      "/specifications/77?tab=analysis"
    );
    expect(screen.getByRole("link", { name: /^project$/i }).getAttribute("href")).toBe(
      "/projects/11?tab=spec"
    );
  });
});
