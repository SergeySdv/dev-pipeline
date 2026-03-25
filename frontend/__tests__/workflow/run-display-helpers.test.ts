import { describe, expect, it } from "vitest";

import { getRunLinkageStats, summarizeRunContext } from "@/lib/run-display";

describe("run display helpers", () => {
  it("computes linkage and active-run counts from real run fields", () => {
    const stats = getRunLinkageStats([
      {
        run_id: "run-1",
        job_type: "execute_step",
        run_kind: "exec",
        status: "running",
        project_id: 1,
        protocol_run_id: 42,
        step_run_id: 7,
        task_id: 10,
        task_title: "Implement linked run workflow",
        task_board_status: "review",
        sprint_id: 3,
        sprint_name: "Sprint 7",
        sprint_status: "active",
        attempt: 1,
        worker_id: null,
        queue: null,
        prompt_version: null,
        params: null,
        result: null,
        error: null,
        log_path: null,
        cost_tokens: null,
        cost_cents: null,
        started_at: null,
        finished_at: null,
        created_at: "2026-03-09T10:00:00Z",
      },
      {
        run_id: "run-2",
        job_type: "run_quality",
        run_kind: "qa",
        status: "succeeded",
        project_id: 1,
        protocol_run_id: 42,
        step_run_id: null,
        task_id: null,
        task_title: null,
        task_board_status: null,
        sprint_id: null,
        sprint_name: null,
        sprint_status: null,
        attempt: 1,
        worker_id: null,
        queue: null,
        prompt_version: null,
        params: null,
        result: null,
        error: null,
        log_path: null,
        cost_tokens: null,
        cost_cents: null,
        started_at: null,
        finished_at: null,
        created_at: "2026-03-09T10:05:00Z",
      },
    ]);

    expect(stats).toEqual({
      activeRuns: 1,
      protocolLinkedRuns: 2,
      stepLinkedRuns: 1,
    });
  });

  it("marks unlinked runs honestly instead of inventing sprint/task data", () => {
    expect(
      summarizeRunContext({
        run_id: "run-1",
        job_type: "planning",
        run_kind: "exec",
        status: "queued",
        project_id: 1,
        protocol_run_id: null,
        step_run_id: null,
        task_id: null,
        task_title: null,
        task_board_status: null,
        sprint_id: null,
        sprint_name: null,
        sprint_status: null,
        attempt: 1,
        worker_id: null,
        queue: null,
        prompt_version: null,
        params: null,
        result: null,
        error: null,
        log_path: null,
        cost_tokens: null,
        cost_cents: null,
        started_at: null,
        finished_at: null,
        created_at: "2026-03-09T10:00:00Z",
      })
    ).toEqual({
      taskLabel: null,
      sprintLabel: null,
      protocolLabel: null,
      stepLabel: null,
      isLinked: false,
    });
  });

  it("surfaces real task and sprint labels when the backend provides agile context", () => {
    expect(
      summarizeRunContext({
        run_id: "run-1",
        job_type: "execute_step",
        run_kind: "exec",
        status: "running",
        project_id: 1,
        protocol_run_id: 42,
        step_run_id: 7,
        task_id: 12,
        task_title: "Implement linked run workflow",
        task_board_status: "review",
        sprint_id: 3,
        sprint_name: "Sprint 7",
        sprint_status: "active",
        attempt: 1,
        worker_id: null,
        queue: null,
        prompt_version: null,
        params: null,
        result: null,
        error: null,
        log_path: null,
        cost_tokens: null,
        cost_cents: null,
        started_at: null,
        finished_at: null,
        created_at: "2026-03-09T10:00:00Z",
      })
    ).toEqual({
      taskLabel: "Task #12: Implement linked run workflow",
      sprintLabel: "Sprint 7 (active)",
      protocolLabel: "Protocol #42",
      stepLabel: "Step #7",
      isLinked: true,
    });
  });
});
