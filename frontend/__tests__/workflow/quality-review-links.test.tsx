import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import QualityPage from "@/app/quality/page";

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
  useQualityDashboard: () => ({
    data: {
      overview: {
        total_protocols: 1,
        passed: 0,
        warnings: 0,
        failed: 1,
        average_score: 0,
      },
      recent_findings: [
        {
          id: 1,
          protocol_id: 42,
          spec_run_id: 77,
          project_name: "Demo Project",
          article: "7",
          article_name: "Traceability",
          severity: "error",
          message: "Missing implementation review handoff",
          timestamp: "2026-03-09T10:00:00Z",
        },
      ],
      constitutional_gates: [],
    },
    isLoading: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TabsList: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TabsTrigger: ({ children }: { children: React.ReactNode }) => <button>{children}</button>,
  TabsContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe("Quality review links", () => {
  it("uses a review-first action for findings with specification context", () => {
    render(<QualityPage />);

    expect(screen.getByRole("link", { name: /review implementation/i }).getAttribute("href")).toBe(
      "/specifications/77?tab=analysis"
    );
    expect(screen.getByRole("link", { name: /^protocol$/i }).getAttribute("href")).toBe(
      "/protocols/42"
    );
  });
});
