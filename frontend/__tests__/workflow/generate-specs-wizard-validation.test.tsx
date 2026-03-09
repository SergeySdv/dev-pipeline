import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GenerateSpecsWizardModal } from "@/components/wizards/generate-specs-wizard";

const pushMock = vi.fn();
const refetchMock = vi.fn();
const mutateAsyncMock = vi.fn();

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
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
  useGenerateSpec: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
  useRunWorkflow: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
  useClarifySpec: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
  useGenerateChecklist: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
  useAnalyzeSpec: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
  useRunImplement: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
}));

describe("GenerateSpecsWizardModal validation", () => {
  beforeEach(() => {
    pushMock.mockReset();
    refetchMock.mockReset();
    mutateAsyncMock.mockReset();
  });

  it("requires at least 10 characters before enabling the next step", () => {
    render(<GenerateSpecsWizardModal projectId={7} open={true} onOpenChange={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/feature name/i), {
      target: { value: "Short validation" },
    });
    fireEvent.change(screen.getByLabelText(/description/i), {
      target: { value: "123456789" },
    });

    expect(screen.getByRole("button", { name: /next/i })).toHaveProperty("disabled", true);
  });
});
