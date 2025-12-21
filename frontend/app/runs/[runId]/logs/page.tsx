"use client"

import { useParams } from "next/navigation"
import { useRunDetail } from "@/lib/api"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Layers } from "lucide-react"
import Link from "next/link"
import { StreamingLogs } from "@/components/features/streaming-logs"

export default function RunLogsPage() {
  const params = useParams()
  const runIdParam = params?.runId
  const runId = Array.isArray(runIdParam) ? runIdParam[0] : runIdParam
  const { data: run, isLoading: runLoading } = useRunDetail(runId)

  if (!runId || runLoading) {
    return <LoadingState />
  }

  if (!run) {
    return <EmptyState title="Run not found" description="This run may have been deleted." />
  }

  return (
    <div className="container py-8 space-y-6">
      <div className="flex items-center gap-4">
        <Link href={`/runs/${runId}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Run
          </Button>
        </Link>
        <Link href={`/runs/${runId}/artifacts`}>
          <Button variant="outline" size="sm">
            <Layers className="h-4 w-4 mr-2" />
            Artifacts
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Run Logs</h1>
          <p className="text-sm text-muted-foreground">
            {run.job_type} • {run.run_kind}
          </p>
        </div>
      </div>

      <div className="h-[calc(100vh-16rem)]">
        <StreamingLogs runId={runId} />
      </div>
    </div>
  )
}
