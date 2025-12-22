"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { apiClient } from "@/lib/api/client"
import type { Event as DevGodzillaEvent } from "@/lib/api/types"

export interface EventStreamFilters {
  protocol_id?: number
  project_id?: number
  event_type?: string
  categories?: string[]
  since_id?: number
}

export interface EventStreamState {
  status: "idle" | "connecting" | "open" | "error"
  lastEventId: number
}

export function useEventStream(
  filters: EventStreamFilters | null,
  options?: {
    enabled?: boolean
    onEvent?: (event: DevGodzillaEvent) => void
  },
): EventStreamState {
  const [state, setState] = useState<EventStreamState>({ status: "idle", lastEventId: 0 })
  const onEventRef = useRef(options?.onEvent)
  onEventRef.current = options?.onEvent

  const enabled = options?.enabled ?? true

  const streamUrl = useMemo(() => {
    if (!enabled || !filters) return null

    const params = new URLSearchParams()
    if (typeof filters.protocol_id === "number") params.set("protocol_id", String(filters.protocol_id))
    if (typeof filters.project_id === "number") params.set("project_id", String(filters.project_id))
    if (filters.event_type) params.set("event_type", filters.event_type)
    for (const category of filters.categories ?? []) {
      if (category) params.append("category", category)
    }
    if (typeof filters.since_id === "number" && filters.since_id > 0) params.set("since_id", String(filters.since_id))

    const { baseUrl, token } = apiClient.getConfig()
    if (token) params.set("token", token)

    const normalizedBase = (baseUrl || "").replace(/\/$/, "")
    const path = `/events/stream?${params.toString()}`
    return normalizedBase ? `${normalizedBase}${path}` : path
  }, [enabled, filters])

  useEffect(() => {
    if (!streamUrl) {
      setState({ status: "idle", lastEventId: 0 })
      return
    }

    let cancelled = false
    setState((prev) => ({ ...prev, status: "connecting" }))

    const source = new EventSource(streamUrl)

    source.onopen = () => {
      if (cancelled) return
      setState((prev) => ({ ...prev, status: "open" }))
    }

    source.onmessage = (message) => {
      if (cancelled) return
      try {
        const payload = JSON.parse(message.data) as DevGodzillaEvent
        if (typeof payload?.id === "number") {
          setState((prev) => ({ ...prev, lastEventId: Math.max(prev.lastEventId, payload.id) }))
        }
        onEventRef.current?.(payload)
      } catch {
        // Ignore malformed frames
      }
    }

    source.onerror = () => {
      if (cancelled) return
      setState((prev) => ({ ...prev, status: "error" }))
      // Let EventSource reconnect automatically; cleanup closes it.
    }

    return () => {
      cancelled = true
      source.close()
    }
  }, [streamUrl])

  return state
}

