"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { useRunDetail, useRunArtifacts } from "@/lib/api"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { DataTable } from "@/components/ui/data-table"
import { ArrowLeft, Download, Eye, FileText, GitCompare } from "lucide-react"
import Link from "next/link"
import { formatBytes, formatDate } from "@/lib/format"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { CodeBlock } from "@/components/ui/code-block"
import { DiffViewer } from "@/components/ui/diff-viewer"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { ColumnDef } from "@tanstack/react-table"
import type { RunArtifact } from "@/lib/api/types"

export default function RunArtifactsPage() {
  const params = useParams()
  const runIdParam = params?.runId
  const runId = Array.isArray(runIdParam) ? runIdParam[0] : runIdParam
  const { data: run, isLoading: runLoading } = useRunDetail(runId)
  const { data: artifacts, isLoading: artifactsLoading } = useRunArtifacts(runId)
  const [viewingArtifact, setViewingArtifact] = useState<RunArtifact | null>(null)
  const [filterKind, setFilterKind] = useState<"all" | "file" | "diff">("all")

  if (!runId || runLoading || artifactsLoading) {
    return <LoadingState />
  }

  if (!run) {
    return <EmptyState title="Run not found" description="This run may have been deleted." />
  }

  const filteredArtifacts = artifacts?.filter((artifact) => {
    if (filterKind === "all") return true
    if (filterKind === "file") return artifact.content_type !== "diff"
    if (filterKind === "diff") return artifact.content_type === "diff"
    return true
  })

  const fileCount = artifacts?.filter((a) => a.content_type !== "diff").length || 0
  const diffCount = artifacts?.filter((a) => a.content_type === "diff").length || 0

  const columns: ColumnDef<RunArtifact>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {row.original.content_type === "diff" ? (
            <GitCompare className="h-4 w-4 text-muted-foreground" />
          ) : (
            <FileText className="h-4 w-4 text-muted-foreground" />
          )}
          <span>{row.original.name}</span>
          {row.original.content_type === "diff" && (
            <Badge variant="outline" className="ml-2">
              Diff
            </Badge>
          )}
        </div>
      ),
    },
    {
      accessorKey: "kind",
      header: "Kind",
    },
    {
      accessorKey: "bytes",
      header: "Size",
      cell: ({ row }) => formatBytes(row.original.bytes),
    },
    {
      accessorKey: "diff_stats",
      header: "Changes",
      cell: ({ row }) => {
        if (row.original.content_type !== "diff" || !row.original.diff_data) return null
        const { additions, deletions } = row.original.diff_data
        return (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-green-600 dark:text-green-400">+{additions}</span>
            <span className="text-red-600 dark:text-red-400">-{deletions}</span>
          </div>
        )
      },
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => formatDate(row.original.created_at),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setViewingArtifact(row.original)}>
            <Eye className="h-4 w-4 mr-1" />
            View
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.open(`/runs/${runId}/artifacts/${row.original.id}/content`, "_blank")}
          >
            <Download className="h-4 w-4 mr-1" />
            Download
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href={`/runs/${runId}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Run
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Run Artifacts</h1>
          <p className="text-sm text-muted-foreground">
            {run.job_type} • {run.run_kind}
          </p>
        </div>
      </div>

      {artifacts && artifacts.length > 0 ? (
        <div className="space-y-4">
          <Tabs
            value={filterKind}
            onValueChange={(v) => {
              if (v === "all" || v === "file" || v === "diff") {
                setFilterKind(v)
              }
            }}
          >
            <TabsList>
              <TabsTrigger value="all">All ({artifacts.length})</TabsTrigger>
              <TabsTrigger value="file">Files ({fileCount})</TabsTrigger>
              <TabsTrigger value="diff">Diffs ({diffCount})</TabsTrigger>
            </TabsList>
          </Tabs>

          <Card>
            <DataTable
              columns={columns}
              data={filteredArtifacts || []}
              enableSearch
              enableExport
              enableColumnFilters
              exportFilename={`run-${runId}-artifacts.csv`}
            />
          </Card>
        </div>
      ) : (
        <Card className="p-12">
          <EmptyState title="No artifacts" description="This run produced no artifacts." />
        </Card>
      )}

      <Dialog open={!!viewingArtifact} onOpenChange={() => setViewingArtifact(null)}>
        <DialogContent className="max-w-5xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {viewingArtifact?.content_type === "diff" ? (
                <GitCompare className="h-5 w-5" />
              ) : (
                <FileText className="h-5 w-5" />
              )}
              {viewingArtifact?.name}
            </DialogTitle>
          </DialogHeader>

          {viewingArtifact?.content_type === "diff" && viewingArtifact?.diff_data ? (
            <DiffViewer
              oldPath={viewingArtifact.diff_data.old_path}
              newPath={viewingArtifact.diff_data.new_path}
              additions={viewingArtifact.diff_data.additions}
              deletions={viewingArtifact.diff_data.deletions}
              hunks={viewingArtifact.diff_data.hunks}
            />
          ) : (
            <div className="p-4 text-sm text-muted-foreground">
              <p>Artifact: {viewingArtifact?.name}</p>
              <p className="mt-2">Path: <code className="font-mono">{viewingArtifact?.path}</code></p>
              <p className="mt-4">Use the Download button to view the full content.</p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
