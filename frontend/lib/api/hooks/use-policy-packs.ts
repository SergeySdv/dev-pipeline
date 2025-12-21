"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "../client"
import { queryKeys } from "../query-keys"
import type { PolicyPack, PolicyPackContent } from "../types"

// List Policy Packs
export function usePolicyPacks() {
  return useQuery({
    queryKey: queryKeys.policyPacks.list(),
    queryFn: () => apiClient.get<PolicyPack[]>("/policy_packs"),
  })
}

// Create/Update Policy Pack
export function useCreatePolicyPack() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      key: string
      version: string
      name: string
      description?: string
      status?: PolicyPack["status"]
      pack: PolicyPackContent
    }) => apiClient.post<PolicyPack>("/policy_packs", data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.policyPacks.list(),
      })
    },
  })
}
