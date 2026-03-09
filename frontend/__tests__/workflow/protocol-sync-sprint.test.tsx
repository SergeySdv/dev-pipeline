import { Suspense } from "react";

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProtocolDetailPage from "@/app/protocols/[id]/page";

const syncToSprintMutateAsyncMock = vi.fn();

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
  useProtocol: () => ({
    data: {
      id: 42,
      project_id: 12,
      protocol_name: "Auth Flow",
      status: "running",
      base_branch: "main",
      description: null,
      spec_hash: "abc123",
      policy_pack_key: null,
      speckit_metadata: {
        spec_run_id: 77,
      },
      linked_sprint_id: 5,
    },
    isLoading: false,
  }),
  useProject: () => ({
    data: {
      id: 12,
      name: "Demo Project",
    },
  }),
  useProtocolAction: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useProtocolFlow: () => ({
    data: null,
  }),
  useCreateProtocolFlow: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useProtocolSprint: () => ({
    data: {
      id: 5,
      name: "Sprint Sync",
      status: "active",
    },
  }),
  useSyncProtocolToSprint: () => ({
    mutateAsync: syncToSprintMutateAsyncMock,
    isPending: false,
  }),
}));

vi.mock("@/app/protocols/[id]/components/artifacts-tab", () => ({
  ArtifactsTab: () => <div>Artifacts</div>,
}));
vi.mock("@/app/protocols/[id]/components/clarifications-tab", () => ({
  ClarificationsTab: () => <div>Clarifications</div>,
}));
vi.mock("@/app/protocols/[id]/components/events-tab", () => ({
  EventsTab: () => <div>Events</div>,
}));
vi.mock("@/app/protocols/[id]/components/feedback-tab", () => ({
  FeedbackTab: () => <div>Feedback</div>,
}));
vi.mock("@/app/protocols/[id]/components/logs-tab", () => ({
  LogsTab: () => <div>Logs</div>,
}));
vi.mock("@/app/protocols/[id]/components/policy-tab", () => ({
  PolicyTab: () => <div>Policy</div>,
}));
vi.mock("@/app/protocols/[id]/components/quality-tab", () => ({
  QualityTab: () => <div>Quality</div>,
}));
vi.mock("@/app/protocols/[id]/components/runs-tab", () => ({
  RunsTab: () => <div>Runs</div>,
}));
vi.mock("@/app/protocols/[id]/components/spec-tab", () => ({
  SpecTab: () => <div>Spec</div>,
}));
vi.mock("@/app/protocols/[id]/components/steps-tab", () => ({
  StepsTab: () => <div>Steps</div>,
}));

describe("Protocol sprint sync action", () => {
  beforeEach(() => {
    syncToSprintMutateAsyncMock.mockReset();
    syncToSprintMutateAsyncMock.mockResolvedValue({ sprint_id: 5, protocol_run_id: 42 });
  });

  it("passes the linked sprint id to the sync mutation", async () => {
    await act(async () => {
      render(
        <Suspense fallback={<div>Loading...</div>}>
          <ProtocolDetailPage params={Promise.resolve({ id: "42" })} />
        </Suspense>
      );
    });

    fireEvent.click(await screen.findByRole("button", { name: /sync sprint/i }));

    await waitFor(() => {
      expect(syncToSprintMutateAsyncMock).toHaveBeenCalledWith({
        protocolId: 42,
        sprintId: 5,
      });
    });
  });
});
