"use client";

import { useMemo,useState } from "react";
import Link from "next/link";

import {
  BarChart3,
  Calendar,
  Check,
  CheckCircle2,
  ExternalLink,
  Link2,
  ListTodo,
  Maximize2,
  Pencil,
  Plus,
  RefreshCw,
  Target,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";

import { SprintBoard } from "@/components/agile/sprint-board";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingState } from "@/components/ui/loading-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BurndownChart } from "@/components/visualizations/burndown-chart";
import { VelocityTrendChart } from "@/components/visualizations/velocity-trend-chart";
import {
  useCompleteSprint,
  useCreateSprintFromProtocol,
  useCreateTask,
  useDeleteSprint,
  useDeleteTask,
  useLinkProtocolToSprint,
  useProjectProtocols,
  useSprintMetrics,
  useSprints,
  useSyncSprintFromProtocol,
  useTasks,
  useUpdateSprint,
  useUpdateTask,
} from "@/lib/api";
import type {
  AgileTaskCreate,
  AgileTaskUpdate,
  SprintUpdate,
  TaskBoardStatus,
} from "@/lib/api/types";

interface SprintTabProps {
  projectId: number;
}

export function SprintTab({ projectId }: SprintTabProps) {
  const { data: sprints, isLoading: sprintsLoading } = useSprints(projectId);
  const [selectedExecution, setSelectedExecution] = useState<string | null>(null);
  const activeSprint = sprints?.find((s) => s.status === "active");
  const resolvedExecution = selectedExecution || (activeSprint ? activeSprint.id.toString() : null);
  const selectedSprintId =
    resolvedExecution && resolvedExecution !== "all" && resolvedExecution !== "backlog"
      ? Number.parseInt(resolvedExecution, 10)
      : null;
  const { data: tasks, isLoading: tasksLoading, mutate: mutateTasks } = useTasks(projectId);
  const { data: metrics } = useSprintMetrics(selectedSprintId);
  const updateTask = useUpdateTask();
  const createTask = useCreateTask();
  const deleteTask = useDeleteTask();
  const { data: projectProtocols = [] } = useProjectProtocols(projectId);
  const createSprintFromProtocol = useCreateSprintFromProtocol(projectId);
  const updateSprint = useUpdateSprint();
  const deleteSprint = useDeleteSprint();
  const completeSprint = useCompleteSprint();
  const linkProtocol = useLinkProtocolToSprint();
  const syncFromProtocol = useSyncSprintFromProtocol();
  const [createSprintOpen, setCreateSprintOpen] = useState(false);
  const [editSprintOpen, setEditSprintOpen] = useState(false);
  const [linkProtocolOpen, setLinkProtocolOpen] = useState(false);
  const [selectedProtocolId, setSelectedProtocolId] = useState("");
  const [linkProtocolId, setLinkProtocolId] = useState("");
  const [sprintName, setSprintName] = useState("");
  const [sprintStart, setSprintStart] = useState("");
  const [sprintEnd, setSprintEnd] = useState("");
  const [editName, setEditName] = useState("");
  const [editGoal, setEditGoal] = useState("");
  const [editStart, setEditStart] = useState("");
  const [editEnd, setEditEnd] = useState("");

  const currentSprint =
    selectedSprintId != null
      ? sprints?.find((s) => s.id === selectedSprintId)
      : resolvedExecution
        ? undefined
        : activeSprint;

  const handleTaskUpdate = async (taskId: number, data: { board_status: TaskBoardStatus }) => {
    await updateTask.mutateAsync(taskId, data);
    mutateTasks();
  };

  const handleTaskCreate = async (data: AgileTaskCreate) => {
    const sprintId =
      resolvedExecution === "backlog" ? undefined : (selectedSprintId ?? data.sprint_id);
    await createTask.mutateAsync(projectId, { ...data, sprint_id: sprintId });
    mutateTasks();
    toast.success("Task created");
  };

  const handleTaskEdit = async (taskId: number, data: AgileTaskUpdate) => {
    await updateTask.mutateAsync(taskId, data);
    mutateTasks();
    toast.success("Task updated");
  };

  const handleTaskDelete = async (taskId: number) => {
    await deleteTask.mutateAsync(taskId);
    mutateTasks();
    toast.success("Task deleted");
  };

  const handleCreateSprint = async () => {
    if (!selectedProtocolId) {
      toast.error("Select a protocol run to create an execution sprint.");
      return;
    }
    try {
      await createSprintFromProtocol.mutateAsync(Number.parseInt(selectedProtocolId, 10), {
        sprint_name: sprintName || undefined,
        start_date: sprintStart || undefined,
        end_date: sprintEnd || undefined,
      });
      toast.success("Execution sprint created");
      setCreateSprintOpen(false);
      setSelectedProtocolId("");
      setSprintName("");
      setSprintStart("");
      setSprintEnd("");
    } catch {
      toast.error("Failed to create execution sprint");
    }
  };

  const handleEditSprint = async () => {
    if (!selectedSprintId) return;
    try {
      const data: SprintUpdate = {};
      if (editName) data.name = editName;
      if (editGoal) data.goal = editGoal;
      if (editStart) data.start_date = editStart;
      if (editEnd) data.end_date = editEnd;
      await updateSprint.mutateAsync(selectedSprintId, data);
      toast.success("Sprint updated");
      setEditSprintOpen(false);
    } catch {
      toast.error("Failed to update sprint");
    }
  };

  const handleDeleteSprint = async () => {
    if (!selectedSprintId) return;
    if (!confirm("Are you sure you want to delete this sprint?")) return;
    try {
      await deleteSprint.mutateAsync(selectedSprintId, projectId);
      toast.success("Sprint deleted");
      setSelectedExecution(null);
    } catch {
      toast.error("Failed to delete sprint");
    }
  };

  const handleCompleteSprint = async () => {
    if (!selectedSprintId) return;
    try {
      await completeSprint.mutateAsync(selectedSprintId, projectId);
      toast.success("Sprint completed");
    } catch {
      toast.error("Failed to complete sprint");
    }
  };

  const handleLinkProtocol = async () => {
    if (!selectedSprintId || !linkProtocolId) return;
    try {
      await linkProtocol.mutateAsync(selectedSprintId, Number.parseInt(linkProtocolId, 10));
      toast.success("Protocol linked to sprint");
      setLinkProtocolOpen(false);
      setLinkProtocolId("");
    } catch {
      toast.error("Failed to link protocol");
    }
  };

  const handleSyncFromProtocol = async () => {
    if (!selectedSprintId) return;
    try {
      await syncFromProtocol.mutateAsync(selectedSprintId, projectId);
      toast.success("Tasks synced from protocol");
      mutateTasks();
    } catch {
      toast.error("Failed to sync from protocol");
    }
  };

  const openEditDialog = () => {
    if (currentSprint) {
      setEditName(currentSprint.name);
      setEditGoal(currentSprint.goal || "");
      setEditStart(currentSprint.start_date || "");
      setEditEnd(currentSprint.end_date || "");
      setEditSprintOpen(true);
    }
  };

  const scopedTasks = useMemo(() => {
    const allTasks = tasks || [];
    if (resolvedExecution === "backlog") {
      return allTasks.filter((task) => !task.sprint_id);
    }
    if (!resolvedExecution || resolvedExecution === "all") {
      return allTasks;
    }
    return allTasks.filter((task) => task.sprint_id === selectedSprintId);
  }, [tasks, resolvedExecution, selectedSprintId]);
  const completionPercent = metrics
    ? Math.round((metrics.completed_points / metrics.total_points) * 100) || 0
    : 0;

  if (sprintsLoading) {
    return <LoadingState message="Loading execution..." />;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Select value={resolvedExecution || ""} onValueChange={setSelectedExecution}>
            <SelectTrigger className="h-9 w-[240px]">
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
                      className="h-4 text-[10px]"
                    >
                      {sprint.status}
                    </Badge>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {currentSprint && (
            <div className="text-muted-foreground flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {currentSprint.start_date} - {currentSprint.end_date}
              </div>
              <Separator orientation="vertical" className="h-4" />
              <div className="flex items-center gap-1">
                <Target className="h-3 w-3" />
                {currentSprint.velocity_planned} pts
              </div>
              <Separator orientation="vertical" className="h-4" />
              <div className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3 text-green-500" />
                {completionPercent}%
              </div>
              <Separator orientation="vertical" className="h-4" />
              <div className="flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                {metrics?.completed_tasks || 0}/{metrics?.total_tasks || 0}
              </div>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {currentSprint && currentSprint.status === "active" && (
            <>
              <Button size="sm" variant="ghost" onClick={openEditDialog} title="Edit sprint">
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleCompleteSprint}
                title="Complete sprint"
              >
                <Check className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setLinkProtocolOpen(true)}
                title="Link protocol"
              >
                <Link2 className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleSyncFromProtocol}
                title="Sync tasks from protocol"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleDeleteSprint}
                title="Delete sprint"
                className="text-destructive hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </>
          )}
          <Button size="sm" variant="outline" onClick={() => setCreateSprintOpen(true)}>
            <Plus className="mr-1 h-4 w-4" />
            Create from Protocol
          </Button>
          <Button size="sm" variant="default" asChild>
            <Link href={`/projects/${projectId}/execution`}>
              <Maximize2 className="mr-1 h-4 w-4" />
              Full Execution
              <ExternalLink className="ml-1 h-3 w-3" />
            </Link>
          </Button>
        </div>
      </div>

      {currentSprint?.goal && (
        <div className="bg-muted/50 flex items-center gap-2 rounded border p-2 text-sm">
          <Target className="text-primary h-4 w-4 shrink-0" />
          <span className="font-medium">Execution Goal:</span>
          <span className="text-muted-foreground">{currentSprint.goal}</span>
        </div>
      )}

      {/* Execution Board */}
      <Tabs defaultValue="board" className="space-y-4">
        <TabsList className="h-8">
          <TabsTrigger value="board" className="h-7 gap-1.5 text-xs">
            <ListTodo className="h-3.5 w-3.5" />
            Board
          </TabsTrigger>
          <TabsTrigger value="burndown" className="h-7 gap-1.5 text-xs">
            <BarChart3 className="h-3.5 w-3.5" />
            Execution Burndown
          </TabsTrigger>
          <TabsTrigger value="velocity" className="h-7 gap-1.5 text-xs">
            <TrendingUp className="h-3.5 w-3.5" />
            Velocity
          </TabsTrigger>
        </TabsList>

        <TabsContent value="board">
          {tasksLoading ? (
            <LoadingState message="Loading tasks..." />
          ) : (
            <SprintBoard
              tasks={scopedTasks}
              sprints={sprints || []}
              onTaskUpdate={handleTaskUpdate}
              onTaskCreate={handleTaskCreate}
              onTaskEdit={handleTaskEdit}
              onTaskDelete={handleTaskDelete}
              showBacklog={
                !selectedExecution || selectedExecution === "all" || selectedExecution === "backlog"
              }
            />
          )}
        </TabsContent>

        <TabsContent value="burndown">
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-sm">Execution Burndown</CardTitle>
            </CardHeader>
            <CardContent>
              {metrics?.burndown ? (
                <BurndownChart data={metrics.burndown} />
              ) : (
                <BurndownChart data={[]} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="velocity">
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-sm">Velocity Trend</CardTitle>
            </CardHeader>
            <CardContent>
              {metrics?.velocity_trend ? (
                <VelocityTrendChart values={metrics.velocity_trend} />
              ) : (
                <VelocityTrendChart values={[]} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Edit Sprint Dialog */}
      <Dialog open={editSprintOpen} onOpenChange={setEditSprintOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Sprint</DialogTitle>
            <DialogDescription>Update sprint details.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Sprint Name</Label>
              <Input
                id="edit-name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-goal">Goal</Label>
              <Input
                id="edit-goal"
                value={editGoal}
                onChange={(e) => setEditGoal(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-start">Start Date</Label>
                <Input
                  id="edit-start"
                  type="date"
                  value={editStart}
                  onChange={(e) => setEditStart(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-end">End Date</Label>
                <Input
                  id="edit-end"
                  type="date"
                  value={editEnd}
                  onChange={(e) => setEditEnd(e.target.value)}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditSprintOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleEditSprint}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Link Protocol Dialog */}
      <Dialog open={linkProtocolOpen} onOpenChange={setLinkProtocolOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Link Protocol to Sprint</DialogTitle>
            <DialogDescription>Connect an existing protocol run to sync tasks.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Protocol Run</Label>
              <Select value={linkProtocolId} onValueChange={setLinkProtocolId}>
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLinkProtocolOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleLinkProtocol}
              disabled={!linkProtocolId || linkProtocolId === "none"}
            >
              Link Protocol
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Execution Dialog */}
      <Dialog open={createSprintOpen} onOpenChange={setCreateSprintOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Execution from Protocol</DialogTitle>
            <DialogDescription>
              Generate a new execution sprint from an existing protocol run.
            </DialogDescription>
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
            <Button
              onClick={handleCreateSprint}
              disabled={!selectedProtocolId || selectedProtocolId === "none"}
            >
              Create Execution
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
