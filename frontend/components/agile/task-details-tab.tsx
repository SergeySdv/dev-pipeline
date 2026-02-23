"use client";

import { useState } from "react";

import { Calendar, Plus,Tag, User, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AgileTask, AgileTaskCreate, Sprint } from "@/lib/api/types";

import { TaskForm } from "./task-form";

export interface TaskDetailsTabProps {
  formData: AgileTaskCreate;
  onFormChange: (data: AgileTaskCreate) => void;
  task?: AgileTask | null;
  sprints: Sprint[];
  isReadOnly?: boolean;
}

export function TaskDetailsTab({
  formData,
  onFormChange,
  task,
  sprints,
  isReadOnly = false,
}: TaskDetailsTabProps) {
  const [newLabel, setNewLabel] = useState("");

  const addLabel = () => {
    if (newLabel.trim() && !formData.labels?.includes(newLabel.trim())) {
      onFormChange({ ...formData, labels: [...(formData.labels || []), newLabel.trim()] });
      setNewLabel("");
    }
  };

  const removeLabel = (label: string) => {
    onFormChange({ ...formData, labels: formData.labels?.filter((l) => l !== label) || [] });
  };

  return (
    <div className="space-y-6">
      <TaskForm formData={formData} onFormChange={onFormChange} isReadOnly={isReadOnly} />

      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-2">
          <Label>Execution</Label>
          <Select
            value={formData.sprint_id?.toString() || "backlog"}
            onValueChange={(value) =>
              onFormChange({
                ...formData,
                sprint_id: value === "backlog" ? undefined : Number.parseInt(value),
              })
            }
            disabled={isReadOnly}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select execution" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="backlog">Execution Backlog</SelectItem>
              {sprints.map((sprint) => (
                <SelectItem key={sprint.id} value={sprint.id.toString()}>
                  {sprint.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {task && (
          <div className="space-y-2">
            <Label>Protocol Run</Label>
            <Input
              value={task.protocol_run_id ? `#${task.protocol_run_id}` : "Not linked"}
              disabled
            />
          </div>
        )}

        {task && (
          <div className="space-y-2">
            <Label>Step Run</Label>
            <Input value={task.step_run_id ? `#${task.step_run_id}` : "Not linked"} disabled />
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="story_points">Story Points</Label>
          <Select
            value={formData.story_points?.toString() || ""}
            onValueChange={(value) =>
              onFormChange({
                ...formData,
                story_points: value ? Number.parseInt(value) : undefined,
              })
            }
            disabled={isReadOnly}
          >
            <SelectTrigger>
              <SelectValue placeholder="Estimate" />
            </SelectTrigger>
            <SelectContent>
              {[1, 2, 3, 5, 8, 13, 21].map((points) => (
                <SelectItem key={points} value={points.toString()}>
                  {points} {points === 1 ? "point" : "points"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="assignee">Assignee</Label>
          <div className="relative">
            <User className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
            <Input
              id="assignee"
              value={formData.assignee}
              onChange={(e) => onFormChange({ ...formData, assignee: e.target.value })}
              placeholder="Assign to..."
              disabled={isReadOnly}
              className="pl-9"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="due_date">Due Date</Label>
          <div className="relative">
            <Calendar className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
            <Input
              id="due_date"
              type="date"
              value={formData.due_date}
              onChange={(e) => onFormChange({ ...formData, due_date: e.target.value })}
              disabled={isReadOnly}
              className="pl-9"
            />
          </div>
        </div>

        <div className="col-span-2 space-y-2">
          <Label>Labels</Label>
          <div className="mb-2 flex flex-wrap gap-2">
            {formData.labels?.map((label) => (
              <Badge key={label} variant="secondary" className="gap-1">
                <Tag className="h-3 w-3" />
                {label}
                {!isReadOnly && (
                  <button
                    onClick={() => removeLabel(label)}
                    className="hover:text-destructive ml-1"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </Badge>
            ))}
          </div>
          {!isReadOnly && (
            <div className="flex gap-2">
              <Input
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                placeholder="Add label..."
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addLabel())}
                className="flex-1"
              />
              <Button type="button" variant="outline" size="icon" onClick={addLabel}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
