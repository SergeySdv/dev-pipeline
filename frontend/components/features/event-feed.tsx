"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Activity, Pause, Play, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatRelativeTime } from "@/lib/format"
import type { Event } from "@/lib/api/types"
import { useEventStream } from "@/lib/api"

const MAX_EVENTS = 200

export function EventFeed({
  protocolId,
  projectId,
}: {
  protocolId?: number
  projectId?: number
}) {
  const [paused, setPaused] = useState(false)
  const [eventTypeFilter, setEventTypeFilter] = useState<string>("all")
  const [search, setSearch] = useState("")
  const [events, setEvents] = useState<Event[]>([])

  const { status, lastEventId } = useEventStream(
    paused
      ? null
      : {
          protocol_id: protocolId,
          project_id: projectId,
        },
    {
      enabled: !paused,
      onEvent: (event) => {
        setEvents((prev) => {
          const next = [event, ...prev]
          const unique = new Map<number, Event>()
          for (const e of next) unique.set(e.id, e)
          return Array.from(unique.values()).slice(0, MAX_EVENTS)
        })
      },
    },
  )

  useEffect(() => {
    // When scope changes, reset list so the UI isn't confusing.
    setEvents([])
  }, [protocolId, projectId])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return events.filter((e) => {
      if (eventTypeFilter !== "all" && e.event_type !== eventTypeFilter) return false
      if (!q) return true
      const blob = `${e.event_type} ${e.message} ${e.project_name ?? ""} ${e.protocol_name ?? ""}`.toLowerCase()
      return blob.includes(q)
    })
  }, [eventTypeFilter, events, search])

  const availableEventTypes = useMemo(() => {
    const set = new Set(events.map((e) => e.event_type).filter(Boolean))
    return Array.from(set).sort()
  }, [events])

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Event Feed
            </CardTitle>
            <CardDescription>
              Real-time updates via SSE • {status} • last id: {lastEventId}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setEvents([])}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Clear
            </Button>
            <Button variant="outline" size="sm" onClick={() => setPaused((p) => !p)}>
              {paused ? <Play className="h-4 w-4 mr-2" /> : <Pause className="h-4 w-4 mr-2" />}
              {paused ? "Resume" : "Pause"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search…" className="w-64" />
          <Select value={eventTypeFilter} onValueChange={setEventTypeFilter}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Event type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All event types</SelectItem>
              {availableEventTypes.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="text-xs text-muted-foreground">{filtered.length} shown</div>
        </div>

        {filtered.length === 0 ? (
          <div className="text-sm text-muted-foreground py-6">No events yet.</div>
        ) : (
          <div className="space-y-2">
            {filtered.map((e) => (
              <div key={e.id} className="rounded-lg border p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={cn("font-mono text-xs", "text-muted-foreground")}>#{e.id}</span>
                      <Badge variant="secondary" className="text-[10px]">
                        {e.event_type}
                      </Badge>
                      {e.event_category && (
                        <Badge variant="outline" className="text-[10px]">
                          {e.event_category}
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground">{formatRelativeTime(e.created_at)}</span>
                    </div>
                    <div className="mt-1 text-sm">{e.message}</div>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {typeof e.project_id === "number" && (
                        <Link href={`/projects/${e.project_id}`} className="hover:underline">
                          Project: {e.project_name ?? e.project_id}
                        </Link>
                      )}
                      {typeof e.protocol_run_id === "number" && (
                        <Link href={`/protocols/${e.protocol_run_id}`} className="hover:underline">
                          Protocol: {e.protocol_name ?? e.protocol_run_id}
                        </Link>
                      )}
                      {typeof e.step_run_id === "number" && (
                        <Link href={`/steps/${e.step_run_id}`} className="hover:underline">
                          Step: {e.step_run_id}
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
                {e.metadata && Object.keys(e.metadata).length > 0 && (
                  <pre className="mt-3 text-xs bg-muted/40 rounded p-3 overflow-auto">
                    {JSON.stringify(e.metadata, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

