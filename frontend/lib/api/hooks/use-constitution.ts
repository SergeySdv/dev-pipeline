"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "../client"
import { queryKeys } from "../query-keys"

// =============================================================================
// Types
// =============================================================================

/**
 * Constitution content response from the API
 */
export interface ConstitutionResponse {
  content: string
  hash?: string | null
  version?: string | null
}

/**
 * Constitution update request payload
 */
export interface ConstitutionUpdateRequest {
  content: string
}

/**
 * Constitution validation result
 */
export interface ConstitutionValidation {
  valid: boolean
  errors: string[]
  warnings: string[]
}

/**
 * Constitution metadata without full content
 */
export interface ConstitutionMetadata {
  hash: string | null
  version: string | null
  line_count: number
  character_count: number
  last_modified: string | null
}

// =============================================================================
// Query Keys
// =============================================================================

export const constitutionKeys = {
  all: ["constitution"] as const,
  detail: (projectId: number) => [...constitutionKeys.all, projectId] as const,
  metadata: (projectId: number) => [...constitutionKeys.all, "metadata", projectId] as const,
  validation: (projectId: number) => [...constitutionKeys.all, "validation", projectId] as const,
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch constitution content for a project
 */
export function useConstitution(projectId: number | undefined) {
  return useQuery({
    queryKey: constitutionKeys.detail(projectId!),
    queryFn: () => apiClient.get<ConstitutionResponse>(`/speckit/constitution/${projectId}`),
    enabled: !!projectId,
  })
}

/**
 * Fetch constitution metadata only (without full content)
 * Useful for showing status without loading the entire file
 */
export function useConstitutionMetadata(projectId: number | undefined) {
  return useQuery({
    queryKey: constitutionKeys.metadata(projectId!),
    queryFn: async () => {
      const response = await apiClient.get<ConstitutionResponse>(`/speckit/constitution/${projectId}`)
      return {
        hash: response.hash ?? null,
        version: response.version ?? null,
        line_count: response.content.split("\n").length,
        character_count: response.content.length,
        last_modified: null, // API doesn't currently return this
      } as ConstitutionMetadata
    },
    enabled: !!projectId,
  })
}

/**
 * Save/update constitution for a project
 */
export function useSaveConstitution() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ projectId, content }: { projectId: number; content: string }) =>
      apiClient.put<ConstitutionResponse>(`/speckit/constitution/${projectId}`, { content }),
    onSuccess: (_, variables) => {
      // Invalidate all constitution-related queries
      queryClient.invalidateQueries({ queryKey: constitutionKeys.detail(variables.projectId) })
      queryClient.invalidateQueries({ queryKey: constitutionKeys.metadata(variables.projectId) })
      // Also invalidate speckit status since constitution affects it
      queryClient.invalidateQueries({ queryKey: queryKeys.speckit.status(variables.projectId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.speckit.constitution(variables.projectId) })
    },
  })
}

/**
 * Reset constitution to defaults (empty content)
 */
export function useResetConstitution() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (projectId: number) =>
      apiClient.put<ConstitutionResponse>(`/speckit/constitution/${projectId}`, { content: "" }),
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({ queryKey: constitutionKeys.detail(projectId) })
      queryClient.invalidateQueries({ queryKey: constitutionKeys.metadata(projectId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.speckit.status(projectId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.speckit.constitution(projectId) })
    },
  })
}

/**
 * Validate constitution content without saving
 * Performs client-side validation and optionally server-side validation
 */
export function useValidateConstitution() {
  return useMutation({
    mutationFn: async ({ 
      projectId, 
      content 
    }: { 
      projectId: number
      content: string 
    }): Promise<ConstitutionValidation> => {
      // Client-side validation
      const errors: string[] = []
      const warnings: string[] = []

      // Check for empty content
      if (!content.trim()) {
        return { valid: true, errors: [], warnings: ["Constitution is empty, defaults will be used"] }
      }

      // Check for reasonable size limits
      if (content.length > 100000) {
        errors.push("Constitution is too large (max 100KB)")
      }

      // Check for basic structure
      const lines = content.split("\n")
      const hasHeaders = lines.some(line => line.startsWith("#"))
      
      if (!hasHeaders) {
        warnings.push("Consider adding headers (# Title) to organize the constitution")
      }

      // Check for common sections
      const content_lower = content.toLowerCase()
      const recommendedSections = ["coding", "architecture", "testing"]
      const missingSections = recommendedSections.filter(
        section => !content_lower.includes(section)
      )
      
      if (missingSections.length > 0 && hasHeaders) {
        warnings.push(`Consider adding sections for: ${missingSections.join(", ")}`)
      }

      // If we have server-side validation endpoint, call it
      // Currently we only do client-side validation
      // const serverValidation = await apiClient.post<ConstitutionValidation>(
      //   `/speckit/constitution/${projectId}/validate`, 
      //   { content }
      // )

      return {
        valid: errors.length === 0,
        errors,
        warnings,
      }
    },
  })
}

/**
 * Hook to check if constitution exists and has content
 */
export function useHasConstitution(projectId: number | undefined) {
  const { data, isLoading, error } = useConstitutionMetadata(projectId)
  
  return {
    hasConstitution: !!data && data.character_count > 0,
    isLoading,
    error,
    metadata: data,
  }
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Client-side validation for constitution content
 * Can be used without a mutation for immediate feedback
 */
export function validateConstitutionContent(content: string): ConstitutionValidation {
  const errors: string[] = []
  const warnings: string[] = []

  if (!content.trim()) {
    return { valid: true, errors: [], warnings: ["Constitution is empty"] }
  }

  if (content.length > 100000) {
    errors.push("Constitution exceeds maximum size (100KB)")
  }

  const lines = content.split("\n")
  const hasHeaders = lines.some(line => line.startsWith("#"))
  
  if (!hasHeaders) {
    warnings.push("Consider adding headers to organize content")
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  }
}

/**
 * Get word count from constitution content
 */
export function getConstitutionWordCount(content: string): number {
  if (!content.trim()) return 0
  return content.trim().split(/\s+/).length
}

/**
 * Estimate reading time in minutes
 */
export function estimateReadingTime(content: string): number {
  const wordCount = getConstitutionWordCount(content)
  // Average reading speed: ~200 words per minute
  return Math.max(1, Math.ceil(wordCount / 200))
}
