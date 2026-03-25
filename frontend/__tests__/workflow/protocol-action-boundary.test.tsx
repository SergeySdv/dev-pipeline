import type { ReactNode } from "react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api/client";
import { useProtocolAction } from "@/lib/api/hooks/use-protocols";
import { queryKeys } from "@/lib/api/query-keys";
import type { ProtocolRun } from "@/lib/api/types";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
  },
  ApiError: class ApiError extends Error {},
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }

  return {
    queryClient,
    Wrapper,
  };
}

const rawPausedProtocol = {
  id: 42,
  project_id: 7,
  protocol_name: "Brownfield Auth Flow",
  status: "paused",
  base_branch: "main",
  worktree_path: "/tmp/worktrees/auth",
  protocol_root: "/tmp/worktrees/auth/.devgodzilla/protocols/auth-flow",
  description: "Implement brownfield authentication flow",
  template_config: {
    mode: "brownfield",
  },
  template_source: {
    kind: "builtin",
    name: "brownfield/default",
  },
  summary: "Protocol summary",
  windmill_flow_id: "flow-123",
  speckit_metadata: {
    spec_run_id: 91,
    spec_hash: "abc123",
    validation_status: "validated",
    validated_at: "2026-03-09T10:00:00Z",
  },
  policy_pack_key: "repo/default",
  policy_pack_version: "1.0.0",
  policy_effective_hash: "policy-hash",
  policy_effective_json: {
    mode: "warn",
  },
  linked_sprint_id: 14,
  created_at: "2026-03-09T09:00:00Z",
  updated_at: "2026-03-09T10:00:00Z",
};

afterEach(() => {
  vi.clearAllMocks();
});

describe("protocol action boundary", () => {
  it("adapts protocol state actions and updates protocol caches", async () => {
    vi.mocked(apiClient.post).mockResolvedValue(rawPausedProtocol);
    const { queryClient, Wrapper } = createWrapper();

    const { result } = renderHook(() => useProtocolAction(), {
      wrapper: Wrapper,
    });

    let response:
      | Awaited<ReturnType<typeof result.current.mutateAsync>>
      | undefined;

    await act(async () => {
      response = await result.current.mutateAsync({
        protocolId: 42,
        action: "pause",
      });
    });

    const detailProtocol = queryClient.getQueryData(
      queryKeys.protocols.detail(42)
    ) as ProtocolRun | undefined;
    const listProtocols = queryClient.getQueryData(
      queryKeys.projects.protocols(7)
    ) as ProtocolRun[] | undefined;

    expect(response).toMatchObject({
      id: 42,
      status: "paused",
      linked_sprint_id: 14,
      spec_hash: "abc123",
      template_source: "{\"kind\":\"builtin\",\"name\":\"brownfield/default\"}",
    });
    expect(detailProtocol).toMatchObject({
      id: 42,
      status: "paused",
      linked_sprint_id: 14,
      spec_hash: "abc123",
    });
    expect(listProtocols).toEqual([
      expect.objectContaining({
        id: 42,
        status: "paused",
        linked_sprint_id: 14,
        spec_hash: "abc123",
      }),
    ]);
  });
});
