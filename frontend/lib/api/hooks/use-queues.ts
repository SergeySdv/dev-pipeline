"use client";

import { useQuery } from "@tanstack/react-query";

import { useVisibility } from "@/lib/hooks/use-visibility";

import { apiClient } from "../client";
import { queryKeys } from "../query-keys";
import type { QueueJob, QueueStats } from "../types";

function useConditionalRefetchInterval(baseInterval: number) {
  const isVisible = useVisibility();
  return isVisible ? baseInterval : false;
}

export function useQueueStats() {
  const refetchInterval = useConditionalRefetchInterval(10000);
  return useQuery({
    queryKey: queryKeys.ops.queueStats,
    queryFn: () => apiClient.get<QueueStats[]>("/queues/stats"),
    refetchInterval,
  });
}

export function useQueueJobs(status?: string) {
  const refetchInterval = useConditionalRefetchInterval(5000);
  return useQuery({
    queryKey: queryKeys.ops.queueJobs(status),
    queryFn: () =>
      apiClient.get<QueueJob[]>(
        `/queues/jobs${status ? `?status=${encodeURIComponent(status)}` : ""}`
      ),
    refetchInterval,
  });
}
