"use client"

import type React from "react"

import { useState, useCallback, useMemo } from "react"
import { useParams, useSearchParams } from "next/navigation"
import Link from "next/link"
import {
  useSprints,
  useTasks,
  useSprintMetrics,
  useUpdateTask,
  useCreateTask,
  useProjectProtocols,
  useCreateSprintFromProtocol,
  useProject,
} from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { LoadingState } from "@/components/ui/loading-state"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { TaskModal } from "@/components/agile/task-modal"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import {
  Calendar,
  Target,
  TrendingUp,
  CheckCircle2,
  Plus,
  ArrowLeft,
  Settings,
  Filter,
  Search,
  MoreHorizontal,
  Play,
  Pause,
  Check,
  RefreshCw,
  Download,
  Zap,
  AlertTriangle,
  Bug,
  BookOpen,
  CheckSquare,
  Layers,
  ArrowUp,
  ArrowRight,
  ArrowDown,
  GripVertical,
  Eye,
  Pencil,
  Trash2,
  User,
  X,
  LayoutGrid,
  List,
} from "lucide-react"
import type { AgileTask, AgileTaskCreate, AgileTaskUpdate, TaskBoardStatus, TaskType, TaskPriority } from "@/lib/api/types"

const taskTypeConfig: Record<TaskType, { icon: typeof Bug; color: string; bg: string; label: string }> = {
  bug: { icon: Bug, color: "text-red-500", bg: "bg-red-500/10", label: "Bug" },
  story: { icon: BookOpen, color: "text-blue-500", bg: "bg-blue-500/10", label: "Story" },
  task: { icon: CheckSquare, color: "text-green-500", bg: "bg-green-500/10", label: "Task" },
  spike: { icon: Zap, color: "text-purple-500", bg: "bg-purple-500/10", label: "Spike" },
  epic: { icon: Layers, color: "text-amber-500", bg: "bg-amber-500/10", label: "Epic" },
}

const priorityConfig: Record<TaskPriority, { icon: typeof AlertTriangle; color: string; label: string }> = {
  critical: { icon: AlertTriangle, color: "text-red-500", label: "Critical" },
  high: { icon: ArrowUp, color: "text-orange-500", label: "High" },
  medium: { icon: ArrowRight, color: "text-yellow-500", label: "Medium" },
  low: { icon: ArrowDown, color: "text-blue-400", label: "Low" },
}

const columns: { id: TaskBoardStatus; title: string; color: string; headerBg: string }[] = [
  { id: "backlog", title: "Backlog", color: "border-t-slate-500", headerBg: "bg-slate-500/10" },
  { id: "todo", title: "To Do", color: "border-t-blue-500", headerBg: "bg-blue-500/10" },
  { id: "in_progress", title: "In Progress", color: "border-t-amber-500", headerBg: "bg-amber-500/10" },
  { id: "review", title: "Review", color: "border-t-purple-500", headerBg: "bg-purple-500/10" },
  { id: "testing", title: "Testing", color: "border-t-cyan-500", headerBg: "bg-cyan-500/10" },
  { id: "done", title: "Done", color: "border-t-green-500", headerBg: "bg-green-500/10" },
]

