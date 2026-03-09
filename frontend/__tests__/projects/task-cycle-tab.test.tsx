import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi, beforeEach } from "vitest"

import { TaskCycleTab } from "@/app/projects/[id]/components/task-cycle-tab"

const hooks = vi.hoisted(() => ({
  useProjectProtocols: vi.fn(),
  useProjectTaskCycle: vi.fn(),
  useStartBrownfieldRun: vi.fn(),
  useBuildContextWorkItem: vi.fn(),
  useImplementWorkItem: vi.fn(),
  useReviewWorkItem: vi.fn(),
  useQaWorkItem: vi.fn(),
  useMarkPrReady: vi.fn(),
  useWorkItemArtifactContent: vi.fn(),
}))

const toast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
}))

vi.mock("@/lib/api", () => hooks)
vi.mock("sonner", () => ({ toast }))

describe("TaskCycleTab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    hooks.useProjectProtocols.mockReturnValue({
      data: [{ id: 7, protocol_name: "demo-feature", status: "planned" }],
    })
    hooks.useProjectTaskCycle.mockReturnValue({
      data: [
        {
          id: 11,
          project_id: 3,
          protocol_run_id: 7,
          title: "step-01-demo",
          status: "needs_rework",
          context_status: "ready",
          review_status: "failed",
          qa_status: "pending",
          owner_agent: "dev",
          helper_agents: [],
          task_dir: "/tmp/task",
          artifact_refs: {
            context_pack_md: "/tmp/task/context_pack.md",
            review_report_md: "/tmp/task/review_report.md",
            test_report_md: "/tmp/task/test_report.md",
            rework_pack_json: "/tmp/task/rework_pack.json",
          },
          depends_on: [],
          pr_ready: false,
          blocking_clarifications: 1,
          blocking_policy_findings: 0,
          iteration_count: 2,
          max_iterations: 5,
          summary: "Add demo behavior",
        },
      ],
      isLoading: false,
    })
    hooks.useStartBrownfieldRun.mockReturnValue({ mutateAsync: vi.fn(), isPending: false })
    hooks.useBuildContextWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useImplementWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useReviewWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useQaWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useMarkPrReady.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useWorkItemArtifactContent.mockReturnValue({ data: null, isLoading: false })
  })

  it("renders work items and task-cycle actions", () => {
    render(<TaskCycleTab projectId={3} />)

    expect(screen.getByText("Brownfield Task Cycle")).toBeTruthy()
    expect(screen.getByText("step-01-demo")).toBeTruthy()
    expect(screen.getByText("Context: ready")).toBeTruthy()
    expect(screen.getByText("Review: failed")).toBeTruthy()
    expect(screen.getByRole("button", { name: /build context/i })).toBeTruthy()
    expect(screen.getByRole("button", { name: /mark pr ready/i })).toBeTruthy()
  })

  it("starts a brownfield task-cycle run from the form", async () => {
    const start = vi.fn().mockResolvedValue({
      protocol: { id: 9 },
      work_items: [],
    })
    hooks.useStartBrownfieldRun.mockReturnValue({ mutateAsync: start, isPending: false })

    render(<TaskCycleTab projectId={5} />)

    fireEvent.change(screen.getByLabelText("Feature request"), {
      target: { value: "Add audit trail to invoice status changes" },
    })
    fireEvent.change(screen.getByLabelText("Feature slug"), {
      target: { value: "invoice-audit-trail" },
    })
    fireEvent.click(screen.getByRole("button", { name: /start task cycle/i }))

    await waitFor(() => {
      expect(start).toHaveBeenCalledWith({
        projectId: 5,
        data: {
          feature_request: "Add audit trail to invoice status changes",
          feature_name: "invoice-audit-trail",
          output_mode: "task_cycle",
          owner_agent: "dev",
          allow_helper_agents: true,
        },
      })
    })
    expect(toast.success).toHaveBeenCalledWith("Task cycle created")
  })
})
