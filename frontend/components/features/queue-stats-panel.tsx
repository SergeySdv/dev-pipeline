"use client"

import { useMemo, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DataTable } from "@/components/ui/data-table"
import type { ColumnDef } from "@tanstack/react-table"
import { Layers } from "lucide-react"
import { useQueueJobs, useQueueStats } from "@/lib/api"
import type { QueueJob, QueueStats } from "@/lib/api/types"

// ============================================================================
// Exported types and functions for property-based testing
// ============================================================================

export interface QueueStatusBreakdown {
  queued: number
  started: number
  failed: number
}

export interface QueueStatsValidation {
  isComplete: boolean
  hasQueuedCount: boolean
  hasStartedCount: boolean
  hasFailedCount: boolean
  allCountsNonNegative: boolean
}

/**
 * Computes the total status breakdown from queue stats data.
 * This aggregates counts across all queues.
 */
export function computeQueueStatusBreakdown(stats: QueueStats[]): QueueStatusBreakdown {
  return stats.reduce(
    (acc, s) => {
      acc.queued += s.queued
      acc.started += s.started
      acc.failed += s.failed
      return acc
    },
    { queued: 0, started: 0, failed: 0 },
  )
}

/**
 * Validates that the queue stats breakdown is complete and valid.
 * Property 15: Queue stats status breakdown
 * For any queue statistics data, the panel SHALL display counts for all job statuses present in the data.
 */
export function validateQueueStatsBreakdown(breakdown: QueueStatusBreakdown): QueueStatsValidation {
  const hasQueuedCount = typeof breakdown.queued === 'number'
  const hasStartedCount = typeof breakdown.started === 'number'
  const hasFailedCount = typeof breakdown.failed === 'number'
  const allCountsNonNegative = breakdown.queued >= 0 && breakdown.started >= 0 && breakdown.failed >= 0
  
  return {
    isComplete: hasQueuedCount && hasStartedCount && hasFailedCount && allCountsNonNegative,
    hasQueuedCount,
    hasStartedCount,
    hasFailedCount,
    allCountsNonNegative,
  }
}

/**
 * Verifies that the breakdown correctly sums all individual queue stats.
 */
export function verifyBreakdownSums(stats: QueueStats[], breakdown: QueueStatusBreakdown): boolean {
  const expectedQueued = stats.reduce((sum, s) => sum + s.queued, 0)
  const expectedStarted = stats.reduce((sum, s) => sum + s.started, 0)
  const expectedFailed = stats.reduce((sum, s) => sum + s.failed, 0)
  
  return (
    breakdown.queued === expectedQueued &&
    breakdown.started === expectedStarted &&
    breakdown.failed === expectedFailed
  )
}

// ============================================================================
// Component
// ============================================================================

export function QueueStatsPanel() {
  const { data: stats = [], isLoading: statsLoading } = useQueueStats()
  const [status, setStatus] = useState<string>("all")
  const { data: jobs = [], isLoading: jobsLoading } = useQueueJobs(status === "all" ? undefined : status)

  const totals = useMemo(() => {
    return computeQueueStatusBreakdown(stats)
  }, [stats])

  const jobColumns: ColumnDef<QueueJob>[] = [
    { accessorKey: "job_id", header: "Job ID", cell: ({ row }) => <span className="font-mono text-xs">{row.original.job_id}</span> },
    { accessorKey: "job_type", header: "Type", cell: ({ row }) => <span className="font-mono text-xs">{row.original.job_type}</span> },
    { accessorKey: "status", header: "Status", cell: ({ row }) => <Badge variant="outline" className="text-[10px]">{row.original.status}</Badge> },
    { accessorKey: "enqueued_at", header: "Enqueued", cell: ({ row }) => <span className="text-xs text-muted-foreground">{row.original.enqueued_at}</span> },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Layers className="h-5 w-5" />
          Queues
        </CardTitle>
        <CardDescription>Queue depth and recent jobs</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border bg-muted/20 p-3">
            <div className="text-xs text-muted-foreground">Queued</div>
            <div className="text-2xl font-bold">{statsLoading ? "…" : totals.queued}</div>
          </div>
          <div className="rounded-lg border bg-muted/20 p-3">
            <div className="text-xs text-muted-foreground">Started</div>
            <div className="text-2xl font-bold">{statsLoading ? "…" : totals.started}</div>
          </div>
          <div className="rounded-lg border bg-muted/20 p-3">
            <div className="text-xs text-muted-foreground">Failed</div>
            <div className="text-2xl font-bold">{statsLoading ? "…" : totals.failed}</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-sm font-medium">Jobs</div>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="queued">queued</SelectItem>
              <SelectItem value="started">started</SelectItem>
              <SelectItem value="failed">failed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {jobsLoading ? (
          <div className="text-sm text-muted-foreground">Loading jobs…</div>
        ) : (
          <DataTable columns={jobColumns} data={jobs} enableSearch enableExport enableColumnFilters exportFilename="queue-jobs.csv" />
        )}
      </CardContent>
    </Card>
  )
}

