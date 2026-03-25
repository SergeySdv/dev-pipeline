import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GenerateSpecsWizardModal } from "@/components/wizards/generate-specs-wizard";

const pushMock = vi.fn();
const refetchMock = vi.fn();
const initMutateAsyncMock = vi.fn();
const generateSpecMutateAsyncMock = vi.fn();
const runWorkflowMutateAsyncMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("@/lib/api", () => ({
  useProject: () => ({
    data: { id: 7, name: "Demo Project" },
    isLoading: false,
  }),
  useSpecKitStatus: () => ({
    data: { initialized: true, spec_count: 0, specs: [] },
    isLoading: false,
    refetch: refetchMock,
  }),
  useInitSpecKit: () => ({
    mutateAsync: initMutateAsyncMock,
    isPending: false,
  }),
  useGenerateSpec: () => ({
    mutateAsync: generateSpecMutateAsyncMock,
    isPending: false,
  }),
  useRunWorkflow: () => ({
    mutateAsync: runWorkflowMutateAsyncMock,
    isPending: false,
  }),
  useClarifySpec: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useGenerateChecklist: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useAnalyzeSpec: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useRunImplement: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

describe("GenerateSpecsWizardModal workflow integration", () => {
  beforeEach(() => {
    pushMock.mockReset();
    refetchMock.mockReset();
    initMutateAsyncMock.mockReset();
    generateSpecMutateAsyncMock.mockReset();
    runWorkflowMutateAsyncMock.mockReset();
  });

  it("uses the canonical workflow endpoint for the default happy path", async () => {
    runWorkflowMutateAsyncMock.mockResolvedValue({
      success: true,
      spec_path: "specs/001-auth-flow/spec.md",
      plan_path: "specs/001-auth-flow/plan.md",
      tasks_path: "specs/001-auth-flow/tasks.md",
      task_count: 5,
      parallelizable_count: 2,
      spec_run_id: 77,
      steps: [],
      error: null,
    });

    render(<GenerateSpecsWizardModal projectId={7} open={true} onOpenChange={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/feature name/i), {
      target: { value: "Auth Flow" },
    });
    fireEvent.change(screen.getByLabelText(/^description/i), {
      target: { value: "Build a deterministic authentication onboarding flow." },
    });

    fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

    fireEvent.change(screen.getByLabelText(/functional requirements/i), {
      target: { value: "Users can sign in and see an authenticated dashboard." },
    });
    fireEvent.change(screen.getByLabelText(/constraints/i), {
      target: { value: "Reuse existing auth tables and routes." },
    });

    fireEvent.click(screen.getByRole("button", { name: /^next$/i }));
    fireEvent.click(screen.getByRole("button", { name: /run spec workflow/i }));

    await waitFor(() => {
      expect(runWorkflowMutateAsyncMock).toHaveBeenCalledWith({
        project_id: 7,
        description:
          "Build a deterministic authentication onboarding flow.\n\n## Requirements\nUsers can sign in and see an authenticated dashboard.\n\n## Constraints & Considerations\nReuse existing auth tables and routes.",
        feature_name: "Auth Flow",
      });
    });
    expect(generateSpecMutateAsyncMock).not.toHaveBeenCalled();
  });
});
