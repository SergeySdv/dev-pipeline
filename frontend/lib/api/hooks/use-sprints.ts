import useSWR, { mutate } from "swr"
import { apiClient } from "../client"
import { queryKeys } from "../query-keys"
import type { Sprint, SprintCreate, AgileTask, AgileTaskCreate, AgileTaskUpdate, SprintMetrics } from "../types"

// Mock sprint data
const mockSprints: Sprint[] = [
  {
    id: 1,
    project_id: 1,
    name: "Sprint 1 - Foundation",
    goal: "Set up core infrastructure and authentication",
    status: "completed",
    start_date: "2024-01-01",
    end_date: "2024-01-14",
    velocity_planned: 34,
    velocity_actual: 32,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-14T00:00:00Z",
  },
  {
    id: 2,
    project_id: 1,
    name: "Sprint 2 - User Features",
    goal: "Implement user dashboard and profile management",
    status: "active",
    start_date: "2024-01-15",
    end_date: "2024-01-28",
    velocity_planned: 40,
    velocity_actual: null,
    created_at: "2024-01-15T00:00:00Z",
    updated_at: "2024-01-20T00:00:00Z",
  },
  {
    id: 3,
    project_id: 1,
    name: "Sprint 3 - API Integration",
    goal: "Build REST API endpoints and external integrations",
    status: "planning",
    start_date: "2024-01-29",
    end_date: "2024-02-11",
    velocity_planned: 38,
    velocity_actual: null,
    created_at: "2024-01-20T00:00:00Z",
    updated_at: "2024-01-20T00:00:00Z",
  },
]

const mockTasks: AgileTask[] = [
  {
    id: 1,
    project_id: 1,
    sprint_id: 2,
    protocol_run_id: 1,
    step_run_id: null,
    title: "Implement user authentication flow",
    description: "Set up OAuth2 authentication with Google and GitHub providers",
    task_type: "story",
    priority: "high",
    board_status: "done",
    story_points: 8,
    assignee: "alice@example.com",
    reporter: "bob@example.com",
    labels: ["auth", "security"],
    acceptance_criteria: [
      "Users can sign in with Google",
      "Users can sign in with GitHub",
      "Session persists across refreshes",
    ],
    blocked_by: null,
    blocks: [2],
    due_date: "2024-01-20",
    started_at: "2024-01-16T09:00:00Z",
    completed_at: "2024-01-19T17:00:00Z",
    created_at: "2024-01-15T00:00:00Z",
    updated_at: "2024-01-19T17:00:00Z",
  },
  {
    id: 2,
    project_id: 1,
    sprint_id: 2,
    protocol_run_id: 1,
    step_run_id: null,
    title: "Build user dashboard UI",
    description: "Create responsive dashboard with key metrics and recent activity",
    task_type: "story",
    priority: "high",
    board_status: "review",
    story_points: 5,
    assignee: "charlie@example.com",
    reporter: "bob@example.com",
    labels: ["ui", "dashboard"],
    acceptance_criteria: ["Dashboard shows user stats", "Recent activity feed", "Responsive on mobile"],
    blocked_by: [1],
    blocks: null,
    due_date: "2024-01-22",
    started_at: "2024-01-20T09:00:00Z",
    completed_at: null,
    created_at: "2024-01-15T00:00:00Z",
    updated_at: "2024-01-21T10:00:00Z",
  },
  {
    id: 3,
    project_id: 1,
    sprint_id: 2,
    protocol_run_id: null,
    step_run_id: null,
    title: "Fix login redirect loop",
    description: "Users are experiencing redirect loops after successful login",
    task_type: "bug",
    priority: "critical",
    board_status: "in_progress",
    story_points: 3,
    assignee: "alice@example.com",
    reporter: "support@example.com",
    labels: ["bug", "auth", "urgent"],
    acceptance_criteria: ["No redirect loops", "Users land on dashboard after login"],
    blocked_by: null,
    blocks: null,
    due_date: "2024-01-21",
    started_at: "2024-01-21T08:00:00Z",
    completed_at: null,
    created_at: "2024-01-20T14:00:00Z",
    updated_at: "2024-01-21T08:00:00Z",
  },
  {
    id: 4,
    project_id: 1,
    sprint_id: 2,
    protocol_run_id: null,
    step_run_id: null,
    title: "Add profile settings page",
    description: "Allow users to update their profile information and preferences",
    task_type: "story",
    priority: "medium",
    board_status: "todo",
    story_points: 5,
    assignee: "david@example.com",
    reporter: "bob@example.com",
    labels: ["ui", "profile"],
    acceptance_criteria: ["Edit name and avatar", "Change email preferences", "Update password"],
    blocked_by: null,
    blocks: null,
    due_date: "2024-01-25",
    started_at: null,
    completed_at: null,
    created_at: "2024-01-15T00:00:00Z",
    updated_at: "2024-01-15T00:00:00Z",
  },
  {
    id: 5,
    project_id: 1,
    sprint_id: 2,
    protocol_run_id: null,
    step_run_id: null,
    title: "Research GraphQL implementation",
    description: "Evaluate GraphQL vs REST for API v2",
    task_type: "spike",
    priority: "low",
    board_status: "todo",
    story_points: 3,
    assignee: "eve@example.com",
    reporter: "bob@example.com",
    labels: ["research", "api"],
    acceptance_criteria: ["Document pros/cons", "Prototype implementation", "Team presentation"],
    blocked_by: null,
    blocks: null,
    due_date: "2024-01-26",
    started_at: null,
    completed_at: null,
    created_at: "2024-01-15T00:00:00Z",
    updated_at: "2024-01-15T00:00:00Z",
  },
  {
    id: 6,
    project_id: 1,
    sprint_id: 2,
    protocol_run_id: null,
    step_run_id: null,
    title: "Write unit tests for auth module",
    description: "Achieve 80% code coverage for authentication module",
    task_type: "task",
    priority: "medium",
    board_status: "testing",
    story_points: 5,
    assignee: "alice@example.com",
    reporter: "alice@example.com",
    labels: ["testing", "auth"],
    acceptance_criteria: ["80% coverage", "All edge cases covered", "CI pipeline passes"],
    blocked_by: null,
    blocks: null,
    due_date: "2024-01-24",
    started_at: "2024-01-19T10:00:00Z",
    completed_at: null,
    created_at: "2024-01-15T00:00:00Z",
    updated_at: "2024-01-22T14:00:00Z",
  },
  {
    id: 7,
    project_id: 1,
    sprint_id: null,
    protocol_run_id: null,
    step_run_id: null,
    title: "Implement notification system",
    description: "Real-time notifications with email fallback",
    task_type: "story",
    priority: "medium",
    board_status: "backlog",
    story_points: 8,
    assignee: null,
    reporter: "bob@example.com",
    labels: ["feature", "notifications"],
    acceptance_criteria: ["In-app notifications", "Email notifications", "User preferences"],
    blocked_by: null,
    blocks: null,
    due_date: null,
    started_at: null,
    completed_at: null,
    created_at: "2024-01-10T00:00:00Z",
    updated_at: "2024-01-10T00:00:00Z",
  },
  {
    id: 8,
    project_id: 1,
    sprint_id: null,
    protocol_run_id: null,
    step_run_id: null,
    title: "Database optimization",
    description: "Optimize slow queries and add proper indexes",
    task_type: "task",
    priority: "high",
    board_status: "backlog",
    story_points: 5,
    assignee: null,
    reporter: "ops@example.com",
    labels: ["performance", "database"],
    acceptance_criteria: ["Query time < 100ms", "Proper indexes", "Query monitoring"],
    blocked_by: null,
    blocks: null,
    due_date: null,
    started_at: null,
    completed_at: null,
    created_at: "2024-01-12T00:00:00Z",
    updated_at: "2024-01-12T00:00:00Z",
  },
]

