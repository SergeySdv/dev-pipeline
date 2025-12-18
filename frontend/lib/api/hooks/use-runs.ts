"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "../client"
import { queryKeys } from "../query-keys"
import type { CodexRun, RunArtifact, RunFilters } from "../types"

const useConditionalRefetchInterval = (baseInterval: number) => {
  if (typeof document === "undefined") return false
  return document.hidden ? false : baseInterval
}

// List Runs with filters
export function useRuns(filters: RunFilters = {}) {
  const refetchInterval = useConditionalRefetchInterval(10000)
  return useQuery({
    queryKey: queryKeys.runs.list(filters),
    queryFn: () => {
      const params = new URLSearchParams()
      if (filters.job_type) params.set("job_type", filters.job_type)
      if (filters.status) params.set("status", filters.status)
      if (filters.run_kind) params.set("run_kind", filters.run_kind)
      if (filters.project_id) params.set("project_id", String(filters.project_id))
      if (filters.protocol_run_id) params.set("protocol_run_id", String(filters.protocol_run_id))
      if (filters.step_run_id) params.set("step_run_id", String(filters.step_run_id))
      if (filters.limit) params.set("limit", String(filters.limit))
      const queryString = params.toString()
      return apiClient.get<CodexRun[]>(`/codex/runs${queryString ? `?${queryString}` : ""}`)
    },
    refetchInterval,
  })
}

// Get Run Detail
export function useRun(runId: string | undefined) {
  const refetchInterval = useConditionalRefetchInterval(5000)
  return useQuery({
    queryKey: queryKeys.runs.detail(runId!),
    queryFn: () => apiClient.get<CodexRun>(`/codex/runs/${runId}`),
    enabled: !!runId,
    refetchInterval,
  })
}

export const useRunDetail = useRun

// Get Run Logs
export function useRunLogs(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.runs.logs(runId!),
    queryFn: () => apiClient.get<{ content: string }>(`/codex/runs/${runId}/logs`),
    enabled: !!runId,
  })
}

// Get Run Artifacts
export function useRunArtifacts(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.runs.artifacts(runId!),
    queryFn: () => apiClient.get<RunArtifact[]>(`/codex/runs/${runId}/artifacts`),
    enabled: !!runId,
  })
}
