"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../client";
import { queryKeys } from "../query-keys";
import type { AgentHealth, AgentMetrics } from "../types";

export function useAgentHealth(projectId?: number) {
  const suffix = projectId ? `?project_id=${projectId}` : "";
  return useQuery({
    queryKey: queryKeys.agents.health(projectId),
    queryFn: () => apiClient.get<AgentHealth[]>(`/agents/health${suffix}`),
  });
}

export function useAgentMetrics(projectId?: number) {
  const suffix = projectId ? `?project_id=${projectId}` : "";
  return useQuery({
    queryKey: queryKeys.agents.metrics(projectId),
    queryFn: () => apiClient.get<AgentMetrics[]>(`/agents/metrics${suffix}`),
  });
}
