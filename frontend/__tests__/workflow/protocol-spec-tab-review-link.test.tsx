import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SpecTab } from "@/app/protocols/[id]/components/spec-tab";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api", () => ({
  useProtocolSpec: () => ({
    data: {
      spec_run_id: 77,
      spec_hash: "abc123",
      validation_status: "valid",
      validated_at: "2026-03-09T10:00:00Z",
      spec: { name: "Auth Flow" },
    },
    isLoading: false,
  }),
}));

describe("Protocol spec tab review link", () => {
  it("links the protocol spec tab back to the canonical review workspace", () => {
    render(<SpecTab protocolId={42} />);

    expect(screen.getByRole("link", { name: /review implementation/i }).getAttribute("href")).toBe(
      "/specifications/77?tab=analysis"
    );
  });
});
