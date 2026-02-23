"use client";

import { useState } from "react";

import { CheckSquare, Plus,X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { AgileTaskCreate } from "@/lib/api/types";

export interface TaskCriteriaTabProps {
  formData: AgileTaskCreate;
  onFormChange: (data: AgileTaskCreate) => void;
  isReadOnly?: boolean;
}

export function TaskCriteriaTab({
  formData,
  onFormChange,
  isReadOnly = false,
}: TaskCriteriaTabProps) {
  const [newCriteria, setNewCriteria] = useState("");

  const addCriteria = () => {
    if (newCriteria.trim()) {
      onFormChange({
        ...formData,
        acceptance_criteria: [...(formData.acceptance_criteria || []), newCriteria.trim()],
      });
      setNewCriteria("");
    }
  };

  const removeCriteria = (index: number) => {
    onFormChange({
      ...formData,
      acceptance_criteria: formData.acceptance_criteria?.filter((_, i) => i !== index) || [],
    });
  };

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        {formData.acceptance_criteria?.map((criteria, index) => (
          <div key={index} className="bg-muted/50 flex items-start gap-3 rounded-lg border p-3">
            <CheckSquare className="mt-0.5 h-4 w-4 text-green-500" />
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
          <div className="text-muted-foreground py-8 text-center">
            <CheckSquare className="mx-auto mb-2 h-8 w-8 opacity-50" />
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
          <Button
            type="button"
            variant="outline"
            onClick={addCriteria}
            className="self-end bg-transparent"
          >
            <Plus className="mr-2 h-4 w-4" />
            Add
          </Button>
        </div>
      )}
    </div>
  );
}
