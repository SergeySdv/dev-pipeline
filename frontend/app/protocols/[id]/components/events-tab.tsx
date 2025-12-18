"use client"

import { useProtocolEvents } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { Activity } from "lucide-react"
import { formatTime } from "@/lib/format"
import { cn } from "@/lib/utils"

interface EventsTabProps {
  protocolId: number
}

const eventTypeColors: Record<string, string> = {
  step_started: "text-blue-500",
  step_completed: "text-green-500",
  step_failed: "text-destructive",
  qa_enqueued: "text-yellow-500",
  qa_completed: "text-green-500",
  qa_failed: "text-destructive",
  planning_started: "text-blue-500",
  planning_completed: "text-green-500",
  protocol_started: "text-blue-500",
  protocol_completed: "text-green-500",
  protocol_failed: "text-destructive",
}

export function EventsTab({ protocolId }: EventsTabProps) {
  const { data: events, isLoading } = useProtocolEvents(protocolId)

  if (isLoading) return <LoadingState message="Loading events..." />

  if (!events || events.length === 0) {
    return (
      <EmptyState icon={Activity} title="No events yet" description="Events will appear here as the protocol runs." />
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Event Timeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {events.map((event) => (
            <div key={event.id} className="flex gap-4 items-start">
              <div className="text-sm text-muted-foreground min-w-20 font-mono">{formatTime(event.created_at)}</div>
              <div className="relative flex-shrink-0">
                <div className="h-3 w-3 rounded-full bg-muted border-2 border-background" />
                <div className="absolute top-3 bottom-0 left-1/2 -translate-x-1/2 w-px bg-border h-full" />
              </div>
              <div className="flex-1 pb-4">
                <p className={cn("font-mono text-sm", eventTypeColors[event.event_type] || "text-muted-foreground")}>
                  {event.event_type}
                </p>
                <p className="text-sm mt-1">{event.message}</p>
                {event.metadata && Object.keys(event.metadata).length > 0 && (
                  <pre className="text-xs text-muted-foreground mt-2 bg-muted p-2 rounded overflow-auto">
                    {JSON.stringify(event.metadata, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
