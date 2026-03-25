import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { TaskCycleTab } from "@/app/projects/[id]/components/task-cycle-tab"

const hooks = vi.hoisted(() => ({
  useAgents: vi.fn(),
  useArchiveWorkItem: vi.fn(),
  useBuildContextWorkItem: vi.fn(),
  useCancelWorkItem: vi.fn(),
  useImplementWorkItem: vi.fn(),
  useMarkPrReady: vi.fn(),
  usePlanWorkItem: vi.fn(),
  useProjectProtocols: vi.fn(),
  useProjectTaskCycle: vi.fn(),
  useQaWorkItem: vi.fn(),
  useRefactorWorkItem: vi.fn(),
  useReassignWorkItemOwner: vi.fn(),
  useReviewWorkItem: vi.fn(),
  useStartBrownfieldRun: vi.fn(),
  useStepArtifactContent: vi.fn(),
  useWorkItemArtifactContent: vi.fn(),
  useWorkItemRuntime: vi.fn(),
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
    hooks.useAgents.mockReturnValue({
      data: [
        { id: "opencode", name: "OpenCode", enabled: true },
        { id: "codex", name: "OpenAI Codex", enabled: true },
      ],
    })
    hooks.useProjectProtocols.mockReturnValue({
      data: [{ id: 7, protocol_name: "demo-feature", status: "planned" }],
      isLoading: false,
    })
    hooks.useProjectTaskCycle.mockReturnValue({
      data: [
        {
          id: 11,
          project_id: 3,
          protocol_run_id: 7,
          title: "step-01-demo",
          status: "needs_rework",
          lifecycle_state: "active",
          lifecycle_reason: null,
          context_status: "ready",
          plan_status: "ready",
          review_status: "failed",
          qa_status: "pending",
          refactor_status: "not_needed",
          owner_agent: "dev",
          helper_agents: [],
          task_dir: "/tmp/task",
          artifact_refs: {
            task_dir: "/tmp/task",
            context_pack_json: "/tmp/task/context_pack.json",
            context_pack_md: "/tmp/task/context_pack.md",
            plan_pack_json: "/tmp/task/plan_pack.json",
            plan_pack_md: "/tmp/task/plan_pack.md",
            review_report_json: "/tmp/task/review_report.json",
            review_report_md: "/tmp/task/review_report.md",
            test_report_json: "/tmp/task/test_report.json",
            test_report_md: "/tmp/task/test_report.md",
            pr_ready_report_json: "/tmp/task/pr_ready_report.json",
            pr_ready_report_md: "/tmp/task/pr_ready_report.md",
            rework_pack_json: "/tmp/task/rework_pack.json",
            step_artifacts_dir: "/tmp/task/artifacts",
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
    hooks.useArchiveWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useBuildContextWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useCancelWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useImplementWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useMarkPrReady.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.usePlanWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useQaWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useRefactorWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useReassignWorkItemOwner.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useReviewWorkItem.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}) })
    hooks.useStepArtifactContent.mockReturnValue({ data: null, isLoading: false })
    hooks.useWorkItemArtifactContent.mockReturnValue({ data: null, isLoading: false })
    hooks.useWorkItemRuntime.mockReturnValue({ data: null, isLoading: false })
  })

  it("renders lifecycle controls and work-item actions", () => {
    render(<TaskCycleTab projectId={3} />)

    expect(screen.getByText("Task Cycle")).toBeTruthy()
    expect(screen.getByText("step-01-demo")).toBeTruthy()
    expect(screen.getByText("Active only")).toBeTruthy()
    expect(screen.getByRole("button", { name: /build context/i })).toBeTruthy()
    expect(screen.getByRole("button", { name: /^plan$/i })).toBeTruthy()
    expect(screen.getByRole("button", { name: /refactor/i })).toBeTruthy()
    expect(screen.getByRole("button", { name: /archive/i })).toBeTruthy()
    expect(screen.getByRole("button", { name: /cancel/i })).toBeTruthy()
    expect(screen.getByRole("button", { name: /save owner/i })).toBeTruthy()
    expect(hooks.useProjectTaskCycle).toHaveBeenCalledWith(3, undefined, "active")
  })

  it("starts a brownfield run from the form", async () => {
    const start = vi.fn().mockResolvedValue({
      protocol: { id: 9, protocol_name: "invoice-audit-trail" },
      work_items: [],
    })
    hooks.useStartBrownfieldRun.mockReturnValue({ mutateAsync: start, isPending: false })

    render(<TaskCycleTab projectId={5} />)

    fireEvent.change(screen.getByPlaceholderText("Feature name"), {
      target: { value: "invoice-audit-trail" },
    })
    fireEvent.change(
      screen.getByPlaceholderText("Describe the brownfield change, expected behavior, and constraints"),
      {
        target: { value: "Add audit trail to invoice status changes" },
      }
    )
    fireEvent.click(screen.getByRole("button", { name: /start brownfield run/i }))

    await waitFor(() => {
      expect(start).toHaveBeenCalledWith({
        projectId: 5,
        data: {
          feature_request: "Add audit trail to invoice status changes",
          feature_name: "invoice-audit-trail",
        },
      })
    })
    expect(toast.success).toHaveBeenCalledWith("Brownfield run created: invoice-audit-trail")
  })

  it("enables QA when review has passed and enables PR readiness after QA passes", () => {
    hooks.useProjectTaskCycle.mockReturnValue({
      data: [
        {
          id: 11,
          project_id: 3,
          protocol_run_id: 7,
          title: "step-01-demo",
          status: "awaiting_review",
          lifecycle_state: "active",
          lifecycle_reason: null,
          context_status: "ready",
          plan_status: "ready",
          review_status: "passed",
          qa_status: "pending",
          refactor_status: "not_needed",
          owner_agent: "dev",
          helper_agents: [],
          task_dir: "/tmp/task",
          artifact_refs: {
            task_dir: "/tmp/task",
            context_pack_json: "/tmp/task/context_pack.json",
            context_pack_md: "/tmp/task/context_pack.md",
            plan_pack_json: "/tmp/task/plan_pack.json",
            plan_pack_md: "/tmp/task/plan_pack.md",
            review_report_json: "/tmp/task/review_report.json",
            review_report_md: "/tmp/task/review_report.md",
            test_report_json: "/tmp/task/test_report.json",
            test_report_md: "/tmp/task/test_report.md",
            pr_ready_report_json: "/tmp/task/pr_ready_report.json",
            pr_ready_report_md: "/tmp/task/pr_ready_report.md",
            rework_pack_json: "/tmp/task/rework_pack.json",
            step_artifacts_dir: "/tmp/task/artifacts",
          },
          depends_on: [],
          pr_ready: false,
          blocking_clarifications: 0,
          blocking_policy_findings: 0,
          iteration_count: 2,
          max_iterations: 5,
          summary: "Add demo behavior",
        },
      ],
      isLoading: false,
    })

    const { rerender } = render(<TaskCycleTab projectId={3} />)

    expect(screen.getByRole("button", { name: /^QA$/i }).hasAttribute("disabled")).toBe(false)
    expect(screen.getByRole("button", { name: /mark pr ready/i }).hasAttribute("disabled")).toBe(true)

    hooks.useProjectTaskCycle.mockReturnValue({
      data: [
        {
          id: 11,
          project_id: 3,
          protocol_run_id: 7,
          title: "step-01-demo",
          status: "ready_for_pr",
          lifecycle_state: "active",
          lifecycle_reason: null,
          context_status: "ready",
          plan_status: "ready",
          review_status: "passed",
          qa_status: "passed",
          refactor_status: "not_needed",
          owner_agent: "dev",
          helper_agents: [],
          task_dir: "/tmp/task",
          artifact_refs: {
            task_dir: "/tmp/task",
            context_pack_json: "/tmp/task/context_pack.json",
            context_pack_md: "/tmp/task/context_pack.md",
            plan_pack_json: "/tmp/task/plan_pack.json",
            plan_pack_md: "/tmp/task/plan_pack.md",
            review_report_json: "/tmp/task/review_report.json",
            review_report_md: "/tmp/task/review_report.md",
            test_report_json: "/tmp/task/test_report.json",
            test_report_md: "/tmp/task/test_report.md",
            pr_ready_report_json: "/tmp/task/pr_ready_report.json",
            pr_ready_report_md: "/tmp/task/pr_ready_report.md",
            rework_pack_json: "/tmp/task/rework_pack.json",
            step_artifacts_dir: "/tmp/task/artifacts",
          },
          depends_on: [],
          pr_ready: false,
          blocking_clarifications: 0,
          blocking_policy_findings: 0,
          iteration_count: 2,
          max_iterations: 5,
          summary: "Add demo behavior",
        },
      ],
      isLoading: false,
    })

    rerender(<TaskCycleTab projectId={3} />)

    expect(screen.getByRole("button", { name: /mark pr ready/i }).hasAttribute("disabled")).toBe(false)
  })

  it("enables refactor after QA passes for needs_refactor reviews", () => {
    hooks.useProjectTaskCycle.mockReturnValue({
      data: [
        {
          id: 11,
          project_id: 3,
          protocol_run_id: 7,
          title: "step-01-demo",
          status: "needs_refactor",
          lifecycle_state: "active",
          lifecycle_reason: null,
          context_status: "ready",
          plan_status: "ready",
          review_status: "needs_refactor",
          qa_status: "passed",
          refactor_status: "required",
          owner_agent: "dev",
          helper_agents: [],
          task_dir: "/tmp/task",
          artifact_refs: {
            task_dir: "/tmp/task",
            context_pack_json: "/tmp/task/context_pack.json",
            context_pack_md: "/tmp/task/context_pack.md",
            plan_pack_json: "/tmp/task/plan_pack.json",
            plan_pack_md: "/tmp/task/plan_pack.md",
            review_report_json: "/tmp/task/review_report.json",
            review_report_md: "/tmp/task/review_report.md",
            test_report_json: "/tmp/task/test_report.json",
            test_report_md: "/tmp/task/test_report.md",
            pr_ready_report_json: "/tmp/task/pr_ready_report.json",
            pr_ready_report_md: "/tmp/task/pr_ready_report.md",
            rework_pack_json: "/tmp/task/rework_pack.json",
            step_artifacts_dir: "/tmp/task/artifacts",
          },
          depends_on: [],
          pr_ready: false,
          blocking_clarifications: 0,
          blocking_policy_findings: 0,
          iteration_count: 2,
          max_iterations: 5,
          summary: "Add demo behavior",
        },
      ],
      isLoading: false,
    })

    render(<TaskCycleTab projectId={3} />)

    expect(screen.getByRole("button", { name: /^QA$/i }).hasAttribute("disabled")).toBe(false)
    expect(screen.getByRole("button", { name: /refactor/i }).hasAttribute("disabled")).toBe(false)
    expect(screen.getByRole("button", { name: /mark pr ready/i }).hasAttribute("disabled")).toBe(true)
  })
})
