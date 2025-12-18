"use client"

import { useEffect } from "react"
import { useVisibility } from "./use-visibility"

interface UsePollingOptions {
  enabled?: boolean
  interval?: number
  onPoll: () => void
}

export function usePolling({ enabled = true, interval = 5000, onPoll }: UsePollingOptions) {
  const isVisible = useVisibility()
  const shouldPoll = enabled && isVisible

  useEffect(() => {
    if (!shouldPoll) return

    const id = setInterval(onPoll, interval)
    return () => clearInterval(id)
  }, [shouldPoll, interval, onPoll])
}
