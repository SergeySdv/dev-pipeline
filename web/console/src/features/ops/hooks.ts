import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export interface QueueStats {
  queue: string;
  queued: number;
  started: number;
  failed: number;
  total: number;
  healthy_percentage: number;
}

export interface QueueJob {
  id: string;
  job_type: string;
  status: string;
  enqueued_at: string;
  started_at?: string;
  worker_id?: string;
  queue: string;
}

export interface Event {
  id: string;
  timestamp: string;
  event_type: string;
  message: string;
  metadata?: Record<string, any>;
  project_id?: number;
  project_name?: string;
  protocol_run_id?: number;
  protocol_name?: string;
}

export interface EventFilters {
  project_id?: number;
  event_type?: string;
  kind?: string;
  limit?: number;
}

export function useQueues() {
  return useQuery({
    queryKey: ['ops', 'queueStats'],
    queryFn: () => apiClient.fetch<QueueStats[]>('/queues'),
    refetchInterval: 10000, // 10 seconds
  });
}

export function useQueueJobs(status?: string) {
  return useQuery({
    queryKey: ['ops', 'queueJobs', { status }],
    queryFn: () => apiClient.fetch<QueueJob[]>(`/queues/jobs${status ? `?status=${status}` : ''}`),
    refetchInterval: 5000, // 5 seconds
  });
}

export function useRecentEvents(filters: EventFilters = {}) {
  const queryParams = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      queryParams.append(key, String(value));
    }
  });

  return useQuery({
    queryKey: ['ops', 'recentEvents', filters],
    queryFn: () => apiClient.fetch<Event[]>(`/events${queryParams.toString() ? `?${queryParams.toString()}` : ''}`),
    refetchInterval: 10000, // 10 seconds
  });
}