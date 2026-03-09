import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OverviewTab } from "@/app/projects/[id]/components/overview-tab";

vi.mock("@/lib/api", () => ({
  useProject: () => ({
    data: {
      id: 12,
      name: "Demo Project",
      local_path: "/tmp/demo-project",
      policy_pack_key: null,
    },
    isLoading: false,
  }),
  useOnboarding: () => ({
    data: {
      status: "completed",
      blocking_clarifications: 0,
    },
    isLoading: false,
  }),
  useProjectProtocols: () => ({
    data: [],
  }),
  useSpecKitStatus: () => ({
    data: {
      initialized: true,
      spec_count: 1,
      specs: [
        {
          name: "001-auth-flow",
          path: "specs/001-auth-flow",
          spec_path: "specs/001-auth-flow/spec.md",
          plan_path: null,
          tasks_path: null,
          checklist_path: null,
          analysis_path: null,
          implement_path: null,
          has_spec: true,
          has_plan: false,
          has_tasks: false,
          status: "draft",
        },
      ],
    },
  }),
  usePolicyFindings: () => ({
    data: [],
  }),
  useProjectCommits: () => ({
    data: [],
  }),
  useProjectPulls: () => ({
    data: [],
  }),
  useClarifySpec: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useGenerateChecklist: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useAnalyzeSpec: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useRunImplement: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useCreateProtocol: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

describe("OverviewTab workflow actions", () => {
  it("promotes the canonical workflow and labels manual step-by-step tools as secondary", () => {
    render(<OverviewTab projectId={12} />);

    expect(screen.getByRole("link", { name: /run spec workflow/i }).getAttribute("href")).toBe(
      "/projects/12?wizard=generate-specs&tab=spec"
    );
    expect(screen.getByRole("link", { name: /manual plan wizard/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /manual tasks wizard/i })).toBeTruthy();
  });
});
