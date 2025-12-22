"use client"

import { useStepRuns } from "@/lib/api"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { DataTable } from "@/components/ui/data-table"
import { StatusPill } from "@/components/ui/status-pill"
import { ArrowLeft, ExternalLink } from "lucide-react"
import Link from "next/link"
import { formatDate } from "@/lib/format"
import type { ColumnDef } from "@tanstack/react-table"
import type { CodexRun } from "@/lib/api/types"

export default function StepRunsPage({ params }: { params: { id: string } }) {
  const { id } = params
  const stepId = Number.parseInt(id)
  const { data: runs, isLoading } = useStepRuns(stepId)

  if (isLoading) {
    return <LoadingState />
  }

  const columns: ColumnDef<CodexRun>[] = [
    {
      accessorKey: "run_id",
      header: "Run ID",
      cell: ({ row }) => (
        <Link href={`/runs/${row.original.run_id}`} className="text-primary hover:underline flex items-center gap-1">
          {row.original.run_id.slice(0, 8)}
          <ExternalLink className="h-3 w-3" />
        </Link>
      ),
    },
    {
      accessorKey: "run_kind",
      header: "Kind",
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusPill status={row.original.status} />,
    },
    {
      accessorKey: "attempt",
      header: "Attempt",
    },
    {
      accessorKey: "cost_tokens",
      header: "Tokens",
      cell: ({ row }) => row.original.cost_tokens?.toLocaleString() || "-",
    },
    {
      accessorKey: "started_at",
      header: "Started",
      cell: ({ row }) => formatDate(row.original.started_at),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href={`/steps/${id}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Step
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Step Runs</h1>
          <p className="text-sm text-muted-foreground">Step #{stepId}</p>
        </div>
      </div>

      {runs && runs.length > 0 ? (
        <Card>
          <DataTable columns={columns} data={runs} enableSearch enableExport exportFilename={`step-${id}-runs.csv`} />
        </Card>
      ) : (
        <Card className="p-12">
          <EmptyState title="No runs" description="This step has no execution runs yet." />
        </Card>
      )}
    </div>
  )
}
