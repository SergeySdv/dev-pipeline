import { describe, expect, it } from "vitest";

import { artifactBytes, artifactKind, artifactPath } from "@/lib/artifacts";

describe("artifact metadata helpers", () => {
  it("prefers current API fields for protocol and step artifacts", () => {
    const artifact = {
      type: "log",
      size: 128,
      created_at: null,
    };

    expect(artifactKind(artifact)).toBe("log");
    expect(artifactBytes(artifact)).toBe(128);
    expect(artifactPath(artifact)).toBeNull();
  });

  it("accepts legacy alias fields when present", () => {
    const artifact = {
      kind: "diff",
      bytes: 256,
      path: "artifacts/changes.diff",
    };

    expect(artifactKind(artifact)).toBe("diff");
    expect(artifactBytes(artifact)).toBe(256);
    expect(artifactPath(artifact)).toBe("artifacts/changes.diff");
  });
});
