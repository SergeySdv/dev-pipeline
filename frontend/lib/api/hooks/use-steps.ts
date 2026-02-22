"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "../client"
import { queryKeys } from "../query-keys"
import type { CodexRun, PolicyFinding, ActionResponse, StepArtifact, ArtifactContent, StepQuality } from "../types"

// Step Runs
export function useStepRuns(stepId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.steps.runs(stepId!),
    queryFn: () => apiClient.get<CodexRun[]>(`/steps/${stepId}/runs`),
    enabled: !!stepId,
  })
}

// Step Policy Findings
export function useStepPolicyFindings(stepId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.steps.policyFindings(stepId!),
    queryFn: () => apiClient.get<PolicyFinding[]>(`/steps/${stepId}/policy/findings`),
    enabled: !!stepId,
  })
}

// Step Actions
export function useStepAction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      stepId,
      action,
    }: {
      stepId: number
      protocolId: number
      action: "execute" | "qa"
    }) => apiClient.post<ActionResponse>(`/steps/${stepId}/actions/${action}`),
    onSuccess: (_, { stepId, protocolId }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.steps.runs(stepId),
      })
      queryClient.invalidateQueries({
        queryKey: queryKeys.protocols.steps(protocolId),
      })
      queryClient.invalidateQueries({
        queryKey: queryKeys.protocols.events(protocolId),
      })
    },
  })
}

// Step Artifacts
export function useStepArtifacts(stepId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.steps.artifacts(stepId!),
    queryFn: () => apiClient.get<StepArtifact[]>(`/steps/${stepId}/artifacts`),
    enabled: !!stepId,
  })
}

export function useStepArtifactContent(stepId: number | undefined, artifactId: number | undefined) {
  return useQuery({
    queryKey: [...queryKeys.steps.artifacts(stepId!), "content", artifactId],
    queryFn: () => apiClient.get<ArtifactContent>(`/steps/${stepId}/artifacts/${artifactId}/content`),
    enabled: !!stepId && !!artifactId,
  })
}

export function useStepArtifactDownloadUrl(stepId: number, artifactId: number) {
  const config = apiClient.getConfig()
  return `${config.baseUrl}/steps/${stepId}/artifacts/${artifactId}/download`
}

// Step Quality
export function useStepQuality(stepId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.steps.quality(stepId!),
    queryFn: () => apiClient.get<StepQuality>(`/steps/${stepId}/quality`),
    enabled: !!stepId,
  })
}

export function useAssignStepAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      stepId,
      agentId,
    }: {
      stepId: number
      protocolId: number
      agentId: string
    }) =>
      apiClient.post<ActionResponse>(`/steps/${stepId}/actions/assign_agent`, {
        agent_id: agentId,
      }),
    onSuccess: (_, { stepId, protocolId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.protocols.steps(protocolId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.steps.runs(stepId) })
    },
  })
}
