import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DesignSolutionWizardModal } from "@/components/wizards/design-solution-wizard";

const pushMock = vi.fn();
const planMutateAsyncMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogDescription: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogFooter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/components/ui/select", () => ({
  Select: ({
    value,
    onValueChange,
    children,
  }: {
    value: string;
    onValueChange: (value: string) => void;
    children: React.ReactNode;
  }) => (
    <select
      aria-label="Select specification"
      value={value}
      onChange={(event) => onValueChange(event.target.value)}
    >
      {children}
    </select>
  ),
  SelectTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SelectValue: ({ placeholder }: { placeholder?: string }) => (
    <option value="">{placeholder || "Select"}</option>
  ),
  SelectContent: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SelectItem: ({ value }: { value: string; children: React.ReactNode }) => (
    <option value={value}>{value}</option>
  ),
}));

vi.mock("@/lib/api", () => ({
  useProject: () => ({
    data: { id: 11, name: "Demo Project" },
    isLoading: false,
  }),
  useSpecKitStatus: () => ({
    data: { initialized: true, spec_count: 1, specs: [] },
    isLoading: false,
  }),
  useProjectSpecs: () => ({
    data: [
      {
        name: "001-auth-flow",
        path: "specs/001-auth-flow",
        spec_path: "specs/001-auth-flow/spec.md",
        has_spec: true,
        has_plan: false,
        has_tasks: false,
        status: "ready",
        spec_run_id: 77,
      },
    ],
    isLoading: false,
  }),
  useGeneratePlan: () => ({
    mutateAsync: planMutateAsyncMock,
    isPending: false,
  }),
  useClarifySpec: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useGenerateChecklist: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useAnalyzeSpec: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useRunImplement: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe("DesignSolutionWizardModal", () => {
  beforeEach(() => {
    pushMock.mockReset();
    planMutateAsyncMock.mockReset();
  });

  it("forwards additional planning context to plan generation", async () => {
    planMutateAsyncMock.mockResolvedValue({
      success: true,
      plan_path: "specs/001-auth-flow/plan.md",
    });

    render(
      <DesignSolutionWizardModal projectId={11} open onOpenChange={vi.fn()} />
    );

    fireEvent.change(screen.getByLabelText(/select specification/i), {
      target: { value: "specs/001-auth-flow/spec.md" },
    });
    fireEvent.change(
      screen.getByPlaceholderText(/specific implementation preferences/i),
      {
        target: {
          value: "Prefer existing auth tables and keep schema changes out of scope.",
        },
      }
    );
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /generate implementation plan/i }));
    });

    expect(planMutateAsyncMock).toHaveBeenCalledWith({
      project_id: 11,
      spec_path: "specs/001-auth-flow/spec.md",
      context: "Prefer existing auth tables and keep schema changes out of scope.",
      spec_run_id: 77,
    });
  });
});
