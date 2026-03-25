import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { OverviewTab } from "@/app/projects/[id]/components/overview-tab";

const createProtocolMutateAsyncMock = vi.fn();

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
  useCreateProtocol: () => ({
    mutateAsync: createProtocolMutateAsyncMock,
    isPending: false,
  }),
}));

describe("OverviewTab protocol quick-create", () => {
  beforeEach(() => {
    createProtocolMutateAsyncMock.mockReset();
    createProtocolMutateAsyncMock.mockResolvedValue({ id: 42 });
  });

  it("submits canonical template fields from the overview dialog", async () => {
    render(<OverviewTab projectId={12} />);

    fireEvent.click(screen.getByRole("button", { name: /create protocol/i }));

    fireEvent.change(await screen.findByLabelText(/protocol name/i), {
      target: { value: "auth-flow" },
    });
    fireEvent.change(screen.getByLabelText(/^description$/i), {
      target: { value: "Implement authentication" },
    });
    fireEvent.change(screen.getByLabelText(/template source/i), {
      target: { value: "./templates/auth.yaml" },
    });
    fireEvent.change(screen.getByLabelText(/template config/i), {
      target: { value: '{ "mode": "guided" }' },
    });

    fireEvent.click(screen.getAllByRole("button", { name: /create protocol/i }).at(-1)!);

    await waitFor(() => {
      expect(createProtocolMutateAsyncMock).toHaveBeenCalledWith({
        projectId: 12,
        data: {
          protocol_name: "auth-flow",
          description: "Implement authentication",
          template_source: "./templates/auth.yaml",
          template_config: {
            mode: "guided",
          },
        },
      });
    });
  });
});
