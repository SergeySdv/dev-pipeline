"use client";

import { Activity } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { useProtocolEvents } from "@/lib/api";
import { formatRelativeTime,formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";

interface EventsTabProps {
  protocolId: number;
}

const eventTypeColors: Record<string, string> = {
  step_started: "text-blue-500",
  step_completed: "text-green-500",
  step_failed: "text-destructive",
  step_qa_required: "text-yellow-500",
  qa_started: "text-yellow-500",
  qa_passed: "text-green-500",
  qa_failed: "text-destructive",
  planning_started: "text-blue-500",
  planning_completed: "text-green-500",
  protocol_started: "text-blue-500",
  protocol_completed: "text-green-500",
  protocol_failed: "text-destructive",
  protocol_paused: "text-yellow-500",
  protocol_resumed: "text-blue-500",
  policy_finding: "text-yellow-500",
};

const categoryLabels: Record<string, string> = {
  onboarding: "Onboarding",
  discovery: "Discovery",
  planning: "Planning",
  execution: "Execution",
  qa: "QA",
  policy: "Policy",
  ci_webhook: "CI/Webhook",
  other: "Other",
};

const categoryColors: Record<string, string> = {
  onboarding: "text-sky-500",
  discovery: "text-indigo-500",
  planning: "text-blue-500",
  execution: "text-emerald-500",
  qa: "text-amber-500",
  policy: "text-orange-500",
  ci_webhook: "text-fuchsia-500",
  other: "text-muted-foreground",
};

export function EventsTab({ protocolId }: EventsTabProps) {
  const { data: events, isLoading } = useProtocolEvents(protocolId);

  if (isLoading) return <LoadingState message="Loading events..." />;

  if (!events || events.length === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="No events yet"
        description="Events will appear here as the protocol runs."
      />
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Event Timeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {events.map((event) => (
            <div key={event.id} className="flex items-start gap-4">
              <div className="text-muted-foreground min-w-20 font-mono text-sm">
                {formatTime(event.created_at)}
              </div>
              <div className="relative flex-shrink-0">
                <div className="bg-muted border-background h-3 w-3 rounded-full border-2" />
                <div className="bg-border absolute top-3 bottom-0 left-1/2 h-full w-px -translate-x-1/2" />
              </div>
              <div className="flex-1 pb-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p
                    className={cn(
                      "font-mono text-sm",
                      eventTypeColors[event.event_type] ||
                        categoryColors[event.event_category || ""] ||
                        "text-muted-foreground"
                    )}
                  >
                    {event.event_type}
                  </p>
                  <span className="text-muted-foreground bg-muted rounded px-1.5 py-0.5 text-xs">
                    {categoryLabels[event.event_category || "other"] ||
                      event.event_category ||
                      "Other"}
                  </span>
                </div>
                <p className="mt-1 text-sm">{event.message}</p>
                <p className="text-muted-foreground mt-1 text-xs">
                  {formatRelativeTime(event.created_at)}
                </p>
                {event.metadata && Object.keys(event.metadata).length > 0 && (
                  <pre className="text-muted-foreground bg-muted mt-2 overflow-auto rounded p-2 text-xs">
                    {JSON.stringify(event.metadata, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
