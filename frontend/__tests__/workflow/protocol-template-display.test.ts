import { describe, expect, it } from "vitest";

import {
  describeProtocolTemplateConfig,
  formatProtocolTemplateSource,
} from "@/lib/protocol-template-display";

describe("protocol template display helpers", () => {
  it("formats structured template sources into canonical labels", () => {
    expect(
      formatProtocolTemplateSource('{"kind":"builtin","name":"brownfield/default"}')
    ).toBe("builtin: brownfield/default");
  });

  it("summarizes template config objects for metadata cards", () => {
    expect(describeProtocolTemplateConfig({ mode: "brownfield", owner: "protocol" })).toEqual({
      summary: "2 fields",
      detail: "mode=brownfield, owner=protocol",
    });
  });

  it("distinguishes absent and empty template config values", () => {
    expect(describeProtocolTemplateConfig(null)).toEqual({ summary: "None", detail: null });
    expect(describeProtocolTemplateConfig({})).toEqual({
      summary: "0 fields",
      detail: "Empty JSON object",
    });
  });
});
