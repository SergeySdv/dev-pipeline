import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export interface Step {
  id: number;
  protocol_run_id: number;
  step_index: number;
  step_name: string;
  step_type: string;
  status: string;
  retries: number;
  model?: string;
  engine_id?: string;
  policy?: Record<string, any>;
  runtime_state?: Record<string, any>;
  summary?: string;
  created_at: string;
  updated_at: string;
}

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
  cost_tokens?: number;
  cost_cents?: number;
  started_at?: string;
  finished_at?: string;
  created_at: string;
}

export interface PolicyFinding {
  code: string;
  message: string;
  severity: 'warning' | 'error';
  suggestion?: string;
  location?: string;
}

export function useStep(stepId: number) {
  return useQuery({
    queryKey: ['steps', 'detail', stepId],
    queryFn: () => apiClient.fetch<Step>(`/steps/${stepId}`),
  });
}

export function useStepRuns(stepId: number) {
  return useQuery({
    queryKey: ['steps', 'runs', stepId],
    queryFn: () => apiClient.fetch<CodexRun[]>(`/steps/${stepId}/runs`),
  });
}

export function useStepPolicyFindings(stepId: number) {
  return useQuery({
    queryKey: ['steps', 'policyFindings', stepId],
    queryFn: () => apiClient.fetch<PolicyFinding[]>(`/steps/${stepId}/policy/findings`),
  });
}