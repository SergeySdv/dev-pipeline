"use client"

import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import type {
  AgileTask,
  AgileTaskCreate,
  AgileTaskUpdate,
  Sprint,
} from "@/lib/api/types"
import { taskTypeConfig, validateTaskForm } from "./task-form"
import { TaskDetailsTab } from "./task-details-tab"
import { TaskCriteriaTab } from "./task-criteria-tab"
import { TaskActivityTab } from "./task-activity-tab"

interface TaskModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  task?: AgileTask | null
  sprints: Sprint[]
  onSave: (data: AgileTaskCreate | AgileTaskUpdate) => Promise<void>
  mode: "create" | "edit" | "view"
}

const initialFormData: AgileTaskCreate = {
  title: "",
  description: "",
  task_type: "task",
  priority: "medium",
  board_status: "backlog",
  story_points: undefined,
  assignee: "",
  sprint_id: undefined,
  labels: [],
  acceptance_criteria: [],
  due_date: "",
}

export function TaskModal({ open, onOpenChange, task, sprints, onSave, mode }: TaskModalProps) {
  const [formData, setFormData] = useState<AgileTaskCreate>(initialFormData)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (task && (mode === "edit" || mode === "view")) {
      setFormData({
        title: task.title,
        description: task.description || "",
        task_type: task.task_type,
        priority: task.priority,
        board_status: task.board_status,
        story_points: task.story_points || undefined,
        assignee: task.assignee || "",
        sprint_id: task.sprint_id || undefined,
        labels: task.labels || [],
        acceptance_criteria: task.acceptance_criteria || [],
        due_date: task.due_date || "",
      })
    } else if (mode === "create") {
      setFormData(initialFormData)
    }
  }, [task, mode, open])

  const handleSave = async () => {
    const validation = validateTaskForm(formData)
    if (!validation.isValid) {
      return
    }
    
    setSaving(true)
    try {
      await onSave(formData)
      onOpenChange(false)
    } finally {
      setSaving(false)
    }
  }

  const isReadOnly = mode === "view"
  const TypeIcon = taskTypeConfig[formData.task_type || "task"].icon
  const validation = validateTaskForm(formData)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="3xl" className="max-h-[90vh] p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg bg-muted ${taskTypeConfig[formData.task_type || "task"].color}`}>
              <TypeIcon className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <DialogTitle className="text-xl">
                {mode === "create" ? "Create Task" : mode === "edit" ? "Edit Task" : task?.title}
              </DialogTitle>
              <DialogDescription>
                {mode === "create"
                  ? "Create a new task for your execution board"
                  : mode === "edit"
                    ? "Update task details and properties"
                    : `${taskTypeConfig[formData.task_type || "task"].label} #${task?.id}`}
              </DialogDescription>
            </div>
            {task && (
              <Badge variant="outline" className="font-mono">
                #{task.id}
              </Badge>
            )}
          </div>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh]">
          <Tabs defaultValue="details" className="w-full">
            <div className="px-6 pt-2">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="details">Details</TabsTrigger>
                <TabsTrigger value="criteria">Acceptance Criteria</TabsTrigger>
                <TabsTrigger value="activity">Activity</TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="details" className="px-6 py-4">
              <TaskDetailsTab
                formData={formData}
                onFormChange={setFormData}
                task={task}
                sprints={sprints}
                isReadOnly={isReadOnly}
              />
            </TabsContent>

            <TabsContent value="criteria" className="px-6 py-4">
              <TaskCriteriaTab
                formData={formData}
                onFormChange={setFormData}
                isReadOnly={isReadOnly}
              />
            </TabsContent>

            <TabsContent value="activity" className="px-6 py-4">
              <TaskActivityTab task={task} />
            </TabsContent>
          </Tabs>
        </ScrollArea>

        <DialogFooter className="px-6 py-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {isReadOnly ? "Close" : "Cancel"}
          </Button>
          {!isReadOnly && (
            <Button onClick={handleSave} disabled={saving || !validation.isValid}>
              {saving ? "Saving..." : mode === "create" ? "Create Task" : "Save Changes"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
