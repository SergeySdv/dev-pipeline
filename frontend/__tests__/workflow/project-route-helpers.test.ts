import { describe, expect, it } from "vitest";

import {
  getProjectExecutionPath,
  getProjectSpecWorkflowPath,
  getProjectSpecWorkspacePath,
} from "@/lib/project-routes";

describe("getProjectExecutionPath", () => {
  it("builds the canonical execution tab route", () => {
    expect(getProjectExecutionPath(12)).toBe("/projects/12?tab=execution");
  });

  it("preserves sprint selection in query state", () => {
    expect(getProjectExecutionPath(12, 44)).toBe("/projects/12?tab=execution&sprint=44");
  });
});

describe("spec workflow routes", () => {
  it("builds the canonical spec workspace route", () => {
    expect(getProjectSpecWorkspacePath(12)).toBe("/projects/12?tab=spec");
  });

  it("builds the canonical full workflow entry route", () => {
    expect(getProjectSpecWorkflowPath(12)).toBe("/projects/12?wizard=generate-specs&tab=spec");
  });
});
