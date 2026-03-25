import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SettingsTab } from "@/app/projects/[id]/components/settings-tab";

const projectData = {
  id: 4,
  name: "telegram-bot-browser-test",
  git_url: "https://github.com/SergeySdv/telegram-bot.git",
  local_path: "/Users/sergei/DevGodzillaProjects/4/telegram-bot",
  repo_mode: "external_repo" as const,
  task_cycle_autonomous: false,
  managed_repo_root_override: "/Users/sergei/PycharmProjects/telegram-bot",
  worktrees_root_override: "/Users/sergei/PycharmProjects/telegram-bot/worktrees",
  artifacts_root_override: "/Users/sergei/PycharmProjects/telegram-bot/worktrees",
  effective_repo_path: "/Users/sergei/DevGodzillaProjects/4/telegram-bot",
  effective_worktrees_root: "/Users/sergei/PycharmProjects/telegram-bot/worktrees",
  effective_artifacts_root: "/Users/sergei/PycharmProjects/telegram-bot/worktrees",
  github_token_configured: true,
  base_branch: "main",
  project_classification: null,
  created_at: "2026-03-25T00:00:00Z",
  updated_at: "2026-03-25T00:00:00Z",
  policy_pack_key: "default",
  policy_pack_version: "1.0",
  policy_overrides: null,
  policy_repo_local_enabled: null,
  policy_effective_hash: null,
  policy_enforcement_mode: "warn" as const,
  status: null,
  constitution_version: "1.0",
};

const assignmentsData = { assignments: {} };

vi.mock("@/lib/api", () => ({
  useProject: () => ({
    data: projectData,
    isLoading: false,
  }),
  useAgents: () => ({
    data: [],
  }),
  useAgentAssignments: () => ({
    data: assignmentsData,
  }),
  useUpdateProject: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdateAgentAssignments: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

describe("SettingsTab storage preview", () => {
  it("updates the effective repo path preview when the server repo path changes", () => {
    render(<SettingsTab projectId={4} />);

    expect(screen.getByText("/Users/sergei/DevGodzillaProjects/4/telegram-bot")).toBeTruthy();

    fireEvent.change(screen.getByLabelText(/server repository path/i), {
      target: { value: "/Users/sergei/PycharmProjects/telegram-bot" },
    });

    expect(screen.getByText("/Users/sergei/PycharmProjects/telegram-bot")).toBeTruthy();
  });
});
