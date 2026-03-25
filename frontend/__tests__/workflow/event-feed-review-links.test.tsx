import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EventFeed } from "@/components/features/event-feed";

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

vi.mock("@/lib/api/hooks/use-events", () => ({
  eventHasProtocolLink: (event: { protocol_run_id?: number | null }) =>
    typeof event.protocol_run_id === "number",
  filterEventsByType: <T,>(events: T[]) => events,
  getUniqueEventTypes: () => ["protocol_started"],
  useWebSocketEventStream: () => ({
    events: [
      {
        id: 11,
        event_type: "protocol_started",
        event_category: "execution",
        message: "Protocol started",
        created_at: "2026-03-09T10:00:00Z",
        protocol_run_id: 42,
        protocol_name: "Auth Flow",
        spec_run_id: 77,
        project_id: 12,
        project_name: "Demo Project",
        step_run_id: null,
        metadata: null,
      },
    ],
    lastEventId: 11,
    isConnected: true,
  }),
}));

describe("EventFeed review links", () => {
  it("prefers a specification review entry point when the event carries spec review context", () => {
    render(<EventFeed projectId={12} />);

    expect(screen.getByRole("link", { name: /review implementation/i }).getAttribute("href")).toBe(
      "/specifications/77?tab=analysis"
    );
    expect(screen.getByRole("link", { name: /auth flow/i }).getAttribute("href")).toBe(
      "/protocols/42"
    );
  });
});
