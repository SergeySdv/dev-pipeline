import { describe, expect, it } from "vitest";

import { hasTaskCycleRuntimeState, runtimeStateForStepPage } from "@/lib/step-runtime-state";

describe("step runtime state helpers", () => {
  it("omits raw task-cycle and qa internals from the generic step page state dump", () => {
    const runtimeState = {
      qa_verdict: {
        verdict: "pass",
      },
      task_cycle: {
        status: "queued",
        owner_agent: "dev",
      },
    };

    expect(hasTaskCycleRuntimeState(runtimeState)).toBe(true);
    expect(runtimeStateForStepPage(runtimeState)).toBeNull();
  });

  it("hides the runtime state card when task-cycle data is the only payload", () => {
    const runtimeState = {
      task_cycle: {
        status: "queued",
      },
    };

    expect(hasTaskCycleRuntimeState(runtimeState)).toBe(true);
    expect(runtimeStateForStepPage(runtimeState)).toBeNull();
  });

  it("preserves non-qa runtime metadata", () => {
    const runtimeState = {
      loop_counts: {
        execute: 2,
      },
      inline_trigger_depth: 1,
      qa_verdict: {
        verdict: "pass",
      },
    };

    expect(hasTaskCycleRuntimeState(runtimeState)).toBe(false);
    expect(runtimeStateForStepPage(runtimeState)).toEqual({
      loop_counts: {
        execute: 2,
      },
      inline_trigger_depth: 1,
    });
  });
});
