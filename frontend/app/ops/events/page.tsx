"use client"

import { useState } from "react"
import { useRecentEvents, useProjects } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { RefreshCw, Activity } from "lucide-react"
import { formatTime, formatRelativeTime } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { EventFilters } from "@/lib/api/types"

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

export default function EventsPage() {
  const [filters, setFilters] = useState<EventFilters>({
    limit: 50,
  })

  const { data: events, isLoading, refetch } = useRecentEvents(filters)
  const { data: projects } = useProjects()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Recent Events</h2>
        <Button variant="outline" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="flex flex-wrap gap-4">
        <Select
          value={filters.project_id?.toString() || "all"}
          onValueChange={(v) => setFilters((f) => ({ ...f, project_id: v === "all" ? undefined : Number(v) }))}
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Projects" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Projects</SelectItem>
            {projects?.map((project) => (
              <SelectItem key={project.id} value={project.id.toString()}>
                {project.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={filters.kind || "all"}
          onValueChange={(v) => setFilters((f) => ({ ...f, kind: v === "all" ? undefined : v }))}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Event Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="step_started">step_started</SelectItem>
            <SelectItem value="step_completed">step_completed</SelectItem>
            <SelectItem value="step_failed">step_failed</SelectItem>
            <SelectItem value="qa_enqueued">qa_enqueued</SelectItem>
            <SelectItem value="planning_started">planning_started</SelectItem>
            <SelectItem value="protocol_started">protocol_started</SelectItem>
            <SelectItem value="protocol_completed">protocol_completed</SelectItem>
          </SelectContent>
        </Select>

        <Input
          type="number"
          placeholder="Limit"
          className="w-24"
          value={filters.limit || 50}
          onChange={(e) => setFilters((f) => ({ ...f, limit: Number(e.target.value) || 50 }))}
        />
      </div>

      {isLoading ? (
        <LoadingState message="Loading events..." />
      ) : !events || events.length === 0 ? (
        <EmptyState icon={Activity} title="No events" description="No events match your filter criteria." />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Event Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {events.map((event) => (
                <div key={event.id} className="flex gap-4 items-start">
                  <div className="text-sm text-muted-foreground min-w-24 font-mono">{formatTime(event.created_at)}</div>
                  <div className="relative flex-shrink-0">
                    <div className="h-3 w-3 rounded-full bg-muted border-2 border-background" />
                    <div className="absolute top-3 bottom-0 left-1/2 -translate-x-1/2 w-px bg-border h-full" />
                  </div>
                  <div className="flex-1 pb-4">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={cn(
                          "font-mono text-sm",
                          eventTypeColors[event.event_type] || "text-muted-foreground",
                        )}
                      >
                        {event.event_type}
                      </span>
                      {event.project_name && (
                        <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                          {event.project_name}
                        </span>
                      )}
                      {event.protocol_name && (
                        <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                          {event.protocol_name}
                        </span>
                      )}
                    </div>
                    <p className="text-sm mt-1">{event.message}</p>
                    <p className="text-xs text-muted-foreground mt-1">{formatRelativeTime(event.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
