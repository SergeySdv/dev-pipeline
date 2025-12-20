"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "../client"
import { queryKeys } from "../query-keys"
import type {
  Agent,
  AgentDefaults,
  AgentHealth,
  AgentMetrics,
  AgentPromptTemplate,
  AgentPromptUpdate,
  AgentProjectOverrides,
  AgentUpdate,
} from "../types"

// List Agents
export function useAgents(projectId?: number) {
  const suffix = projectId ? `?project_id=${projectId}` : ""
  return useQuery({
    queryKey: queryKeys.agents.list(projectId),
    queryFn: () => apiClient.get<Agent[]>(`/agents${suffix}`),
    enabled: projectId !== undefined ? Number.isFinite(projectId) : true,
  })
}

// Get Agent by ID
export function useAgent(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.agents.detail(id!),
    queryFn: () => apiClient.get<Agent>(`/agents/${id}`),
    enabled: !!id,
  })
}

export function useAgentDefaults(projectId?: number) {
  const suffix = projectId ? `?project_id=${projectId}` : ""
  return useQuery({
    queryKey: queryKeys.agents.defaults(projectId),
    queryFn: () => apiClient.get<AgentDefaults>(`/agents/defaults${suffix}`),
  })
}

export function useAgentPrompts(projectId?: number) {
  const suffix = projectId ? `?project_id=${projectId}` : ""
  return useQuery({
    queryKey: queryKeys.agents.prompts(projectId),
    queryFn: () => apiClient.get<AgentPromptTemplate[]>(`/agents/prompts${suffix}`),
  })
}

export function useAgentHealth(projectId?: number) {
  const suffix = projectId ? `?project_id=${projectId}` : ""
  return useQuery({
    queryKey: queryKeys.agents.health(projectId),
    queryFn: () => apiClient.get<AgentHealth[]>(`/agents/health${suffix}`),
  })
}

export function useAgentMetrics(projectId?: number) {
  const suffix = projectId ? `?project_id=${projectId}` : ""
  return useQuery({
    queryKey: queryKeys.agents.metrics(projectId),
    queryFn: () => apiClient.get<AgentMetrics[]>(`/agents/metrics${suffix}`),
  })
}

export function useProjectAgentOverrides(projectId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.agents.project(projectId || 0),
    queryFn: () => apiClient.get<AgentProjectOverrides>(`/agents/projects/${projectId}`),
    enabled: !!projectId,
  })
}

export function useUpdateAgentConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      agentId,
      data,
      projectId,
    }: {
      agentId: string
      data: AgentUpdate
      projectId?: number
    }) => {
      if (projectId) {
        return apiClient.put<Agent>(`/agents/projects/${projectId}/agents/${agentId}`, data)
      }
      return apiClient.put<Agent>(`/agents/${agentId}/config`, data)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list(variables.projectId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.detail(variables.agentId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.project(variables.projectId || 0) })
    },
  })
}

export function useUpdateAgentDefaults() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, defaults }: { projectId?: number; defaults: AgentDefaults }) => {
      const suffix = projectId ? `?project_id=${projectId}` : ""
      return apiClient.put<AgentDefaults>(`/agents/defaults${suffix}`, defaults)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.defaults(variables.projectId) })
    },
  })
}

export function useUpdateAgentPrompt() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectId,
      promptId,
      data,
    }: {
      projectId?: number
      promptId: string
      data: AgentPromptUpdate
    }) => {
      if (projectId) {
        return apiClient.put<AgentPromptTemplate>(`/agents/projects/${projectId}/prompts/${promptId}`, data)
      }
      return apiClient.put<AgentPromptTemplate>(`/agents/prompts/${promptId}`, data)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.prompts(variables.projectId) })
    },
  })
}

export function useUpdateProjectAgentOverrides() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, overrides }: { projectId: number; overrides: AgentProjectOverrides }) =>
      apiClient.put<AgentProjectOverrides>(`/agents/projects/${projectId}`, overrides),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.project(variables.projectId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list(variables.projectId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.defaults(variables.projectId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.prompts(variables.projectId) })
    },
  })
}
