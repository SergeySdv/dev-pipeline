"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { Activity,ExternalLink } from "lucide-react";

import { StreamingLogs } from "@/components/features/streaming-logs";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useProtocolRuns } from "@/lib/api";

interface LogsTabProps {
  protocolId: number;
}

export function LogsTab({ protocolId }: LogsTabProps) {
  const { data: runs, isLoading } = useProtocolRuns(protocolId);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const resolvedRunId = selectedRunId ?? runs?.[0]?.run_id ?? null;

  const selectedRun = useMemo(
    () => runs?.find((run) => run.run_id === resolvedRunId),
    [runs, resolvedRunId]
  );

  if (isLoading) return <LoadingState message="Loading runs..." />;

  if (!runs || runs.length === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="No runs"
        description="No runs available for log streaming."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <Select value={resolvedRunId || ""} onValueChange={(value) => setSelectedRunId(value)}>
          <SelectTrigger className="w-72">
            <SelectValue placeholder="Select a run" />
          </SelectTrigger>
          <SelectContent>
            {runs.map((run) => (
              <SelectItem key={run.run_id} value={run.run_id}>
                {run.job_type} • {run.status} • {run.run_id.slice(0, 8)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {selectedRun && (
          <Link href={`/runs/${selectedRun.run_id}`} className="inline-flex items-center">
            <Button variant="outline" size="sm">
              <ExternalLink className="mr-2 h-4 w-4" />
              Run Details
            </Button>
          </Link>
        )}
      </div>

      {resolvedRunId && (
        <div className="h-[calc(100vh-28rem)]">
          <StreamingLogs runId={resolvedRunId} />
        </div>
      )}
    </div>
  );
}