// Sprint hooks
export function useSprints(projectId: number) {
  return useSWR<Sprint[]>(queryKeys.sprints.byProject(projectId), async () => {
    if (apiClient.getMockMode()) {
      await new Promise((r) => setTimeout(r, 300))
      return mockSprints.filter((s) => s.project_id === projectId)
    }
    return apiClient.get<Sprint[]>(`/projects/${projectId}/sprints`)
  })
}

export function useAllSprints() {
  return useSWR<Sprint[]>(queryKeys.sprints.all, async () => {
    if (apiClient.getMockMode()) {
      await new Promise((r) => setTimeout(r, 300))
      return mockSprints
    }
    return apiClient.get<Sprint[]>("/sprints")
  })
}

export function useSprint(sprintId: number) {
  return useSWR<Sprint>(queryKeys.sprints.detail(sprintId), async () => {
    if (apiClient.getMockMode()) {
      await new Promise((r) => setTimeout(r, 200))
      const sprint = mockSprints.find((s) => s.id === sprintId)
      if (!sprint) throw new Error("Sprint not found")
      return sprint
    }
    return apiClient.get<Sprint>(`/sprints/${sprintId}`)
  })
}

export function useSprintMetrics(sprintId: number) {
  return useSWR<SprintMetrics>(queryKeys.sprints.metrics(sprintId), async () => {
    if (apiClient.getMockMode()) {
      await new Promise((r) => setTimeout(r, 200))
      const tasks = mockTasks.filter((t) => t.sprint_id === sprintId)
      return {
        sprint_id: sprintId,
        total_tasks: tasks.length,
        completed_tasks: tasks.filter((t) => t.board_status === "done").length,
        total_points: tasks.reduce((acc, t) => acc + (t.story_points || 0), 0),
        completed_points: tasks
          .filter((t) => t.board_status === "done")
          .reduce((acc, t) => acc + (t.story_points || 0), 0),
        burndown: [
          { date: "2024-01-15", ideal: 40, actual: 40 },
          { date: "2024-01-17", ideal: 34, actual: 35 },
          { date: "2024-01-19", ideal: 28, actual: 27 },
          { date: "2024-01-21", ideal: 22, actual: 19 },
          { date: "2024-01-23", ideal: 16, actual: 16 },
        ],
        velocity_trend: [28, 32, 30, 34, 32],
      }
    }
    return apiClient.get<SprintMetrics>(`/sprints/${sprintId}/metrics`)
  })
}

