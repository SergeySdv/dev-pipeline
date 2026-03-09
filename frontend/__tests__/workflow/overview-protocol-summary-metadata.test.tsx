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
    data: [
      {
        id: 42,
        project_id: 12,
        protocol_name: "Auth Flow",
        status: "running",
        base_branch: "main",
        worktree_path: null,
        windmill_flow_id: null,
        protocol_root: null,
        description: null,
        template_source: '{"kind":"builtin","name":"brownfield/default"}',
        template_config: {
          mode: "brownfield",
          owner: "protocol",
        },
        summary: null,
        speckit_metadata: null,
        spec_hash: null,
        spec_validation_status: null,
        spec_validated_at: null,
        policy_pack_key: null,
        policy_pack_version: null,
        policy_effective_hash: null,
        policy_effective_json: null,
        linked_sprint_id: null,
        created_at: "2026-03-09T12:00:00Z",
        updated_at: "2026-03-09T12:00:00Z",
      },
    ],
  }),
  useSpecKitStatus: () => ({
    data: {
      initialized: true,
      spec_count: 0,
      specs: [],
    },
  }),
  usePolicyFindings: () => ({ data: [] }),
  useProjectCommits: () => ({ data: [] }),
  useProjectPulls: () => ({ data: [] }),
  useClarifySpec: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useGenerateChecklist: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useAnalyzeSpec: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useRunImplement: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useCreateProtocol: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe("OverviewTab protocol summaries", () => {
  it("shows template provenance in recent protocol cards", () => {
    render(<OverviewTab projectId={12} />);

    expect(screen.getByText("Auth Flow")).toBeDefined();
    expect(screen.getByText("builtin: brownfield/default")).toBeDefined();
    expect(screen.getByText("Config: 2 fields")).toBeDefined();
  });
});
