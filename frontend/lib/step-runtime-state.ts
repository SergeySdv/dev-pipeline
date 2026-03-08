import type { StepRuntimeState } from "@/lib/api/types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function hasTaskCycleRuntimeState(
  runtimeState: StepRuntimeState | null | undefined,
): boolean {
  return isRecord(runtimeState) && isRecord(runtimeState.task_cycle);
}

export function runtimeStateForStepPage(
  runtimeState: StepRuntimeState | null | undefined,
): StepRuntimeState | null {
  if (!isRecord(runtimeState)) {
    return null;
  }

  const { task_cycle: _taskCycle, qa_verdict: _qaVerdict, ...rest } = runtimeState;
  return Object.keys(rest).length > 0 ? rest : null;
}
