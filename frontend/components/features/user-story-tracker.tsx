"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useProtocolSteps } from "@/lib/api/hooks/use-protocols";
import { LoadingState } from "@/components/ui/loading-state";
import { CheckCircle2, Circle, PlayCircle, XCircle, AlertTriangle, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StepRun, StepStatus } from "@/lib/api/types";

// =============================================================================
// Types
// =============================================================================

export interface UserStory {
  id: string;
  name: string;
  is_mvp: boolean;
  tasks: Task[];
  completed: number;
  total: number;
}

export interface Task {
  id: string;
  description: string;
  status: StepStatus;
}

export interface UserStoryTrackerProps {
  protocolRunId: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Gets the icon component for a task status
 */
function getTaskStatusIcon(status: StepStatus) {
  switch (status) {
    case "completed":
      return CheckCircle2;
    case "running":
      return PlayCircle;
    case "failed":
      return XCircle;
    case "blocked":
      return AlertTriangle;
    case "pending":
    case "needs_qa":
    case "cancelled":
    default:
      return Circle;
  }
}

/**
 * Gets the color class for a task status
 */
function getTaskStatusColor(status: StepStatus): string {
  switch (status) {
    case "completed":
      return "text-green-500";
    case "running":
      return "text-blue-500";
    case "failed":
      return "text-red-500";
    case "blocked":
      return "text-yellow-500";
    case "needs_qa":
      return "text-purple-500";
    case "pending":
    case "cancelled":
    default:
      return "text-muted-foreground";
  }
}

/**
 * Gets the badge variant for a task status
 */
function getTaskStatusBadgeVariant(status: StepStatus): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "completed":
      return "default";
    case "running":
      return "secondary";
    case "failed":
      return "destructive";
    case "blocked":
    case "needs_qa":
      return "outline";
    default:
      return "outline";
  }
}

/**
 * Formats a step name to extract user story information
 */
function extractUserStoryInfo(stepName: string): { storyId: string; storyName: string; isMvp: boolean } {
  // Pattern: "US1: ..." or "US1 - ..." or "User Story 1: ..."
  const usMatch = stepName.match(/(?:US|User Story)\s*(\d+)/i);
  
  if (usMatch) {
    const storyNum = usMatch[1];
    return {
      storyId: `US${storyNum}`,
      storyName: stepName.replace(/^(?:US|User Story)\s*\d+\s*[:-]\s*/i, ""),
      isMvp: storyNum === "1",
    };
  }
  
  // Fallback: use phase number or step type as grouping
  return {
    storyId: "other",
    storyName: stepName,
    isMvp: false,
  };
}

/**
 * Groups steps by user story and calculates progress
 */
function groupStepsByUserStory(steps: StepRun[] | undefined): UserStory[] {
  if (!steps || steps.length === 0) return [];
  
  const groups = new Map<string, UserStory>();
  
  for (const step of steps) {
    const info = extractUserStoryInfo(step.step_name);
    
    if (!groups.has(info.storyId)) {
      groups.set(info.storyId, {
        id: info.storyId,
        name: info.storyName,
        is_mvp: info.isMvp,
        tasks: [],
        completed: 0,
        total: 0,
      });
    }
    
    const story = groups.get(info.storyId)!;
    const task: Task = {
      id: String(step.id),
      description: step.summary || step.step_name,
      status: step.status,
    };
    
    story.tasks.push(task);
    story.total += 1;
    if (step.status === "completed") {
      story.completed += 1;
    }
  }
  
  // Sort: MVP first, then by completion progress
  return Array.from(groups.values()).sort((a, b) => {
    if (a.is_mvp && !b.is_mvp) return -1;
    if (!a.is_mvp && b.is_mvp) return 1;
    const progressA = a.total > 0 ? a.completed / a.total : 0;
    const progressB = b.total > 0 ? b.completed / b.total : 0;
    return progressB - progressA;
  });
}

/**
 * Calculate overall progress across all stories
 */
function calculateOverallProgress(stories: UserStory[]): { completed: number; total: number; percentage: number } {
  const completed = stories.reduce((sum, s) => sum + s.completed, 0);
  const total = stories.reduce((sum, s) => sum + s.total, 0);
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
  return { completed, total, percentage };
}

