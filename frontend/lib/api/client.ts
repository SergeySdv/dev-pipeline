// API Client with authentication, error handling, and mock mode support

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: Record<string, unknown>,
  ) {
    super(message)
    this.name = "ApiError"
  }

  get type(): ApiErrorType {
    if (this.status === 401) return "unauthorized"
    if (this.status === 403) return "forbidden"
    if (this.status === 404) return "not_found"
    if (this.status === 409) return "conflict"
    if (this.status === 400) return "validation"
    if (this.status >= 500) return "server_error"
    return "server_error"
  }
}

export type ApiErrorType =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "validation"
  | "server_error"
  | "network_error"

interface ApiClientConfig {
  baseUrl: string
  token?: string
  projectTokens?: Record<number, string>
  onUnauthorized?: () => void
}

const STORAGE_KEY = "tasksgodzilla_config"

interface StoredConfig {
  apiBase: string
  token: string
  projectTokens: Record<number, string>
}

function getStoredConfig(): StoredConfig | null {
  if (typeof window === "undefined") return null
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

function setStoredConfig(config: Partial<StoredConfig>) {
  if (typeof window === "undefined") return
  const current = getStoredConfig() || { apiBase: "", token: "", projectTokens: {} }
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...current, ...config }))
}

class ApiClient {
  private config: ApiClientConfig
  private useMockData = false

  constructor() {
    const stored = getStoredConfig()
    // Use environment variable, stored config, or default to localhost:8080
    const defaultBaseUrl = typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_BASE_URL
      ? process.env.NEXT_PUBLIC_API_BASE_URL
      : "http://localhost:8080"
    this.config = {
      baseUrl: stored?.apiBase || defaultBaseUrl,
      token: stored?.token,
      projectTokens: stored?.projectTokens || {},
    }
  }

  configure(config: Partial<ApiClientConfig>) {
    this.config = { ...this.config, ...config }
    setStoredConfig({
      apiBase: this.config.baseUrl,
      token: this.config.token,
      projectTokens: this.config.projectTokens,
    })
  }

  setMockMode(enabled: boolean) {
    this.useMockData = enabled
  }

  getMockMode() {
    return this.useMockData
  }

  getConfig() {
    return { ...this.config }
  }

  setProjectToken(projectId: number, token: string) {
    this.config.projectTokens = {
      ...this.config.projectTokens,
      [projectId]: token,
    }
    setStoredConfig({ projectTokens: this.config.projectTokens })
  }

