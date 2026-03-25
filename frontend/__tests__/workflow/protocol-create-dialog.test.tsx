import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProtocolsTab } from "@/app/projects/[id]/components/protocols-tab";

const createProtocolMutateAsyncMock = vi.fn();

vi.mock("@/lib/api", () => ({
  useProjectProtocols: () => ({
    data: [],
    isLoading: false,
  }),
  useCreateProtocol: () => ({
    mutateAsync: createProtocolMutateAsyncMock,
    isPending: false,
  }),
}));

describe("ProtocolsTab create dialog", () => {
  beforeEach(() => {
    createProtocolMutateAsyncMock.mockReset();
    createProtocolMutateAsyncMock.mockResolvedValue({
      id: 42,
      project_id: 9,
      protocol_name: "auth-flow",
      status: "pending",
      base_branch: "main",
      worktree_path: null,
      windmill_flow_id: null,
      protocol_root: null,
      description: null,
      template_config: null,
      template_source: null,
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
    });
  });

  it("submits the canonical protocol create payload with parsed template config", async () => {
    render(<ProtocolsTab projectId={9} />);

    fireEvent.click(screen.getAllByRole("button", { name: /create protocol/i })[0]);

    fireEvent.change(await screen.findByLabelText(/protocol name/i), {
      target: { value: "auth-flow" },
    });
    fireEvent.change(screen.getByLabelText(/description/i), {
      target: { value: "Implement authentication flow" },
    });
    fireEvent.change(screen.getByLabelText(/base branch/i), {
      target: { value: "develop" },
    });
    fireEvent.change(screen.getByLabelText(/template source/i), {
      target: { value: "./templates/auth.yaml" },
    });
    fireEvent.change(screen.getByLabelText(/template config/i), {
      target: { value: '{ "mode": "brownfield", "owner": "protocol" }' },
    });

    fireEvent.click(screen.getAllByRole("button", { name: /create protocol/i }).at(-1)!);

    await waitFor(() => {
      expect(createProtocolMutateAsyncMock).toHaveBeenCalledWith({
        projectId: 9,
        data: {
          protocol_name: "auth-flow",
          description: "Implement authentication flow",
          base_branch: "develop",
          template_source: "./templates/auth.yaml",
          template_config: {
            mode: "brownfield",
            owner: "protocol",
          },
        },
      });
    });
  });
});
