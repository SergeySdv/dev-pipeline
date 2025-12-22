"use client"

import { Clock, ArrowRight, CheckSquare, MessageSquare } from "lucide-react"
import type { AgileTask } from "@/lib/api/types"

export interface TaskActivityTabProps {
  task?: AgileTask | null
}

export function TaskActivityTab({ task }: TaskActivityTabProps) {
  if (!task) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>Activity will appear here after the task is created</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-full bg-muted">
          <Clock className="h-4 w-4 text-muted-foreground" />
        </div>
        <div>
          <p className="text-sm">Task created</p>
          <p className="text-xs text-muted-foreground">{new Date(task.created_at).toLocaleString()}</p>
        </div>
      </div>
      {task.started_at && (
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-full bg-blue-500/10">
            <ArrowRight className="h-4 w-4 text-blue-500" />
          </div>
          <div>
            <p className="text-sm">Work started</p>
            <p className="text-xs text-muted-foreground">{new Date(task.started_at).toLocaleString()}</p>
          </div>
        </div>
      )}
      {task.completed_at && (
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-full bg-green-500/10">
            <CheckSquare className="h-4 w-4 text-green-500" />
          </div>
          <div>
            <p className="text-sm">Task completed</p>
            <p className="text-xs text-muted-foreground">
              {new Date(task.completed_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
