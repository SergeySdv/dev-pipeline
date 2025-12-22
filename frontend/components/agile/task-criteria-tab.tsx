"use client"

import { useState } from "react"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { CheckSquare, X, Plus } from "lucide-react"
import type { AgileTaskCreate } from "@/lib/api/types"

export interface TaskCriteriaTabProps {
  formData: AgileTaskCreate
  onFormChange: (data: AgileTaskCreate) => void
  isReadOnly?: boolean
}

export function TaskCriteriaTab({
  formData,
  onFormChange,
  isReadOnly = false,
}: TaskCriteriaTabProps) {
  const [newCriteria, setNewCriteria] = useState("")

  const addCriteria = () => {
    if (newCriteria.trim()) {
      onFormChange({
        ...formData,
        acceptance_criteria: [...(formData.acceptance_criteria || []), newCriteria.trim()],
      })
      setNewCriteria("")
    }
  }

  const removeCriteria = (index: number) => {
    onFormChange({
      ...formData,
      acceptance_criteria: formData.acceptance_criteria?.filter((_, i) => i !== index) || [],
    })
  }

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        {formData.acceptance_criteria?.map((criteria, index) => (
          <div key={index} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 border">
            <CheckSquare className="h-4 w-4 mt-0.5 text-green-500" />
            <span className="flex-1 text-sm">{criteria}</span>
            {!isReadOnly && (
              <button
                onClick={() => removeCriteria(index)}
                className="text-muted-foreground hover:text-destructive"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        ))}
        {formData.acceptance_criteria?.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <CheckSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No acceptance criteria defined</p>
          </div>
        )}
      </div>
      {!isReadOnly && (
        <div className="flex gap-2">
          <Textarea
            value={newCriteria}
            onChange={(e) => setNewCriteria(e.target.value)}
            placeholder="Add acceptance criteria..."
            rows={2}
            className="flex-1"
          />
          <Button type="button" variant="outline" onClick={addCriteria} className="self-end bg-transparent">
            <Plus className="h-4 w-4 mr-2" />
            Add
          </Button>
        </div>
      )}
    </div>
  )
}
