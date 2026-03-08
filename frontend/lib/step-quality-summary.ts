import type { StepQuality } from "@/lib/api/types";

export interface StepQualitySummary {
  overallStatus: string;
  scorePercent: number;
  blockingIssues: number;
  warnings: number;
  totalFindings: number;
  gates: Array<{
    name: string;
    article: string;
    status: string;
    findingsCount: number;
  }>;
  highlightedFindings: Array<{
    gateName: string;
    article: string;
    message: string;
    suggestedFix: string | null;
  }>;
}

export function summarizeStepQuality(
  quality: StepQuality | null | undefined,
): StepQualitySummary | null {
  if (!quality) {
    return null;
  }

  const highlightedFindings = quality.gates.flatMap((gate) =>
    gate.findings.map((finding) => ({
      gateName: gate.name,
      article: gate.article,
      message: finding.message,
      suggestedFix: finding.suggested_fix ?? null,
    })),
  );

  return {
    overallStatus: quality.overall_status,
    scorePercent: Math.round(quality.score * 100),
    blockingIssues: quality.blocking_issues,
    warnings: quality.warnings,
    totalFindings: highlightedFindings.length,
    gates: quality.gates.map((gate) => ({
      name: gate.name,
      article: gate.article,
      status: gate.status,
      findingsCount: gate.findings.length,
    })),
    highlightedFindings: highlightedFindings.slice(0, 3),
  };
}
