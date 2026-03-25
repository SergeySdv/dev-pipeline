import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProtocolsTab } from "@/app/projects/[id]/components/protocols-tab";

vi.mock("@/lib/api", () => ({
  useProjectProtocols: () => ({
    data: [
      {
        id: 42,
        project_id: 9,
        protocol_name: "auth-flow",
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
    isLoading: false,
  }),
  useCreateProtocol: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

describe("ProtocolsTab template metadata", () => {
  it("shows canonical template provenance in the protocol list", () => {
    render(<ProtocolsTab projectId={9} />);

    expect(screen.getByText("Template Source")).toBeDefined();
    expect(screen.getByText("builtin: brownfield/default")).toBeDefined();
    expect(screen.getByText("Config")).toBeDefined();
    expect(screen.getByText("2 fields")).toBeDefined();
  });
});
