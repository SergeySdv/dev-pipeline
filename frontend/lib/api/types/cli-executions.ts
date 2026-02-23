// CLI Execution Tracking Types

export interface LogEntry {
  timestamp: string;
  level: "info" | "debug" | "warn" | "error";
  message: string;
  source?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface CLIExecution {
  execution_id: string;
  execution_type: string;
  engine_id: string;
  project_id?: number | null;
  status: "pending" | "running" | "succeeded" | "failed" | "cancelled";
  started_at?: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  command?: string | null;
  working_dir?: string | null;
  pid?: number | null;
  exit_code?: number | null;
  error?: string | null;
  metadata: Record<string, unknown>;
  log_count: number;
  logs?: LogEntry[] | null;
}

export interface CLIExecutionListResponse {
  executions: CLIExecution[];
  total: number;
  active_count: number;
}

export interface CLIExecutionFilters {
  execution_type?: string;
  project_id?: number;
  status?: string;
  limit?: number;
}
