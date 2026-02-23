"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../client";
import { queryKeys } from "../query-keys";
import type { Event, EventFilters, HealthResponse, MetricsSummary } from "../types";

const useConditionalRefetchInterval = (baseInterval: number) => {
  if (typeof document === "undefined") return false;
  if (baseInterval <= 0) return false;
  return document.hidden ? false : baseInterval;
};

// Health Check
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => apiClient.get<HealthResponse>("/health"),
    refetchInterval: 30000, // Check every 30s
  });
}

// Recent Events
export function useRecentEvents(
  filters: EventFilters = {},
  options?: { refetchIntervalMs?: number }
) {
  const refetchInterval = useConditionalRefetchInterval(options?.refetchIntervalMs ?? 10000);
  return useQuery({
    queryKey: queryKeys.ops.recentEvents(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.project_id) params.set("project_id", String(filters.project_id));
      if (filters.protocol_run_id) params.set("protocol_id", String(filters.protocol_run_id));
      if (filters.event_type) params.set("event_type", filters.event_type);
      if (filters.categories) {
        filters.categories.forEach((category) => {
          params.append("category", category);
        });
      }
      if (filters.limit) params.set("limit", String(filters.limit));
      const queryString = params.toString();
      const response = await apiClient.get<{ events: Event[] }>(
        `/events/recent${queryString ? `?${queryString}` : ""}`
      );
      return response.events;
    },
    refetchInterval,
  });
}

// Metrics Summary
export function useMetricsSummary(hours: number = 24) {
  return useQuery({
    queryKey: queryKeys.ops.metricsSummary(hours),
    queryFn: () => apiClient.get<MetricsSummary>(`/metrics/summary?hours=${hours}`),
    refetchInterval: 30000, // Refresh every 30s
  });
}
