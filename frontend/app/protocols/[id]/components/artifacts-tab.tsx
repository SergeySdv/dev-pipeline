"use client"

import { useProtocolArtifacts } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { FileBox, Download, FileText, Code2, Image } from "lucide-react"
import { Button } from "@/components/ui/button"
import { formatRelativeTime } from "@/lib/format"

interface ArtifactsTabProps {
  protocolId: number
}

function artifactIcon(kind: string) {
  if (kind === "code" || kind === "diff") return Code2
  if (kind === "image" || kind === "screenshot") return Image
  return FileText
}

function formatBytes(bytes: number | null) {
  if (!bytes) return "-"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function ArtifactsTab({ protocolId }: ArtifactsTabProps) {
  const { data: artifacts, isLoading } = useProtocolArtifacts(protocolId)

  if (isLoading) return <LoadingState message="Loading artifacts..." />
  if (!artifacts || artifacts.length === 0) {
    return <EmptyState icon={FileBox} title="No artifacts" description="Protocol artifacts will appear here after steps produce output." />
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileBox className="h-5 w-5" />
            Protocol Artifacts
          </CardTitle>
          <CardDescription>{artifacts.length} artifact(s) across all steps</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {artifacts.map((artifact) => {
              const Icon = artifactIcon(artifact.kind)
              return (
                <div key={artifact.id} className="flex items-center gap-3 rounded-lg border p-3">
                  <Icon className="h-5 w-5 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm truncate">{artifact.name}</span>
                      <Badge variant="outline" className="text-[10px] shrink-0">{artifact.kind}</Badge>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                      <span className="truncate">{artifact.path}</span>
                      <span>{formatBytes(artifact.bytes)}</span>
                      <span>{formatRelativeTime(artifact.created_at)}</span>
                    </div>
                  </div>
                  {artifact.step_run_id && (
                    <Badge variant="secondary" className="text-[10px] shrink-0">
                      Step #{artifact.step_run_id}
                    </Badge>
                  )}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
