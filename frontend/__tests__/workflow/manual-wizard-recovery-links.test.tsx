import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DesignSolutionWizardModal } from "@/components/wizards/design-solution-wizard";
import { ImplementFeatureWizardModal } from "@/components/wizards/implement-feature-wizard";

const pushMock = vi.fn();
const specKitStatusState = { initialized: true };
let projectSpecsState: Array<Record<string, unknown>> = [];
let sprintsState: Array<Record<string, unknown>> = [];

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogDescription: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/components/ui/select", () => ({
  Select: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectValue: ({ placeholder }: { placeholder?: string }) => <span>{placeholder}</span>,
  SelectContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectItem: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/components/shared", () => ({
  ClarificationDialog: () => null,
  DesignSolutionWizardSkeleton: () => <div>Loading...</div>,
  ImplementFeatureWizardSkeleton: () => <div>Loading...</div>,
}));

vi.mock("@/lib/api", () => ({
  useProject: () => ({
    data: { id: 11, name: "Demo Project" },
    isLoading: false,
  }),
  useSpecKitStatus: () => ({
    data: {
      initialized: specKitStatusState.initialized,
      spec_count: projectSpecsState.length,
      specs: projectSpecsState,
    },
    isLoading: false,
  }),
  useProjectSpecs: () => ({
    data: projectSpecsState,
    isLoading: false,
  }),
  useSprints: () => ({
    data: sprintsState,
    isLoading: false,
  }),
  useGeneratePlan: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useClarifySpec: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useGenerateChecklist: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useAnalyzeSpec: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useRunImplement: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useGenerateTasks: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useImportTasksToSprint: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useCreateProtocolFromSpec: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe("manual wizard recovery links", () => {
  beforeEach(() => {
    pushMock.mockReset();
    specKitStatusState.initialized = true;
    projectSpecsState = [];
    sprintsState = [];
  });

  it("sends manual planning users to the canonical workflow when SpecKit is uninitialized", () => {
    specKitStatusState.initialized = false;

    render(<DesignSolutionWizardModal projectId={11} open onOpenChange={vi.fn()} />);

    expect(
      screen.getByRole("link", { name: /run the full speckit workflow first/i }).getAttribute("href")
    ).toBe("/projects/11?wizard=generate-specs&tab=spec");
  });

  it("sends manual planning users to the canonical workflow when no specs exist", () => {
    render(<DesignSolutionWizardModal projectId={11} open onOpenChange={vi.fn()} />);

    expect(
      screen.getByRole("link", { name: /run the full speckit workflow first/i }).getAttribute("href")
    ).toBe("/projects/11?wizard=generate-specs&tab=spec");
  });

  it("sends manual task users to the canonical workflow when SpecKit is uninitialized", () => {
    specKitStatusState.initialized = false;

    render(<ImplementFeatureWizardModal projectId={11} open onOpenChange={vi.fn()} />);

    expect(
      screen.getByRole("link", { name: /run the full speckit workflow first/i }).getAttribute("href")
    ).toBe("/projects/11?wizard=generate-specs&tab=spec");
  });

  it("sends manual task users back to the spec workspace when no plans exist", () => {
    projectSpecsState = [
      {
        name: "001-auth-flow",
        path: "specs/001-auth-flow",
        spec_path: "specs/001-auth-flow/spec.md",
        plan_path: null,
        tasks_path: null,
        has_spec: true,
        has_plan: false,
        has_tasks: false,
        status: "ready",
      },
    ];

    render(<ImplementFeatureWizardModal projectId={11} open onOpenChange={vi.fn()} />);

    expect(
      screen.getByRole("link", { name: /open the spec workspace first/i }).getAttribute("href")
    ).toBe("/projects/11?tab=spec");
  });
});
