"use client"

import { useState } from "react"
import Link from "next/link"
import { useRuns } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { DataTable } from "@/components/ui/data-table"
import { StatusPill } from "@/components/ui/status-pill"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { CLIExecutionsList } from "@/components/cli-executions-list"
import { ExternalLink, PlayCircle, RefreshCw, ListTodo } from "lucide-react"
import { formatRelativeTime, formatTokens, formatCost, truncateHash } from "@/lib/format"
import type { ColumnDef } from "@tanstack/react-table"
import type { CodexRun, RunFilters } from "@/lib/api/types"
import { CostAnalyticsChart } from "@/components/visualizations/cost-analytics-chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const columns: ColumnDef<CodexRun>[] = [
  {
    accessorKey: "run_id",
    header: "Run ID",
    cell: ({ row }) => (
      <Link href={`/runs/${row.original.run_id}`} className="font-mono text-sm hover:underline">
        {truncateHash(row.original.run_id, 12)}
      </Link>
    ),
  },
  {
    id: "agile_context",
    header: "Sprint/Task",
    cell: () => {
      // In real app, this would come from joined data
      const hasTask = Math.random() > 0.5
      const sprintName = hasTask ? `Sprint ${Math.floor(Math.random() * 5) + 1}` : null

      return hasTask ? (
        <div className="flex items-center gap-1 text-xs">
          <ListTodo className="h-3 w-3 text-blue-400" />
          <span className="text-muted-foreground">{sprintName}</span>
        </div>
      ) : (
        <span className="text-xs text-muted-foreground">-</span>
      )
    },
  },
  {
    accessorKey: "job_type",
    header: "Job Type",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.job_type}</span>,
  },
  {
    accessorKey: "run_kind",
    header: "Kind",
    cell: ({ row }) => <span className="capitalize">{row.original.run_kind}</span>,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusPill status={row.original.status} size="sm" />,
  },
  {
    accessorKey: "attempt",
    header: "Attempt",
  },
  {
    accessorKey: "cost_tokens",
    header: "Tokens",
    cell: ({ row }) => <span className="text-muted-foreground">{formatTokens(row.original.cost_tokens)}</span>,
  },
  {
    accessorKey: "cost_cents",
    header: "Cost",
    cell: ({ row }) => <span className="text-muted-foreground">{formatCost(row.original.cost_cents)}</span>,
  },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => <span className="text-muted-foreground">{formatRelativeTime(row.original.created_at)}</span>,
  },
  {
    id: "actions",
    cell: ({ row }) => (
      <Link href={`/runs/${row.original.run_id}`}>
        <Button variant="ghost" size="sm">
          <ExternalLink className="h-4 w-4" />
        </Button>
      </Link>
    ),
  },
]

export default function RunsPage() {
  const [filters, setFilters] = useState<RunFilters>({
    limit: 100,
  })

  const { data: runs, isLoading, refetch } = useRuns(filters)

  return (
    <div className="container py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Runs Explorer</h1>
          <p className="text-muted-foreground">Browse and inspect execution runs across all projects</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" asChild>
            <Link href="/execution">
              <ListTodo className="mr-2 h-4 w-4" />
              View Execution
            </Link>
          </Button>
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* CLI Executions Section */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">Active Operations</h2>
        <CLIExecutionsList />
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Job History</h2>
        </div>

        <div className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3 text-sm">
          <div className="flex items-center gap-2">
            <ListTodo className="h-4 w-4 text-blue-400" />
            <span className="font-medium">Linked to Tasks:</span>
            <span className="text-muted-foreground">{runs ? Math.floor(runs.length * 0.6) : 0}</span>
          </div>
          <div className="h-4 w-px bg-border" />
          <div className="flex items-center gap-2">
            <PlayCircle className="h-4 w-4 text-green-400" />
            <span className="font-medium">Active Executions:</span>
            <span className="text-muted-foreground">3</span>
          </div>
          <div className="h-4 w-px bg-border" />
          <div className="flex items-center gap-2">
            <span className="font-medium">Execution Runs:</span>
            <span className="text-muted-foreground">{runs ? Math.floor(runs.length * 0.4) : 0}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-4">
          <Select
            value={filters.job_type || "all"}
            onValueChange={(v) => setFilters((f) => ({ ...f, job_type: v === "all" ? undefined : v }))}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Job Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="execute_step">execute_step</SelectItem>
              <SelectItem value="run_quality">run_quality</SelectItem>
              <SelectItem value="planning">planning</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={filters.status || "all"}
            onValueChange={(v) =>
              setFilters((f) => ({ ...f, status: v === "all" ? undefined : (v as RunFilters["status"]) }))
            }
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="succeeded">Succeeded</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={filters.run_kind || "all"}
            onValueChange={(v) => setFilters((f) => ({ ...f, run_kind: v === "all" ? undefined : v }))}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Kind" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Kinds</SelectItem>
              <SelectItem value="exec">exec</SelectItem>
              <SelectItem value="qa">qa</SelectItem>
            </SelectContent>
          </Select>

          <Input
            type="number"
            placeholder="Limit"
            className="w-24"
            value={filters.limit || 100}
            onChange={(e) => setFilters((f) => ({ ...f, limit: Number(e.target.value) || 100 }))}
          />
        </div>

        {isLoading ? (
          <LoadingState message="Loading runs..." />
        ) : !runs || runs.length === 0 ? (
          <EmptyState icon={PlayCircle} title="No runs found" description="No runs match your filter criteria." />
        ) : (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Cost Analytics</CardTitle>
                <CardDescription>Costs aggregated from the current run set</CardDescription>
              </CardHeader>
              <CardContent>
                <CostAnalyticsChart runs={runs} />
              </CardContent>
            </Card>
            <DataTable columns={columns} data={runs} enableSearch enableExport enableColumnFilters exportFilename="runs.csv" />
          </div>
        )}
      </div>
    </div>
  )
}