  async fetch<T>(path: string, options?: RequestInit & { projectId?: number }): Promise<T> {
    if (this.useMockData) {
      return this.getMockResponse<T>(path, options?.method || "GET")
    }

    const headers = new Headers(options?.headers)
    headers.set("Content-Type", "application/json")

    if (this.config.token) {
      headers.set("Authorization", `Bearer ${this.config.token}`)
    }

    if (options?.projectId && this.config.projectTokens?.[options.projectId]) {
      headers.set("X-Project-Token", this.config.projectTokens[options.projectId])
    }

    headers.set("X-Request-ID", crypto.randomUUID())

    try {
      const response = await fetch(`${this.config.baseUrl}${path}`, {
        ...options,
        headers,
      })

      if (response.status === 401) {
        this.config.onUnauthorized?.()
        throw new ApiError("Unauthorized", 401)
      }

      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new ApiError(body.detail || `Request failed with status ${response.status}`, response.status, body)
      }

      const text = await response.text()
      if (!text) return {} as T
      return JSON.parse(text)
    } catch (error) {
      if (error instanceof ApiError && error.status === 0) {
        console.log("[v0] API unavailable, using mock data")
        this.useMockData = true
        return this.getMockResponse<T>(path, options?.method || "GET")
      }
      if (error instanceof ApiError) throw error
      throw new ApiError(error instanceof Error ? error.message : "Network error", 0)
    }
  }

  private async getMockResponse<T>(path: string, method: string): Promise<T> {
    const {
      mockProjects,
      mockProtocols,
      mockSteps,
      mockRuns,
      mockEvents,
      mockPolicyPacks,
      mockClarifications,
      mockQueueStats,
      mockOnboarding,
      mockBranches,
      mockArtifacts,
      mockPolicyFindings,
      mockSprints,
      mockAgileTasks,
      getMockProject,
      getMockProtocol,
      getMockProtocolsByProject,
      getMockStepsByProtocol,
      getMockRunsByProtocol,
      getMockEventsByProtocol,
      getMockClarificationsByProject,
      getMockClarificationsByProtocol,
      getMockSprintsByProject,
      getMockSprint,
      getMockTasksBySprint,
      getMockTasksByProject,
      getMockTask,
    } = await import("./mock-data")

    await new Promise((resolve) => setTimeout(resolve, 300))

    const cleanPath = path.split("?")[0]

    if (cleanPath === "/projects" && method === "GET") return mockProjects as T
    if (cleanPath.match(/^\/projects\/(\d+)$/) && method === "GET") {
      const id = Number.parseInt(cleanPath.split("/")[2])
      return getMockProject(id) as T
    }
    if (cleanPath.match(/^\/projects\/(\d+)\/protocols$/) && method === "GET") {
      const projectId = Number.parseInt(cleanPath.split("/")[2])
      return getMockProtocolsByProject(projectId) as T
    }
    if (cleanPath.match(/^\/projects\/(\d+)\/clarifications$/) && method === "GET") {
      const projectId = Number.parseInt(cleanPath.split("/")[2])
      return getMockClarificationsByProject(projectId) as T
    }
    if (cleanPath.match(/^\/projects\/(\d+)\/onboarding$/) && method === "GET") {
      const projectId = Number.parseInt(cleanPath.split("/")[2])
      return (mockOnboarding[projectId] || {
        project_id: projectId,
        status: "not_started",
        stages: [],
        events: [],
        blocking_clarifications: 0,
      }) as T
    }
    if (cleanPath.match(/^\/projects\/(\d+)\/branches$/) && method === "GET") {
      const projectId = Number.parseInt(cleanPath.split("/")[2])
      return (mockBranches[projectId] || []) as T
    }

    if (cleanPath === "/protocols" && method === "GET") return mockProtocols as T

    if (cleanPath.match(/^\/protocols\/(\d+)$/) && method === "GET") {
      const id = Number.parseInt(cleanPath.split("/")[2])
      return getMockProtocol(id) as T
    }
    if (cleanPath.match(/^\/protocols\/(\d+)\/steps$/) && method === "GET") {
      const protocolId = Number.parseInt(cleanPath.split("/")[2])
      return getMockStepsByProtocol(protocolId) as T
    }
    if (cleanPath.match(/^\/protocols\/(\d+)\/runs$/) && method === "GET") {
      const protocolId = Number.parseInt(cleanPath.split("/")[2])
      return getMockRunsByProtocol(protocolId) as T
    }
    if (cleanPath.match(/^\/protocols\/(\d+)\/events$/) && method === "GET") {
      const protocolId = Number.parseInt(cleanPath.split("/")[2])
      return getMockEventsByProtocol(protocolId) as T
    }
    if (cleanPath.match(/^\/protocols\/(\d+)\/policy\/findings$/) && method === "GET") {
      const protocolId = Number.parseInt(cleanPath.split("/")[2])
      return (mockPolicyFindings[protocolId] || []) as T
    }
    if (cleanPath.match(/^\/protocols\/(\d+)\/clarifications$/) && method === "GET") {
      const protocolId = Number.parseInt(cleanPath.split("/")[2])
      return getMockClarificationsByProtocol(protocolId) as T
    }

    if (cleanPath.match(/^\/steps\/(\d+)$/) && method === "GET") {
      const id = Number.parseInt(cleanPath.split("/")[2])
      return mockSteps.find((s) => s.id === id) as T
    }
    if (cleanPath.match(/^\/steps\/(\d+)\/policy\/findings$/) && method === "GET") {
      const stepId = Number.parseInt(cleanPath.split("/")[2])
      return (mockPolicyFindings[stepId] || []) as T
    }
    if (cleanPath.match(/^\/steps\/(\d+)\/runs$/) && method === "GET") {
      const stepId = Number.parseInt(cleanPath.split("/")[2])
      return mockRuns.filter((r) => r.step_id === stepId) as T
    }

    if (cleanPath === "/runs" && method === "GET") return mockRuns as T
    if (cleanPath === "/codex/runs" && method === "GET") return mockRuns as T
    if (cleanPath.match(/^\/runs\/(.+)$/) && method === "GET") {
      const runId = cleanPath.split("/")[2]
      return mockRuns.find((r) => r.run_id === runId) as T
    }
    if (cleanPath.match(/^\/codex\/runs\/(.+)\/artifacts$/) && method === "GET") {
      const runId = cleanPath.split("/")[3]
      return (mockArtifacts[runId] || []) as T
    }
    if (cleanPath.match(/^\/codex\/runs\/(.+)\/logs$/) && method === "GET") {
      const runId = cleanPath.split("/")[3]
      return { content: `Mock logs for run ${runId}` } as T
    }
    if (cleanPath.match(/^\/codex\/runs\/(.+)$/) && method === "GET") {
      const runId = cleanPath.split("/")[3]
      return mockRuns.find((r) => r.run_id === runId) as T
    }

    if (cleanPath.match(/^\/runs\/(.+)\/artifacts$/) && method === "GET") {
      const runId = cleanPath.split("/")[2]
      return (mockArtifacts[runId] || []) as T
    }

    if ((cleanPath === "/policy_packs" || cleanPath === "/policy-packs") && method === "GET")
      return mockPolicyPacks as T
    if (cleanPath.match(/^\/policy[-_]packs\/(.+)$/) && method === "GET") {
      const key = cleanPath.split("/")[2]
      return mockPolicyPacks.find((p) => p.key === key) as T
    }

    if (cleanPath === "/sprints" && method === "GET") return mockSprints as T
    if (cleanPath.match(/^\/sprints\/(\d+)$/) && method === "GET") {
      const id = Number.parseInt(cleanPath.split("/")[2])
      return getMockSprint(id) as T
    }
    if (cleanPath.match(/^\/projects\/(\d+)\/sprints$/) && method === "GET") {
      const projectId = Number.parseInt(cleanPath.split("/")[2])
      return getMockSprintsByProject(projectId) as T
    }
    if (cleanPath.match(/^\/sprints\/(\d+)\/tasks$/) && method === "GET") {
      const sprintId = Number.parseInt(cleanPath.split("/")[2])
      return getMockTasksBySprint(sprintId) as T
    }

    if (cleanPath === "/tasks" && method === "GET") return mockAgileTasks as T
    if (cleanPath.match(/^\/tasks\/(\d+)$/) && method === "GET") {
      const id = Number.parseInt(cleanPath.split("/")[2])
      return getMockTask(id) as T
    }
    if (cleanPath.match(/^\/projects\/(\d+)\/tasks$/) && method === "GET") {
      const projectId = Number.parseInt(cleanPath.split("/")[2])
      return getMockTasksByProject(projectId) as T
    }

    if (cleanPath === "/health" && method === "GET") {
      return { status: "ok", version: "mock-v1.0.0" } as T
    }

    if (method === "POST" || method === "PUT") {
      return {
        message: "Mock operation successful",
        job: { job_id: "mock_job_" + Math.random().toString(36).substr(2, 9) },
      } as T
    }

    return {} as T
  }

  get<T>(path: string, options?: { projectId?: number }) {
    return this.fetch<T>(path, { method: "GET", ...options })
  }

  post<T>(path: string, body?: unknown, options?: { projectId?: number }) {
    return this.fetch<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    })
  }

  put<T>(path: string, body?: unknown, options?: { projectId?: number }) {
    return this.fetch<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    })
  }

  delete<T>(path: string, options?: { projectId?: number }) {
    return this.fetch<T>(path, { method: "DELETE", ...options })
  }
}

export const apiClient = new ApiClient()

// Use mock mode only if explicitly enabled via environment variable
if (typeof window !== "undefined") {
  const useMock = typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_MOCK_MODE === 'true'
  apiClient.setMockMode(useMock)
}

