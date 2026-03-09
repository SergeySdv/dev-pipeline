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
    runId: "run-review-context",
  }),
}));

vi.mock("@/lib/api", () => ({
  useRun: () => ({
    data: {
      run_id: "run-review-context",
      job_type: "execute_step",
      run_kind: "protocol",
      status: "running",
      project_id: 12,
      protocol_run_id: 42,
      spec_run_id: 77,
      step_run_id: null,
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

describe("Run detail review links", () => {
  it("offers review-first navigation before the raw protocol page", () => {
    render(<RunDetailPage />);

    expect(screen.getByRole("link", { name: /review implementation/i }).getAttribute("href")).toBe(
      "/specifications/77?tab=analysis"
    );
    expect(screen.getByRole("link", { name: /^protocol/i }).getAttribute("href")).toBe(
      "/protocols/42"
    );
  });
});
