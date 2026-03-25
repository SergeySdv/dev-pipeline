import type { ReactNode } from "react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api/client";
import { useCreateProject } from "@/lib/api/hooks/use-projects";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }

  return { Wrapper };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("project create boundary", () => {
  it("disables automatic retries for project creation", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      id: 11,
      name: "telegram-bot",
      git_url: "https://github.com/example/telegram-bot.git",
      local_path: null,
      github_token_configured: false,
      base_branch: "main",
      project_classification: null,
      created_at: "2026-03-25T00:00:00Z",
      updated_at: "2026-03-25T00:00:00Z",
      policy_pack_key: null,
      policy_pack_version: null,
      policy_overrides: null,
      policy_repo_local_enabled: null,
      policy_effective_hash: null,
      policy_enforcement_mode: null,
      status: "active",
      constitution_version: null,
    });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useCreateProject(), { wrapper: Wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        name: "telegram-bot",
        git_url: "https://github.com/example/telegram-bot.git",
      });
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/projects",
      {
        name: "telegram-bot",
        git_url: "https://github.com/example/telegram-bot.git",
      },
      { skipRetry: true }
    );
  });
});
