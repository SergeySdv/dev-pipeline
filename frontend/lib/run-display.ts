import type { CodexRun } from "@/lib/api/types";

export interface RunLinkageStats {
  activeRuns: number;
  protocolLinkedRuns: number;
  stepLinkedRuns: number;
}

export interface RunContextSummary {
  protocolLabel: string | null;
  stepLabel: string | null;
  isLinked: boolean;
}

export function getRunLinkageStats(runs: CodexRun[]): RunLinkageStats {
  return runs.reduce(
    (stats, run) => {
      if (run.status === "queued" || run.status === "running") {
        stats.activeRuns += 1;
      }
      if (typeof run.protocol_run_id === "number") {
        stats.protocolLinkedRuns += 1;
      }
      if (typeof run.step_run_id === "number") {
        stats.stepLinkedRuns += 1;
      }
      return stats;
    },
    {
      activeRuns: 0,
      protocolLinkedRuns: 0,
      stepLinkedRuns: 0,
    }
  );
}

export function summarizeRunContext(run: CodexRun): RunContextSummary {
  const protocolLabel =
    typeof run.protocol_run_id === "number" ? `Protocol #${run.protocol_run_id}` : null;
  const stepLabel = typeof run.step_run_id === "number" ? `Step #${run.step_run_id}` : null;
  return {
    protocolLabel,
    stepLabel,
    isLinked: Boolean(protocolLabel || stepLabel),
  };
}
