import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import RunDetailPage from "@/app/runs/[runId]/page";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({
    runId: "run-linked-task",
  }),
}));

vi.mock("@/lib/api", () => ({
  useRun: () => ({
    data: {
      run_id: "run-linked-task",
      job_type: "execute_step",
      run_kind: "exec",
      status: "running",
      project_id: 12,
      protocol_run_id: 42,
      spec_run_id: 77,
      step_run_id: 7,
      task_id: 99,
      task_title: "Implement linked run workflow",
      task_board_status: "review",
      sprint_id: 5,
      sprint_name: "Sprint 7",
      sprint_status: "active",
      attempt: 1,
      worker_id: null,
      queue: "default",
      prompt_version: null,
      params: null,
      result: null,
      error: null,
      log_path: null,
      cost_tokens: 10,
      cost_cents: 1,
      started_at: "2026-03-09T10:00:00Z",
      finished_at: null,
      created_at: "2026-03-09T09:59:00Z",
      updated_at: "2026-03-09T10:00:00Z",
    },
    isLoading: false,
    error: null,
  }),
  useRunLogs: () => ({
    data: null,
    isLoading: false,
  }),
  useRunArtifacts: () => ({
    data: [],
    isLoading: false,
  }),
}));

describe("Run detail agile context", () => {
  it("shows real task and sprint linkage when the backend provides it", () => {
    render(<RunDetailPage />);

    expect(screen.getByText(/task #99/i)).toBeTruthy();
    expect(screen.getByText(/implement linked run workflow/i)).toBeTruthy();
    expect(screen.getByText(/^review$/i)).toBeTruthy();
    expect(screen.getByText(/sprint 7/i)).toBeTruthy();
    expect(screen.getByText(/\(active\)/i)).toBeTruthy();
    expect(screen.queryByText(/no sprint or task linkage recorded for this run/i)).toBeNull();
  });
});
