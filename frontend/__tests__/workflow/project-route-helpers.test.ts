import { describe, expect, it } from "vitest";

import { getProjectExecutionPath } from "@/lib/project-routes";

describe("getProjectExecutionPath", () => {
  it("builds the canonical execution tab route", () => {
    expect(getProjectExecutionPath(12)).toBe("/projects/12?tab=execution");
  });

  it("preserves sprint selection in query state", () => {
    expect(getProjectExecutionPath(12, 44)).toBe("/projects/12?tab=execution&sprint=44");
  });
});
