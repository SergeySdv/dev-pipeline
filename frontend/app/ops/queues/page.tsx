"use client"

import { useQueueStats, useQueueJobs } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DataTable } from "@/components/ui/data-table"
import { StatusPill } from "@/components/ui/status-pill"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { RefreshCw, Inbox } from "lucide-react"
import { formatRelativeTime } from "@/lib/format"
import { useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import type { QueueJob } from "@/lib/api/types"

const jobColumns: ColumnDef<QueueJob>[] = [
  {
    accessorKey: "job_id",
    header: "Job ID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.job_id.slice(0, 12)}...</span>,
  },
  {
    accessorKey: "job_type",
    header: "Type",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.job_type}</span>,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusPill status={row.original.status} size="sm" />,
  },
  {
    accessorKey: "enqueued_at",
    header: "Enqueued",
    cell: ({ row }) => <span className="text-muted-foreground">{formatRelativeTime(row.original.enqueued_at)}</span>,
  },
  {
    accessorKey: "started_at",
    header: "Started",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.started_at ? formatRelativeTime(row.original.started_at) : "-"}
      </span>
    ),
  },
]

export default function QueuesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQueueStats()
  const {
    data: jobs,
    isLoading: jobsLoading,
    refetch: refetchJobs,
  } = useQueueJobs(statusFilter === "all" ? undefined : statusFilter)

  const handleRefresh = () => {
    refetchStats()
    refetchJobs()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Queue Statistics</h2>
        <Button variant="outline" onClick={handleRefresh}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {statsLoading ? (
        <LoadingState message="Loading queue stats..." />
      ) : stats && stats.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-3">
          {stats.map((queue) => {
            const total = queue.queued + queue.started + queue.failed
            const healthPercent = total > 0 ? Math.round(((queue.queued + queue.started) / total) * 100) : 100

            return (
              <Card key={queue.name}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg capitalize">{queue.name}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Queued</span>
                    <span className="font-medium">{queue.queued}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Started</span>
                    <span className="font-medium">{queue.started}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Failed</span>
                    <span className="font-medium text-destructive">{queue.failed}</span>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Health</span>
                      <span>{healthPercent}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className={`h-full transition-all ${healthPercent > 80 ? "bg-green-500" : healthPercent > 50 ? "bg-yellow-500" : "bg-destructive"}`}
                        style={{ width: `${healthPercent}%` }}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        <EmptyState icon={Inbox} title="No queues" description="No queue data available." />
      )}

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Recent Jobs</h2>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="All" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="started">Started</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {jobsLoading ? (
          <LoadingState message="Loading jobs..." />
        ) : !jobs || jobs.length === 0 ? (
          <EmptyState icon={Inbox} title="No jobs" description="No jobs match your filter criteria." />
        ) : (
          <DataTable columns={jobColumns} data={jobs} enableSearch enableExport enableColumnFilters exportFilename="queue-jobs.csv" />
        )}
      </div>
    </div>
  )
}
