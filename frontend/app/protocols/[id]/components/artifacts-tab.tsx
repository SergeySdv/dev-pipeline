"use client";

import { Code2, FileBox, FileText, Image } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { useProtocolArtifacts } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";

interface ArtifactsTabProps {
  protocolId: number;
}

function artifactIcon(kind: string) {
  if (kind === "code" || kind === "diff") return Code2;
  if (kind === "image" || kind === "screenshot") return Image;
  return FileText;
}

function formatBytes(bytes: number | null | undefined) {
  if (!bytes) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ArtifactsTab({ protocolId }: ArtifactsTabProps) {
  const { data: artifacts, isLoading } = useProtocolArtifacts(protocolId);

  if (isLoading) return <LoadingState message="Loading artifacts..." />;
  if (!artifacts || artifacts.length === 0) {
    return (
      <EmptyState
        icon={FileBox}
        title="No artifacts"
        description="Protocol artifacts will appear here after steps produce output."
      />
    );
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
              const Icon = artifactIcon(artifact.kind);
              return (
                <div key={artifact.id} className="flex items-center gap-3 rounded-lg border p-3">
                  <Icon className="text-muted-foreground h-5 w-5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium">{artifact.name}</span>
                      <Badge variant="outline" className="shrink-0 text-[10px]">
                        {artifact.kind}
                      </Badge>
                    </div>
                    <div className="text-muted-foreground mt-1 flex items-center gap-3 text-xs">
                      <span className="truncate">{artifact.path}</span>
                      <span>{formatBytes(artifact.bytes)}</span>
                      <span>{formatRelativeTime(artifact.created_at)}</span>
                    </div>
                  </div>
                  {artifact.step_run_id && (
                    <Badge variant="secondary" className="shrink-0 text-[10px]">
                      Step #{artifact.step_run_id}
                    </Badge>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
