"use client"

import { useState, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { Badge } from "@/components/ui/badge"
import { Save, RotateCcw, FileText, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { useConstitution, useSaveConstitution } from "@/lib/api"

// =============================================================================
// Types
// =============================================================================

export interface ConstitutionEditorProps {
  projectId: number
  className?: string
  onSaveSuccess?: () => void
  onSaveError?: (error: Error) => void
}

export interface ConstitutionData {
  content: string
  hash?: string | null
  version?: string | null
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Validates constitution content for basic structure
 */
export function validateConstitution(content: string): { valid: boolean; errors: string[] } {
  const errors: string[] = []
  
  if (!content.trim()) {
    return { valid: true, errors: [] } // Empty is valid (will use defaults)
  }
  
  // Check for basic markdown structure
  const lines = content.split("\n")
  const hasHeaders = lines.some(line => line.startsWith("#"))
  
  if (!hasHeaders) {
    errors.push("Constitution should contain at least one header (# Title)")
  }
  
  return { valid: errors.length === 0, errors }
}

/**
 * Truncates content for preview
 */
export function truncatePreview(content: string, maxLength: number = 200): string {
  if (content.length <= maxLength) return content
  return content.slice(0, maxLength) + "..."
}

// =============================================================================
// Component
// =============================================================================

export function ConstitutionEditor({
  projectId,
  className,
  onSaveSuccess,
  onSaveError,
}: ConstitutionEditorProps) {
  const { data, isLoading, error } = useConstitution(projectId)
  const saveMutation = useSaveConstitution()
  
  const [editedContent, setEditedContent] = useState<string>("")
  const [isEditing, setIsEditing] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  // Initialize edited content when data loads
  const content = data?.content ?? ""
  
  const handleStartEdit = useCallback(() => {
    setEditedContent(content)
    setIsEditing(true)
    setLocalError(null)
  }, [content])

  const handleCancelEdit = useCallback(() => {
    setEditedContent("")
    setIsEditing(false)
    setLocalError(null)
  }, [])

  const handleSave = useCallback(async () => {
    const validation = validateConstitution(editedContent)
    if (!validation.valid) {
      setLocalError(validation.errors.join(", "))
      return
    }

    try {
      await saveMutation.mutateAsync({ projectId, content: editedContent })
      setIsEditing(false)
      setEditedContent("")
      setLocalError(null)
      onSaveSuccess?.()
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to save constitution")
      setLocalError(error.message)
      onSaveError?.(error)
    }
  }, [editedContent, projectId, saveMutation, onSaveSuccess, onSaveError])

  const handleReset = useCallback(async () => {
    try {
      await saveMutation.mutateAsync({ projectId, content: "" })
      setLocalError(null)
      setIsEditing(false)
      onSaveSuccess?.()
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to reset constitution")
      setLocalError(error.message)
      onSaveError?.(error)
    }
  }, [projectId, saveMutation, onSaveSuccess, onSaveError])

  if (isLoading) {
    return <LoadingState message="Loading constitution..." />
  }

  if (error) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Error loading constitution"
        description={error instanceof Error ? error.message : "An unknown error occurred"}
      />
    )
  }

  const validation = isEditing ? validateConstitution(editedContent) : { valid: true, errors: [] }
  const hasChanges = isEditing && editedContent !== content

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Constitution
            </CardTitle>
            <CardDescription>
              Define project-specific guidelines, coding standards, and preferences
            </CardDescription>
          </div>
          {data?.content && !isEditing && (
            <Badge variant="secondary" className="text-xs">
              {data.content.split("\n").length} lines
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {(localError || saveMutation.error) && (
          <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{localError || (saveMutation.error instanceof Error ? saveMutation.error.message : "An error occurred")}</span>
          </div>
        )}

        {!validation.valid && (
          <div className="rounded-md bg-yellow-500/10 p-3 text-sm text-yellow-600 dark:text-yellow-400">
            {validation.errors.join(", ")}
          </div>
        )}

        {isEditing ? (
          <div className="space-y-4">
            <Textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              placeholder="# Project Constitution&#10;&#10;Define your project's coding standards, architectural guidelines, and preferences here...&#10;&#10;## Coding Standards&#10;- Use TypeScript strict mode&#10;- Prefer functional components over class components&#10;&#10;## Architecture&#10;- Follow hexagonal architecture principles&#10;- Keep business logic separate from infrastructure"
              className="min-h-[400px] font-mono text-sm"
            />
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                {editedContent.length} characters • {editedContent.split("\n").length} lines
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={handleCancelEdit}
                  disabled={saveMutation.isPending}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={saveMutation.isPending || !hasChanges}
                >
                  {saveMutation.isPending ? (
                    "Saving..."
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-1" />
                      Save Changes
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {content ? (
              <div className="rounded-md border bg-muted/30 p-4">
                <pre className="whitespace-pre-wrap font-mono text-sm overflow-auto max-h-[400px]">
                  {content}
                </pre>
              </div>
            ) : (
              <div className="rounded-md border border-dashed p-8 text-center">
                <FileText className="h-10 w-10 mx-auto text-muted-foreground mb-2" />
                <p className="text-muted-foreground">
                  No constitution defined yet.
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Click "Edit" to add project-specific guidelines.
                </p>
              </div>
            )}
            <div className="flex items-center justify-end gap-2">
              {content && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleReset}
                  disabled={saveMutation.isPending}
                  className="text-muted-foreground"
                >
                  <RotateCcw className="h-4 w-4 mr-1" />
                  Reset
                </Button>
              )}
              <Button onClick={handleStartEdit} disabled={saveMutation.isPending}>
                {content ? "Edit" : "Create Constitution"}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
