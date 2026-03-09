import { Suspense } from "react";

import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import SpecificationDetailPage from "@/app/specifications/[id]/page";

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
  useSpecification: () => ({
    data: {
      id: 77,
      spec_run_id: 77,
      title: "Review Ready",
      path: "specs/0001-review-ready",
      project_id: 11,
      project_name: "Spec Review Project",
      status: "completed",
      tasks_generated: true,
      has_plan: true,
      has_tasks: true,
      checklist_path: "specs/0001-review-ready/checklist.md",
      analysis_path: "specs/0001-review-ready/analysis.md",
      implement_path: "specs/0001-review-ready/_runtime",
      protocol_id: 42,
      sprint_id: null,
      sprint_name: null,
      linked_tasks: 5,
      completed_tasks: 2,
      story_points: 8,
    },
    isLoading: false,
  }),
  useSpecificationContent: () => ({
    data: {
      id: 77,
      path: "specs/0001-review-ready",
      title: "Review Ready",
      spec_content: "# Spec",
      plan_content: "# Plan",
      tasks_content: "# Tasks",
      checklist_content: "# Checklist",
      analysis_content: "# Analysis\n\nImplementation review is ready.",
    },
    isLoading: false,
  }),
}));

describe("Specification detail review surface", () => {
  it("exposes analysis content as part of the implementation review surface", async () => {
    let container: HTMLElement;
    await act(async () => {
      ({ container } = render(
        <Suspense fallback={<div>Loading...</div>}>
          <SpecificationDetailPage params={Promise.resolve({ id: "77" })} />
        </Suspense>
      ));
    });

    expect(await screen.findByRole("tab", { name: /analysis/i })).toBeTruthy();
    expect(container.textContent).toContain("Review StatusReview Ready");
    expect(container.textContent).toContain("AnalysisGenerated");
    expect(screen.getAllByText(/review ready/i).length).toBeGreaterThan(0);
  });
});