// =============================================================================
// Component
// =============================================================================

export function UserStoryTracker({ protocolRunId }: UserStoryTrackerProps) {
  const { data: steps, isLoading } = useProtocolSteps(Number(protocolRunId));
  
  const stories = useMemo(() => groupStepsByUserStory(steps), [steps]);
  const overallProgress = useMemo(() => calculateOverallProgress(stories), [stories]);
  
  if (isLoading) {
    return <LoadingState message="Loading user stories..." />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            User Story Progress
          </div>
          <Badge variant="secondary">
            {overallProgress.completed}/{overallProgress.total}
          </Badge>
        </CardTitle>
        {stories.length > 0 && (
          <div className="space-y-1">
            <Progress value={overallProgress.percentage} className="h-2" />
            <p className="text-xs text-muted-foreground text-right">
              {overallProgress.percentage}% complete
            </p>
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {stories.length === 0 ? (
          <div className="text-center text-sm text-muted-foreground py-4">
            No user stories found
          </div>
        ) : (
          stories.map((story) => (
            <div key={story.id} className="space-y-2">
              {/* Story Header */}
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-medium">{story.id}</h4>
                {story.is_mvp && (
                  <Badge variant="default" className="text-xs">
                    MVP
                  </Badge>
                )}
                <span className="text-xs text-muted-foreground ml-auto">
                  {story.completed}/{story.total} tasks
                </span>
              </div>
              
              {/* Story Progress Bar */}
              <Progress 
                value={story.total > 0 ? (story.completed / story.total) * 100 : 0} 
                className="h-1.5"
              />
              
              {/* Task List */}
              <div className="space-y-1.5 pl-2">
                {story.tasks.map((task) => {
                  const Icon = getTaskStatusIcon(task.status);
                  return (
                    <div
                      key={task.id}
                      className="flex items-center gap-2 text-sm"
                    >
                      <Icon className={cn("h-3.5 w-3.5", getTaskStatusColor(task.status))} />
                      <span className="flex-1 truncate">{task.description}</span>
                      <Badge 
                        variant={getTaskStatusBadgeVariant(task.status)} 
                        className="text-xs capitalize"
                      >
                        {task.status}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Summary Variant
// =============================================================================

export function UserStorySummary({ protocolRunId }: { protocolRunId: string }) {
  const { data: steps } = useProtocolSteps(Number(protocolRunId));
  
  const stories = useMemo(() => groupStepsByUserStory(steps), [steps]);
  const overallProgress = useMemo(() => calculateOverallProgress(stories), [stories]);
  
  const mvpStory = stories.find((s) => s.is_mvp);
  const mvpProgress = mvpStory && mvpStory.total > 0 
    ? Math.round((mvpStory.completed / mvpStory.total) * 100) 
    : 0;
  
  return (
    <Card>
      <CardHeader className="py-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Zap className="h-4 w-4" />
          Stories Overview
        </CardTitle>
      </CardHeader>
      <CardContent className="py-2 space-y-3">
        {/* Overall Progress */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Overall Progress</span>
            <span className="font-medium">{overallProgress.percentage}%</span>
          </div>
          <Progress value={overallProgress.percentage} className="h-2" />
        </div>
        
        {/* MVP Progress (if exists) */}
        {mvpStory && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1">
                <Badge variant="default" className="text-xs">MVP</Badge>
                <span className="text-muted-foreground">{mvpStory.id}</span>
              </div>
              <span className="font-medium">{mvpProgress}%</span>
            </div>
            <Progress value={mvpProgress} className="h-1.5" />
          </div>
        )}
        
        {/* Stories Summary */}
        <div className="flex flex-wrap gap-1.5">
          {stories.slice(0, 5).map((story) => {
            const progress = story.total > 0 
              ? Math.round((story.completed / story.total) * 100) 
              : 0;
            return (
              <Badge
                key={story.id}
                variant={progress === 100 ? "default" : "outline"}
                className="text-xs"
              >
                {story.id}: {progress}%
              </Badge>
            );
          })}
          {stories.length > 5 && (
            <Badge variant="secondary" className="text-xs">
              +{stories.length - 5} more
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
