import { describe, expect, it } from "vitest";

import { getImplementSuccessOutcome } from "@/lib/workflow/implement-result";

describe("getImplementSuccessOutcome", () => {
  it("routes to the bootstrapped protocol when implement returns linkage", () => {
    expect(
      getImplementSuccessOutcome({
        protocol_id: 42,
        step_count: 3,
      })
    ).toEqual({
      message: "Execution bootstrapped (3 steps)",
      targetPath: "/protocols/42",
    });
  });

  it("falls back to legacy messaging when protocol linkage is absent", () => {
    expect(
      getImplementSuccessOutcome({
        protocol_id: null,
        step_count: 0,
      })
    ).toEqual({
      message: "Implementation run initialized",
      targetPath: null,
    });
  });
});
