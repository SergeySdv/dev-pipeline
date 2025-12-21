import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export interface CodexRun {
  run_id: string;
  job_type: string;
  run_kind: string;
  status: string;
  project_id?: number;
  protocol_run_id?: number;
  step_run_id?: number;
  attempt: number;
  worker_id?: string;
  queue: string;
  prompt_version?: string;
  params?: Record<string, any>;
  result?: Record<string, any>;
  error?: string;
  log_path?: string;
  cost_tokens?: number;
  cost_cents?: number;
  started_at?: string;
  finished_at?: string;
  created_at: string;
}

export interface RunFilters {
  job_type?: string;
  status?: string;
  run_kind?: string;
  project_id?: number;
  protocol_id?: number;
  step_id?: number;
  limit?: number;
}

export function useRuns(filters: RunFilters = {}) {
  const queryParams = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      queryParams.append(key, String(value));
    }
  });

  return useQuery({
    queryKey: ['runs', 'list', filters],
    queryFn: () => apiClient.fetch<CodexRun[]>(`/codex/runs${queryParams.toString() ? `?${queryParams.toString()}` : ''}`),
  });
}

export function useRun(runId: string) {
  return useQuery({
    queryKey: ['runs', 'detail', runId],
    queryFn: () => apiClient.fetch<CodexRun>(`/codex/runs/${runId}`),
  });
}

export function useRunLogs(runId: string) {
  return useQuery({
    queryKey: ['runs', 'logs', runId],
    queryFn: () => apiClient.fetch<string>(`/codex/runs/${runId}/logs`),
  });
}

export function useRunArtifacts(runId: string) {
  return useQuery({
    queryKey: ['runs', 'artifacts', runId],
    queryFn: () => apiClient.fetch<any[]>(`/codex/runs/${runId}/artifacts`),
  });
}

export function useArtifactContent(runId: string, artifactId: string) {
  return useQuery({
    queryKey: ['runs', 'artifactContent', runId, artifactId],
    queryFn: () => apiClient.fetch<string>(`/codex/runs/${runId}/artifacts/${artifactId}/content`),
  });
}