import { describe, expect, it } from "vitest";

import {
  getProjectExecutionPath,
  getProjectManualPlanWizardPath,
  getProjectManualTasksWizardPath,
  getProjectSpecWorkflowPath,
  getProjectSpecWorkspacePath,
  getSpecificationDetailPath,
  getSpecificationReviewPath,
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

  it("builds the manual plan wizard route", () => {
    expect(getProjectManualPlanWizardPath(12)).toBe("/projects/12?wizard=design-solution");
  });

  it("builds the manual tasks wizard route", () => {
    expect(getProjectManualTasksWizardPath(12)).toBe("/projects/12?wizard=implement-feature");
  });

  it("builds a specification detail route", () => {
    expect(getSpecificationDetailPath(77)).toBe("/specifications/77");
  });

  it("builds a specification review route", () => {
    expect(getSpecificationReviewPath(77)).toBe("/specifications/77?tab=analysis");
  });
});
