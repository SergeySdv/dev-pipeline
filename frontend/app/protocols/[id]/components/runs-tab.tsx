"use client"

import Link from "next/link"
import { useProtocolRuns } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { DataTable } from "@/components/ui/data-table"
import { StatusPill } from "@/components/ui/status-pill"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { ExternalLink, PlayCircle } from "lucide-react"
import { formatRelativeTime, formatTokens, truncateHash } from "@/lib/format"
import type { ColumnDef } from "@tanstack/react-table"
import type { CodexRun } from "@/lib/api/types"

interface RunsTabProps {
  protocolId: number
}

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
    cell: ({ row }) => <span className="text-muted-foreground">{row.original.attempt}</span>,
  },
  {
    accessorKey: "cost_tokens",
    header: "Tokens",
    cell: ({ row }) => <span className="text-muted-foreground">{formatTokens(row.original.cost_tokens)}</span>,
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

export function RunsTab({ protocolId }: RunsTabProps) {
  const { data: runs, isLoading } = useProtocolRuns(protocolId)

  if (isLoading) return <LoadingState message="Loading runs..." />

  if (!runs || runs.length === 0) {
    return (
      <EmptyState
        icon={PlayCircle}
        title="No runs yet"
        description="Execution runs will appear here when steps are executed."
      />
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Execution Runs</h3>
        <p className="text-sm text-muted-foreground">{runs.length} run(s)</p>
      </div>
      <DataTable columns={columns} data={runs} />
    </div>
  )
}
