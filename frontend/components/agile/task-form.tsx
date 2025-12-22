"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Bug,
  BookOpen,
  Zap,
  CheckSquare,
  Layers,
  AlertTriangle,
  ArrowUp,
  ArrowRight,
  ArrowDown,
} from "lucide-react"
import type {
  AgileTaskCreate,
  TaskType,
  TaskPriority,
  TaskBoardStatus,
} from "@/lib/api/types"

export const taskTypeConfig: Record<TaskType, { icon: typeof Bug; label: string; color: string }> = {
  bug: { icon: Bug, label: "Bug", color: "text-red-500" },
  story: { icon: BookOpen, label: "Story", color: "text-blue-500" },
  task: { icon: CheckSquare, label: "Task", color: "text-green-500" },
  spike: { icon: Zap, label: "Spike", color: "text-purple-500" },
  epic: { icon: Layers, label: "Epic", color: "text-amber-500" },
}

export const priorityConfig: Record<TaskPriority, { icon: typeof AlertTriangle; label: string; color: string }> = {
  critical: { icon: AlertTriangle, label: "Critical", color: "text-red-500" },
  high: { icon: ArrowUp, label: "High", color: "text-orange-500" },
  medium: { icon: ArrowRight, label: "Medium", color: "text-yellow-500" },
  low: { icon: ArrowDown, label: "Low", color: "text-blue-500" },
}

export const statusOptions: { value: TaskBoardStatus; label: string }[] = [
  { value: "backlog", label: "Backlog" },
  { value: "todo", label: "To Do" },
  { value: "in_progress", label: "In Progress" },
  { value: "review", label: "Review" },
  { value: "testing", label: "Testing" },
  { value: "done", label: "Done" },
]

export interface TaskFormProps {
  formData: AgileTaskCreate
  onFormChange: (data: AgileTaskCreate) => void
  isReadOnly?: boolean
}

export interface TaskFormValidationResult {
  isValid: boolean
  errors: Record<string, string>
}

export function validateTaskForm(formData: AgileTaskCreate): TaskFormValidationResult {
  const errors: Record<string, string> = {}
  
  if (!formData.title || !formData.title.trim()) {
    errors.title = "Title is required"
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  }
}

export function TaskForm({ formData, onFormChange, isReadOnly = false }: TaskFormProps) {
  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="col-span-2 space-y-2">
        <Label htmlFor="title">Title</Label>
        <Input
          id="title"
          value={formData.title}
          onChange={(e) => onFormChange({ ...formData, title: e.target.value })}
          placeholder="Enter task title"
          disabled={isReadOnly}
          className="font-medium"
        />
      </div>

      <div className="col-span-2 space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => onFormChange({ ...formData, description: e.target.value })}
          placeholder="Describe the task..."
          disabled={isReadOnly}
          rows={4}
        />
      </div>

      <div className="space-y-2">
        <Label>Type</Label>
        <Select
          value={formData.task_type}
          onValueChange={(value: TaskType) => onFormChange({ ...formData, task_type: value })}
          disabled={isReadOnly}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(taskTypeConfig).map(([key, config]) => {
              const Icon = config.icon
              return (
                <SelectItem key={key} value={key}>
                  <div className="flex items-center gap-2">
                    <Icon className={`h-4 w-4 ${config.color}`} />
                    {config.label}
                  </div>
                </SelectItem>
              )
            })}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Priority</Label>
        <Select
          value={formData.priority}
          onValueChange={(value: TaskPriority) => onFormChange({ ...formData, priority: value })}
          disabled={isReadOnly}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(priorityConfig).map(([key, config]) => {
              const Icon = config.icon
              return (
                <SelectItem key={key} value={key}>
                  <div className="flex items-center gap-2">
                    <Icon className={`h-4 w-4 ${config.color}`} />
                    {config.label}
                  </div>
                </SelectItem>
              )
            })}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Status</Label>
        <Select
          value={formData.board_status}
          onValueChange={(value: TaskBoardStatus) => onFormChange({ ...formData, board_status: value })}
          disabled={isReadOnly}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {statusOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
