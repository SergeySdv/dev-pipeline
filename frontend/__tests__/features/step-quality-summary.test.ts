import { describe, expect, it } from "vitest";

import { summarizeStepQuality } from "@/lib/step-quality-summary";

describe("step quality summary helpers", () => {
  it("builds a compact QA summary with highlighted findings", () => {
    const summary = summarizeStepQuality({
      step_run_id: 4,
      overall_status: "failed",
      score: 0.42,
      blocking_issues: 1,
      warnings: 1,
      gates: [
        {
          name: "Prompt QA",
          article: "prompt_qa",
          status: "failed",
          findings: [
            {
              code: "prompt.missing_commit",
              severity: "error",
              message: "Repository has uncommitted changes.",
              suggested_fix: "Commit the implementation changes before retrying QA.",
            },
          ],
        },
        {
          name: "Tests",
          article: "test",
          status: "warning",
          findings: [
            {
              code: "test.flaky",
              severity: "warning",
              message: "A flaky test was retried.",
              suggested_fix: null,
            },
          ],
        },
      ],
    });

    expect(summary).toEqual({
      overallStatus: "failed",
      scorePercent: 42,
      blockingIssues: 1,
      warnings: 1,
      totalFindings: 2,
      gates: [
        {
          name: "Prompt QA",
          article: "prompt_qa",
          status: "failed",
          findingsCount: 1,
        },
        {
          name: "Tests",
          article: "test",
          status: "warning",
          findingsCount: 1,
        },
      ],
      highlightedFindings: [
        {
          gateName: "Prompt QA",
          article: "prompt_qa",
          message: "Repository has uncommitted changes.",
          suggestedFix: "Commit the implementation changes before retrying QA.",
        },
        {
          gateName: "Tests",
          article: "test",
          message: "A flaky test was retried.",
          suggestedFix: null,
        },
      ],
    });
  });

  it("returns a no-issue summary when QA passed cleanly", () => {
    const summary = summarizeStepQuality({
      step_run_id: 3,
      overall_status: "passed",
      score: 1,
      blocking_issues: 0,
      warnings: 0,
      gates: [
        {
          name: "Prompt QA",
          article: "prompt_qa",
          status: "skipped",
          findings: [],
        },
        {
          name: "Tests",
          article: "test",
          status: "passed",
          details: {
            command: "pytest --tb=short -q",
            stdout: "37 passed in 12.47s",
            stderr: null,
          },
          findings: [],
        },
      ],
    });

    expect(summary?.overallStatus).toBe("passed");
    expect(summary?.scorePercent).toBe(100);
    expect(summary?.totalFindings).toBe(0);
    expect(summary?.gates).toEqual([
      {
        name: "Prompt QA",
        article: "prompt_qa",
        status: "skipped",
        findingsCount: 0,
      },
      {
        name: "Tests",
        article: "test",
        status: "passed",
        findingsCount: 0,
      },
    ]);
    expect(summary?.highlightedFindings).toEqual([]);
  });
});