// Task hooks
export function useTasks(projectId: number, sprintId?: number | null) {
  return useSWR<AgileTask[]>(queryKeys.tasks.byProject(projectId, sprintId), async () => {
    if (apiClient.getMockMode()) {
      await new Promise((r) => setTimeout(r, 300))
      let tasks = mockTasks.filter((t) => t.project_id === projectId)
      if (sprintId !== undefined) {
        tasks = tasks.filter((t) => t.sprint_id === sprintId)
      }
      return tasks
    }
    const params = sprintId ? `?sprint_id=${sprintId}` : ""
    return apiClient.get<AgileTask[]>(`/projects/${projectId}/tasks${params}`)
  })
}

export function useAllTasks() {
  return useSWR<AgileTask[]>(queryKeys.tasks.all, async () => {
    if (apiClient.getMockMode()) {
      await new Promise((r) => setTimeout(r, 300))
      return mockTasks
    }
    return apiClient.get<AgileTask[]>("/tasks")
  })
}

export function useTask(taskId: number) {
  return useSWR<AgileTask>(queryKeys.tasks.detail(taskId), async () => {
    if (apiClient.getMockMode()) {
      await new Promise((r) => setTimeout(r, 200))
      const task = mockTasks.find((t) => t.id === taskId)
      if (!task) throw new Error("Task not found")
      return task
    }
    return apiClient.get<AgileTask>(`/tasks/${taskId}`)
  })
}

export function useCreateTask() {
  return {
    mutateAsync: async (projectId: number, data: AgileTaskCreate) => {
      if (apiClient.getMockMode()) {
        await new Promise((r) => setTimeout(r, 300))
        const newTask: AgileTask = {
          id: mockTasks.length + 1,
          project_id: projectId,
          sprint_id: data.sprint_id || null,
          protocol_run_id: null,
          step_run_id: null,
          title: data.title,
          description: data.description || null,
          task_type: data.task_type || "task",
          priority: data.priority || "medium",
          board_status: data.board_status || "backlog",
          story_points: data.story_points || null,
          assignee: data.assignee || null,
          reporter: "current@user.com",
          labels: data.labels || [],
          acceptance_criteria: data.acceptance_criteria || null,
          blocked_by: null,
          blocks: null,
          due_date: data.due_date || null,
          started_at: null,
          completed_at: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        mockTasks.push(newTask)
        mutate(queryKeys.tasks.byProject(projectId, data.sprint_id))
        return newTask
      }
      const result = await apiClient.post<AgileTask>(`/projects/${projectId}/tasks`, data)
      mutate(queryKeys.tasks.byProject(projectId, data.sprint_id))
      return result
    },
    isPending: false,
  }
}

export function useUpdateTask() {
  return {
    mutateAsync: async (taskId: number, data: AgileTaskUpdate) => {
      if (apiClient.getMockMode()) {
        await new Promise((r) => setTimeout(r, 200))
        const taskIndex = mockTasks.findIndex((t) => t.id === taskId)
        if (taskIndex === -1) throw new Error("Task not found")
        mockTasks[taskIndex] = { ...mockTasks[taskIndex], ...data, updated_at: new Date().toISOString() }
        mutate(queryKeys.tasks.detail(taskId))
        mutate(queryKeys.tasks.byProject(mockTasks[taskIndex].project_id, mockTasks[taskIndex].sprint_id))
        return mockTasks[taskIndex]
      }
      const result = await apiClient.patch<AgileTask>(`/tasks/${taskId}`, data)
      mutate(queryKeys.tasks.detail(taskId))
      return result
    },
    isPending: false,
  }
}

export function useCreateSprint() {
  return {
    mutateAsync: async (projectId: number, data: SprintCreate) => {
      if (apiClient.getMockMode()) {
        await new Promise((r) => setTimeout(r, 300))
        const newSprint: Sprint = {
          id: mockSprints.length + 1,
          project_id: projectId,
          name: data.name,
          goal: data.goal || null,
          status: "planning",
          start_date: data.start_date || null,
          end_date: data.end_date || null,
          velocity_planned: data.velocity_planned || null,
          velocity_actual: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        mockSprints.push(newSprint)
        mutate(queryKeys.sprints.byProject(projectId))
        return newSprint
      }
      const result = await apiClient.post<Sprint>(`/projects/${projectId}/sprints`, data)
      mutate(queryKeys.sprints.byProject(projectId))
      return result
    },
    isPending: false,
  }
}
