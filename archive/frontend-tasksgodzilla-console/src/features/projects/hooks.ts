import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export interface Project {
  id: number;
  name: string;
  git_url: string;
  local_path: string | null;
  base_branch: string;
  ci_provider: string | null;
  project_classification: string | null;
  default_models: Record<string, string> | null;
  secrets: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  policy_pack_key: string | null;
  policy_pack_version: string | null;
  policy_overrides: Record<string, unknown> | null;
  policy_repo_local_enabled: boolean | null;
  policy_effective_hash: string | null;
  policy_enforcement_mode: string | null;
}

export interface ProjectCreate {
  name: string;
  git_url: string;
  base_branch?: string;
  ci_provider?: string;
  project_classification?: string;
  default_models?: Record<string, string>;
}

export function useProjects() {
  return useQuery({
    queryKey: ['projects', 'list'],
    queryFn: () => apiClient.fetch<Project[]>('/projects'),
  });
}

export function useProject(id: number) {
  return useQuery({
    queryKey: ['projects', 'detail', id],
    queryFn: () => apiClient.fetch<Project>(`/projects/${id}`),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: ProjectCreate) => 
      apiClient.fetch<Project>('/projects', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', 'list'] });
    },
  });
}

export function useProjectOnboarding(id: number) {
  return useQuery({
    queryKey: ['projects', 'onboarding', id],
    queryFn: () => apiClient.fetch(`/projects/${id}/onboarding`),
  });
}

export function useStartProjectOnboarding(id: number) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => 
      apiClient.fetch(`/projects/${id}/onboarding/actions/start`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', 'onboarding', id] });
    },
  });
}

export function useProjectPolicy(id: number) {
  return useQuery({
    queryKey: ['projects', 'policy', id],
    queryFn: () => apiClient.fetch(`/projects/${id}/policy`),
  });
}

export function useUpdateProjectPolicy(id: number) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: any) => 
      apiClient.fetch(`/projects/${id}/policy`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', 'policy', id] });
      queryClient.invalidateQueries({ queryKey: ['projects', 'policyEffective', id] });
      queryClient.invalidateQueries({ queryKey: ['projects', 'policyFindings', id] });
    },
  });
}

export function useProjectClarifications(id: number, status?: string) {
  return useQuery({
    queryKey: ['projects', 'clarifications', id, { status }],
    queryFn: () => apiClient.fetch(`/projects/${id}/clarifications${status ? `?status=${status}` : ''}`),
  });
}

export function useAnswerProjectClarification(id: number) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ key, answer }: { key: string; answer: string }) => 
      apiClient.fetch(`/projects/${id}/clarifications/${key}`, {
        method: 'POST',
        body: JSON.stringify({ answer }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', 'clarifications', id] });
    },
  });
}

export function useProjectBranches(id: number) {
  return useQuery({
    queryKey: ['projects', 'branches', id],
    queryFn: () => apiClient.fetch(`/projects/${id}/branches`),
  });
}