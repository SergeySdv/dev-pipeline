import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BranchesTab } from "@/app/projects/[id]/components/branches-tab";

vi.mock("@/components/ui/data-table", () => ({
  DataTable: () => <div data-testid="branches-table" />,
}));

vi.mock("@/lib/api", () => ({
  useProjectBranches: () => ({ data: [], isLoading: false }),
  useProjectCommits: () => ({ data: [], isLoading: false }),
  useProjectPulls: () => ({ data: [], isLoading: false }),
  useProjectWorktrees: () => ({
    data: [
      {
        branch_name: "spec/001-auth-flow",
        worktree_path: "/tmp/demo-project/.worktrees/spec-001-auth-flow",
        protocol_run_id: 42,
        protocol_name: "Auth Flow Protocol",
        protocol_status: "running",
        spec_run_id: 77,
        last_commit_sha: "abcdef1234567890",
        last_commit_message: "Bootstrap auth flow implementation",
        last_commit_date: "2026-03-09T12:00:00Z",
        pr_url: null,
      },
    ],
    isLoading: false,
  }),
  useDeleteBranch: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useCreateBranch: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe("BranchesTab review links", () => {
  it("links worktree actions through the specification review entry point", () => {
    render(<BranchesTab projectId={11} />);

    expect(screen.getByRole("link", { name: /review implementation/i }).getAttribute("href")).toBe(
      "/specifications/77?tab=analysis"
    );
    expect(screen.getByRole("link", { name: /open protocol/i }).getAttribute("href")).toBe(
      "/protocols/42"
    );
  });
});
