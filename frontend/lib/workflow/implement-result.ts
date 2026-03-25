import type { ImplementResponse } from "@/lib/api";

export function getImplementSuccessOutcome(
  result: Pick<ImplementResponse, "protocol_id" | "step_count">
): { message: string; targetPath: string | null } {
  if (result.protocol_id) {
    const stepCount = result.step_count ?? 0;
    return {
      message: stepCount > 0 ? `Execution bootstrapped (${stepCount} steps)` : "Execution bootstrapped",
      targetPath: `/protocols/${result.protocol_id}`,
    };
  }

  return {
    message: "Implementation run initialized",
    targetPath: null,
  };
}