export default function ProjectExecutionPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const projectId = Number.parseInt(params.id as string)

  const { data: project } = useProject(projectId)
  const { data: sprints, isLoading: sprintsLoading } = useSprints(projectId)
  const sprintParam = searchParams.get("sprint")
  const initialExecution =
    sprintParam && (sprintParam === "all" || sprintParam === "backlog" || !Number.isNaN(Number.parseInt(sprintParam, 10)))
      ? sprintParam
      : null
  const [selectedExecution, setSelectedExecution] = useState<string | null>(initialExecution)
  const activeSprint = sprints?.find((s) => s.status === "active")
  const resolvedExecution = selectedExecution ?? (activeSprint ? activeSprint.id.toString() : null)
  const selectedSprintId =
    resolvedExecution && resolvedExecution !== "all" && resolvedExecution !== "backlog"
      ? Number.parseInt(resolvedExecution, 10)
      : null
  const { data: tasks, isLoading: tasksLoading, mutate: mutateTasks } = useTasks(projectId)
  const { data: metrics } = useSprintMetrics(selectedSprintId)
  const { data: projectProtocols = [] } = useProjectProtocols(projectId)
  const updateTask = useUpdateTask()
  const createTask = useCreateTask()
  const createSprintFromProtocol = useCreateSprintFromProtocol(projectId)

  // UI State
  const [createSprintOpen, setCreateSprintOpen] = useState(false)
  const [sprintSettingsOpen, setSprintSettingsOpen] = useState(false)
  const [selectedProtocolId, setSelectedProtocolId] = useState("")
  const [sprintName, setSprintName] = useState("")
  const [sprintStart, setSprintStart] = useState("")
  const [sprintEnd, setSprintEnd] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [filterType, setFilterType] = useState<string>("all")
  const [filterPriority, setFilterPriority] = useState<string>("all")
  const [filterAssignee, setFilterAssignee] = useState<string>("all")
  const [viewMode, setViewMode] = useState<"board" | "list">("board")
  const [showBacklog, setShowBacklog] = useState(true)

  // Task Modal State
  const [taskModalOpen, setTaskModalOpen] = useState(false)
  const [taskModalMode, setTaskModalMode] = useState<"create" | "edit" | "view">("create")
  const [selectedTask, setSelectedTask] = useState<AgileTask | null>(null)

  // Drag & Drop State
  const [draggedTask, setDraggedTask] = useState<AgileTask | null>(null)
  const [dragOverColumn, setDragOverColumn] = useState<TaskBoardStatus | null>(null)

  const currentSprint =
    selectedSprintId != null
      ? sprints?.find((s) => s.id === selectedSprintId)
      : resolvedExecution
        ? undefined
        : activeSprint

  // Filter tasks
  const scopedTasks = useMemo(() => {
    const allTasks = tasks || []
    if (resolvedExecution === "backlog") {
      return allTasks.filter((task) => !task.sprint_id)
    }
    if (!resolvedExecution || resolvedExecution === "all") {
      return allTasks
    }
    return allTasks.filter((task) => task.sprint_id === selectedSprintId)
  }, [tasks, resolvedExecution, selectedSprintId])

  const filteredTasks = useMemo(() => {
    return scopedTasks.filter((task) => {
      if (searchQuery && !task.title.toLowerCase().includes(searchQuery.toLowerCase())) return false
      if (filterType !== "all" && task.task_type !== filterType) return false
      if (filterPriority !== "all" && task.priority !== filterPriority) return false
      if (filterAssignee !== "all" && task.assignee !== filterAssignee) return false
      return true
    })
  }, [scopedTasks, searchQuery, filterType, filterPriority, filterAssignee])

  const showBacklogColumn = showBacklog || resolvedExecution === "backlog"
  const visibleColumns = showBacklogColumn ? columns : columns.filter((c) => c.id !== "backlog")

  const getTasksByColumn = useCallback(
    (status: TaskBoardStatus) => {
      return filteredTasks.filter((task) => task.board_status === status)
    },
    [filteredTasks],
  )

  // Handlers
  const handleDragStart = (e: React.DragEvent, task: AgileTask) => {
    setDraggedTask(task)
    e.dataTransfer.effectAllowed = "move"
    e.dataTransfer.setData("text/plain", task.id.toString())
  }

  const handleDragOver = (e: React.DragEvent, status: TaskBoardStatus) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "move"
    setDragOverColumn(status)
  }

  const handleDragLeave = () => setDragOverColumn(null)

  const handleDrop = async (e: React.DragEvent, status: TaskBoardStatus) => {
    e.preventDefault()
    setDragOverColumn(null)
    if (draggedTask && draggedTask.board_status !== status) {
      try {
        await updateTask.mutateAsync(draggedTask.id, { board_status: status })
        mutateTasks()
        toast.success(`Task moved to ${columns.find((c) => c.id === status)?.title}`)
      } catch {
        toast.error("Failed to move task")
      }
    }
    setDraggedTask(null)
  }

  const handleDragEnd = () => {
    setDraggedTask(null)
    setDragOverColumn(null)
  }

  const handleTaskCreate = async (data: AgileTaskCreate) => {
    const sprintId =
      resolvedExecution === "backlog" ? undefined : selectedSprintId ?? data.sprint_id
    await createTask.mutateAsync(projectId, { ...data, sprint_id: sprintId })
    mutateTasks()
    toast.success("Task created")
  }

  const handleTaskEdit = async (taskId: number, data: AgileTaskUpdate) => {
    await updateTask.mutateAsync(taskId, data)
    mutateTasks()
    toast.success("Task updated")
  }

  const handleCreateSprint = async () => {
    if (!selectedProtocolId) {
      toast.error("Select a protocol run to create an execution sprint.")
      return
    }
    try {
      await createSprintFromProtocol.mutateAsync(Number.parseInt(selectedProtocolId, 10), {
        sprint_name: sprintName || undefined,
        start_date: sprintStart || undefined,
        end_date: sprintEnd || undefined,
      })
      toast.success("Execution sprint created")
      setCreateSprintOpen(false)
      setSelectedProtocolId("")
      setSprintName("")
      setSprintStart("")
      setSprintEnd("")
    } catch {
      toast.error("Failed to create execution sprint")
    }
  }

  const handleSprintAction = async (action: string) => {
    toast.success(`Execution ${action}`)
    setSprintSettingsOpen(false)
  }

  const openCreateModal = () => {
    setSelectedTask(null)
    setTaskModalMode("create")
    setTaskModalOpen(true)
  }

  const openViewModal = (task: AgileTask) => {
    setSelectedTask(task)
    setTaskModalMode("view")
    setTaskModalOpen(true)
  }

  const openEditModal = (task: AgileTask) => {
    setSelectedTask(task)
    setTaskModalMode("edit")
    setTaskModalOpen(true)
  }

  const handleModalSave = async (data: AgileTaskCreate | AgileTaskUpdate) => {
    if (taskModalMode === "create") {
      await handleTaskCreate(data as AgileTaskCreate)
    } else if (taskModalMode === "edit" && selectedTask) {
      await handleTaskEdit(selectedTask.id, data as AgileTaskUpdate)
    }
  }

  const getColumnStats = (status: TaskBoardStatus) => {
    const columnTasks = getTasksByColumn(status)
    const totalPoints = columnTasks.reduce((acc, t) => acc + (t.story_points || 0), 0)
    return { count: columnTasks.length, points: totalPoints }
  }

  // Get unique assignees for filter
  const assignees = [...new Set(tasks?.map((t) => t.assignee).filter(Boolean) || [])]

  const completionPercent = metrics ? Math.round((metrics.completed_points / metrics.total_points) * 100) || 0 : 0

  if (sprintsLoading) {
    return <LoadingState message="Loading execution board..." />
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <div className="border-b bg-card/50 shrink-0">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="sm" asChild>
                <Link href={`/projects/${projectId}`}>
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Project
                </Link>
              </Button>
              <Separator orientation="vertical" className="h-6" />
              <div>
                <h1 className="text-xl font-bold">{project?.name || `Project #${projectId}`}</h1>
                <p className="text-sm text-muted-foreground">Execution Board - Advanced View</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowBacklog(!showBacklog)}>
                {showBacklog ? "Hide Backlog" : "Show Backlog"}
              </Button>
              <div className="flex items-center border rounded-md">
                <Button
                  variant={viewMode === "board" ? "secondary" : "ghost"}
                  size="sm"
                  className="rounded-r-none"
                  onClick={() => setViewMode("board")}
                >
                  <LayoutGrid className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === "list" ? "secondary" : "ghost"}
                  size="sm"
                  className="rounded-l-none"
                  onClick={() => setViewMode("list")}
                >
                  <List className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Execution Selector & Stats */}
      <div className="border-b bg-muted/30 shrink-0">
        <div className="px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Select value={resolvedExecution || ""} onValueChange={setSelectedExecution}>
                <SelectTrigger className="w-[280px]">
                  <SelectValue placeholder="Select execution" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Executions</SelectItem>
                  <SelectItem value="backlog">Execution Backlog</SelectItem>
                  {sprints?.map((sprint) => (
                    <SelectItem key={sprint.id} value={sprint.id.toString()}>
                      <div className="flex items-center gap-2">
                        {sprint.name}
                        <Badge
                          variant={sprint.status === "active" ? "default" : "secondary"}
                          className="text-[10px] h-4"
                        >
                          {sprint.status}
                        </Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {currentSprint && (
                <>
                  <Separator orientation="vertical" className="h-5" />
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Calendar className="h-3.5 w-3.5" />
                      <span>
                        {currentSprint.start_date} - {currentSprint.end_date}
                      </span>
                    </div>
                    <Separator orientation="vertical" className="h-4" />
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Target className="h-3.5 w-3.5" />
                      <span>{currentSprint.velocity_planned || 0} pts planned</span>
                    </div>
                    <Separator orientation="vertical" className="h-4" />
                    <div className="flex items-center gap-1.5">
                      <TrendingUp className="h-3.5 w-3.5 text-green-500" />
                      <span className="font-medium">{completionPercent}%</span>
                      <span className="text-muted-foreground">complete</span>
                    </div>
                    <Separator orientation="vertical" className="h-4" />
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>
                        {metrics?.completed_tasks || 0}/{metrics?.total_tasks || 0} tasks
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => setCreateSprintOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create from Protocol
              </Button>
              {currentSprint && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button size="sm" variant="outline">
                      <Settings className="h-4 w-4 mr-2" />
                      Execution Actions
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {currentSprint.status === "planning" && (
                      <DropdownMenuItem onClick={() => handleSprintAction("started")}>
                        <Play className="h-4 w-4 mr-2" />
                        Start Execution
                      </DropdownMenuItem>
                    )}
                    {currentSprint.status === "active" && (
                      <>
                        <DropdownMenuItem onClick={() => handleSprintAction("paused")}>
                          <Pause className="h-4 w-4 mr-2" />
                          Pause Execution
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleSprintAction("completed")}>
                          <Check className="h-4 w-4 mr-2" />
                          Complete Execution
                        </DropdownMenuItem>
                      </>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => setSprintSettingsOpen(true)}>
                      <Settings className="h-4 w-4 mr-2" />
                      Execution Settings
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Refresh Board
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <Download className="h-4 w-4 mr-2" />
                      Export Execution
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>

          {/* Execution Goal */}
          {currentSprint?.goal && (
            <div className="mt-3 p-2 bg-background/50 rounded border flex items-center gap-2">
              <Target className="h-4 w-4 text-primary shrink-0" />
              <span className="text-sm font-medium">Execution Goal:</span>
              <span className="text-sm text-muted-foreground">{currentSprint.goal}</span>
            </div>
          )}
        </div>
      </div>

      {/* Filters & Search */}
      <div className="border-b bg-background shrink-0">
        <div className="px-6 py-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search tasks..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-8 w-[200px]"
                />
              </div>
              <Separator orientation="vertical" className="h-5" />
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <Select value={filterType} onValueChange={setFilterType}>
                  <SelectTrigger className="h-8 w-[120px]">
                    <SelectValue placeholder="Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    {Object.entries(taskTypeConfig).map(([key, config]) => (
                      <SelectItem key={key} value={key}>
                        {config.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={filterPriority} onValueChange={setFilterPriority}>
                  <SelectTrigger className="h-8 w-[120px]">
                    <SelectValue placeholder="Priority" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Priority</SelectItem>
                    {Object.entries(priorityConfig).map(([key, config]) => (
                      <SelectItem key={key} value={key}>
                        {config.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={filterAssignee} onValueChange={setFilterAssignee}>
                  <SelectTrigger className="h-8 w-[140px]">
                    <SelectValue placeholder="Assignee" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Assignees</SelectItem>
                    {assignees.map((assignee) => (
                      <SelectItem key={assignee} value={assignee!}>
                        {assignee}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {(filterType !== "all" || filterPriority !== "all" || filterAssignee !== "all" || searchQuery) && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8"
                  onClick={() => {
                    setFilterType("all")
                    setFilterPriority("all")
                    setFilterAssignee("all")
                    setSearchQuery("")
                  }}
                >
                  <X className="h-3 w-3 mr-1" />
                  Clear filters
                </Button>
              )}
            </div>

            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span>{filteredTasks.length} tasks</span>
              <Separator orientation="vertical" className="h-4" />
              <span>{filteredTasks.reduce((acc, t) => acc + (t.story_points || 0), 0)} points</span>
              <Separator orientation="vertical" className="h-4" />
              <Button size="sm" onClick={openCreateModal}>
                <Plus className="h-4 w-4 mr-2" />
                Add Task
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Board */}
      <div className="flex-1 overflow-hidden">
        {tasksLoading ? (
          <LoadingState message="Loading tasks..." />
        ) : viewMode === "board" ? (
          <ScrollArea className="h-full">
            <div className="p-6">
              <div className="flex gap-4" style={{ minWidth: visibleColumns.length * 300 }}>
                {visibleColumns.map((column) => {
                  const stats = getColumnStats(column.id)
                  const columnTasks = getTasksByColumn(column.id)
                  const isDropTarget = dragOverColumn === column.id

                  return (
                    <div
                      key={column.id}
                      className={cn(
                        "flex-1 min-w-[280px] max-w-[350px] rounded-lg border border-t-4 bg-muted/30 transition-all flex flex-col",
                        column.color,
                        isDropTarget && "ring-2 ring-primary ring-offset-2 bg-primary/5",
                      )}
                      onDragOver={(e) => handleDragOver(e, column.id)}
                      onDragLeave={handleDragLeave}
                      onDrop={(e) => handleDrop(e, column.id)}
                    >
                      <div className={cn("p-3 border-b", column.headerBg)}>
                        <div className="flex items-center justify-between">
                          <h4 className="font-semibold text-sm">{column.title}</h4>
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="text-xs h-5 px-1.5">
                              {stats.count}
                            </Badge>
                            {stats.points > 0 && (
                              <Badge variant="outline" className="text-xs h-5 px-1.5">
                                {stats.points}pt
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>

                      <ScrollArea className="flex-1 min-h-[400px] max-h-[calc(100vh-320px)]">
                        <div className="p-2 space-y-2">
                          {columnTasks.map((task) => {
                            const TypeIcon = taskTypeConfig[task.task_type].icon
                            const PriorityIcon = priorityConfig[task.priority].icon
                            const isDragging = draggedTask?.id === task.id

                            return (
                              <div
                                key={task.id}
                                draggable
                                onDragStart={(e) => handleDragStart(e, task)}
                                onDragEnd={handleDragEnd}
                                className={cn(
                                  "group p-3 rounded-md border bg-card shadow-sm cursor-grab active:cursor-grabbing transition-all hover:shadow-md hover:border-primary/50",
                                  isDragging && "opacity-50 scale-95",
                                )}
                              >
                                <div className="flex items-start gap-2">
                                  <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 mt-0.5 shrink-0" />
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between gap-2 mb-2">
                                      <div className="flex items-center gap-1.5">
                                        <div className={cn("p-1 rounded", taskTypeConfig[task.task_type].bg)}>
                                          <TypeIcon className={cn("h-3 w-3", taskTypeConfig[task.task_type].color)} />
                                        </div>
                                        <span className="text-xs font-mono text-muted-foreground">#{task.id}</span>
                                        {task.protocol_run_id && (
                                          <span className="text-[10px] text-muted-foreground">
                                            PR#{task.protocol_run_id}
                                          </span>
                                        )}
                                        {task.step_run_id && (
                                          <span className="text-[10px] text-muted-foreground">S#{task.step_run_id}</span>
                                        )}
                                      </div>
                                      <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                          <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6 opacity-0 group-hover:opacity-100"
                                          >
                                            <MoreHorizontal className="h-3 w-3" />
                                          </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                          <DropdownMenuItem onClick={() => openViewModal(task)}>
                                            <Eye className="h-4 w-4 mr-2" />
                                            View Details
                                          </DropdownMenuItem>
                                          <DropdownMenuItem onClick={() => openEditModal(task)}>
                                            <Pencil className="h-4 w-4 mr-2" />
                                            Edit
                                          </DropdownMenuItem>
                                          <DropdownMenuSeparator />
                                          <DropdownMenuItem className="text-destructive">
                                            <Trash2 className="h-4 w-4 mr-2" />
                                            Delete
                                          </DropdownMenuItem>
                                        </DropdownMenuContent>
                                      </DropdownMenu>
                                    </div>

                                    <p
                                      className="text-sm font-medium line-clamp-2 mb-2 cursor-pointer hover:text-primary"
                                      onClick={() => openViewModal(task)}
                                    >
                                      {task.title}
                                    </p>

                                    <div className="flex flex-wrap gap-1 mb-2">
                                      {task.labels.slice(0, 2).map((label) => (
                                        <Badge key={label} variant="outline" className="text-[10px] h-4 px-1">
                                          {label}
                                        </Badge>
                                      ))}
                                      {task.labels.length > 2 && (
                                        <Badge variant="outline" className="text-[10px] h-4 px-1">
                                          +{task.labels.length - 2}
                                        </Badge>
                                      )}
                                    </div>

                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center gap-2">
                                        <PriorityIcon className={cn("h-3 w-3", priorityConfig[task.priority].color)} />
                                        {task.story_points && (
                                          <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
                                            {task.story_points}pt
                                          </Badge>
                                        )}
                                      </div>
                                      {task.assignee && (
                                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                          <div className="h-5 w-5 rounded-full bg-primary/10 flex items-center justify-center">
                                            <User className="h-3 w-3" />
                                          </div>
                                          <span className="truncate max-w-[60px]">{task.assignee}</span>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )
                          })}

                          {columnTasks.length === 0 && (
                            <div className="py-8 text-center text-muted-foreground">
                              <p className="text-xs">No tasks</p>
                              <Button variant="ghost" size="sm" className="mt-2" onClick={openCreateModal}>
                                <Plus className="h-3 w-3 mr-1" />
                                Add task
                              </Button>
                            </div>
                          )}
                        </div>
                      </ScrollArea>
                    </div>
                  )
                })}
              </div>
            </div>
            <ScrollBar orientation="horizontal" />
          </ScrollArea>
        ) : (
          /* List View */
          <ScrollArea className="h-full">
            <div className="p-6">
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr className="text-left text-sm">
                      <th className="p-3 font-medium">Task</th>
                      <th className="p-3 font-medium w-[100px]">Type</th>
                      <th className="p-3 font-medium w-[100px]">Priority</th>
                      <th className="p-3 font-medium w-[120px]">Status</th>
                      <th className="p-3 font-medium w-[80px]">Points</th>
                      <th className="p-3 font-medium w-[120px]">Assignee</th>
                      <th className="p-3 font-medium w-[50px]"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTasks.map((task) => {
                      const TypeIcon = taskTypeConfig[task.task_type].icon
                      const PriorityIcon = priorityConfig[task.priority].icon
                      return (
                        <tr key={task.id} className="border-t hover:bg-muted/30">
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono text-muted-foreground">#{task.id}</span>
                              {task.protocol_run_id && (
                                <span className="text-[10px] text-muted-foreground">PR#{task.protocol_run_id}</span>
                              )}
                              {task.step_run_id && (
                                <span className="text-[10px] text-muted-foreground">S#{task.step_run_id}</span>
                              )}
                              <span
                                className="font-medium cursor-pointer hover:text-primary"
                                onClick={() => openViewModal(task)}
                              >
                                {task.title}
                              </span>
                            </div>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1.5">
                              <TypeIcon className={cn("h-4 w-4", taskTypeConfig[task.task_type].color)} />
                              <span className="text-sm capitalize">{task.task_type}</span>
                            </div>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1.5">
                              <PriorityIcon className={cn("h-4 w-4", priorityConfig[task.priority].color)} />
                              <span className="text-sm capitalize">{task.priority}</span>
                            </div>
                          </td>
                          <td className="p-3">
                            <Badge variant="outline" className="text-xs">
                              {task.board_status.replace("_", " ")}
                            </Badge>
                          </td>
                          <td className="p-3 text-sm">{task.story_points || "-"}</td>
                          <td className="p-3 text-sm text-muted-foreground">{task.assignee || "-"}</td>
                          <td className="p-3">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => openViewModal(task)}>View</DropdownMenuItem>
                                <DropdownMenuItem onClick={() => openEditModal(task)}>Edit</DropdownMenuItem>
                                <DropdownMenuItem className="text-destructive">Delete</DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </ScrollArea>
        )}
      </div>

      {/* Create Execution Dialog */}
      <Dialog open={createSprintOpen} onOpenChange={setCreateSprintOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Execution from Protocol</DialogTitle>
            <DialogDescription>Generate a new execution sprint from an existing protocol run.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Protocol Run</Label>
              <Select value={selectedProtocolId} onValueChange={setSelectedProtocolId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select protocol run" />
                </SelectTrigger>
                <SelectContent>
                  {projectProtocols.length === 0 && (
                    <SelectItem value="none" disabled>
                      No protocol runs found
                    </SelectItem>
                  )}
                  {projectProtocols.map((protocol) => (
                    <SelectItem key={protocol.id} value={protocol.id.toString()}>
                      {protocol.protocol_name} #{protocol.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="sprint-name">Execution Name (optional)</Label>
              <Input
                id="sprint-name"
                value={sprintName}
                onChange={(event) => setSprintName(event.target.value)}
                placeholder="Protocol-based execution"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="start-date">Start Date</Label>
                <Input
                  id="start-date"
                  type="date"
                  value={sprintStart}
                  onChange={(event) => setSprintStart(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end-date">End Date</Label>
                <Input
                  id="end-date"
                  type="date"
                  value={sprintEnd}
                  onChange={(event) => setSprintEnd(event.target.value)}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateSprintOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateSprint} disabled={!selectedProtocolId || selectedProtocolId === "none"}>
              Create Execution
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Execution Settings Dialog */}
      <Dialog open={sprintSettingsOpen} onOpenChange={setSprintSettingsOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Execution Settings</DialogTitle>
            <DialogDescription>Configure execution settings and preferences.</DialogDescription>
          </DialogHeader>
          {currentSprint && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Execution Name</Label>
                <Input defaultValue={currentSprint.name} />
              </div>
              <div className="space-y-2">
                <Label>Goal</Label>
                <Textarea defaultValue={currentSprint.goal || ""} rows={2} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Start Date</Label>
                  <Input type="date" defaultValue={currentSprint.start_date || ""} />
                </div>
                <div className="space-y-2">
                  <Label>End Date</Label>
                  <Input type="date" defaultValue={currentSprint.end_date || ""} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Planned Velocity</Label>
                  <Input type="number" defaultValue={currentSprint.velocity_planned || ""} />
                </div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select defaultValue={currentSprint.status}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="planning">Planning</SelectItem>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSprintSettingsOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                toast.success("Execution settings saved")
                setSprintSettingsOpen(false)
              }}
            >
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Task Modal */}
      <TaskModal
        open={taskModalOpen}
        onOpenChange={setTaskModalOpen}
        task={selectedTask}
        sprints={sprints || []}
        onSave={handleModalSave}
        mode={taskModalMode}
      />
    </div>
  )
}
