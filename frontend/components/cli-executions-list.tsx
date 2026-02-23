"use client";

import { useEffect, useRef, useState } from "react";

import {
  Clock,
  Loader2,
  Terminal,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  useActiveCLIExecutions,
  useCLIExecutionLogStream,
} from "@/lib/api/hooks/use-cli-executions";
import { CLIExecution } from "@/lib/api/types/cli-executions";
import { cn } from "@/lib/utils";

export function CLIExecutionsList() {
  const { data: activeExecutions, isLoading } = useActiveCLIExecutions();
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);

  // Auto-select the first active execution if none selected
  useEffect(() => {
    if (
      !selectedExecutionId &&
      activeExecutions?.active_count &&
      activeExecutions.active_count > 0
    ) {
      setSelectedExecutionId(activeExecutions.executions[0].execution_id);
    }
  }, [activeExecutions, selectedExecutionId]);

  if (isLoading) {
    return (
      <div className="flex justify-center p-4">
        <Loader2 className="text-muted-foreground animate-spin" />
      </div>
    );
  }

  const hasActive = activeExecutions?.active_count && activeExecutions.active_count > 0;

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-base">
              <Terminal className="h-4 w-4" />
              Active Operations
              {hasActive && (
                <Badge
                  variant="outline"
                  className="ml-2 animate-pulse border-blue-500 text-blue-500"
                >
                  Running
                </Badge>
              )}
            </CardTitle>
            <CardDescription>Real-time tracking of discovery and agent processes</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {!hasActive && !selectedExecutionId ? (
          <div className="text-muted-foreground p-8 text-center text-sm">No active operations.</div>
        ) : (
          <div className="flex h-[500px] flex-col border-t md:flex-row">
            {/* List Sidebar */}
            <div className="w-full overflow-y-auto border-r md:w-1/3">
              {activeExecutions?.executions.map((exec) => (
                <div
                  key={exec.execution_id}
                  onClick={() => setSelectedExecutionId(exec.execution_id)}
                  className={cn(
                    "hover:bg-muted/50 cursor-pointer border-b p-4 transition-colors",
                    selectedExecutionId === exec.execution_id && "bg-muted"
                  )}
                >
                  <div className="mb-1 flex items-start justify-between">
                    <span className="text-sm font-semibold capitalize">{exec.execution_type}</span>
                    <ExecutionStatusBadge status={exec.status} />
                  </div>
                  <div className="text-muted-foreground mb-2 text-xs break-words whitespace-pre-wrap">
                    {exec.command}
                  </div>
                  <div className="text-muted-foreground flex items-center gap-2 text-xs">
                    <Badge variant="secondary" className="h-4 px-1 text-[10px]">
                      {exec.engine_id}
                    </Badge>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {exec.duration_seconds ? `${exec.duration_seconds.toFixed(1)}s` : "..."}
                    </span>
                  </div>
                </div>
              ))}

              {/* If we have a selected ID that is NOT in the active list (because it finished), 
                  we might want to fetch it separately or list recent ones. 
                  For now, let's keep it simple. */}
            </div>

            {/* Log Terminal */}
            <div className="flex w-full flex-col bg-black font-mono text-xs text-gray-300 md:w-2/3">
              {selectedExecutionId ? (
                <ExecutionLogViewer executionId={selectedExecutionId} />
              ) : (
                <div className="flex flex-1 items-center justify-center text-gray-600">
                  Select an operation to view logs
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ExecutionStatusBadge({ status }: { status: CLIExecution["status"] }) {
  switch (status) {
    case "running":
      return (
        <Badge variant="default" className="bg-blue-600 hover:bg-blue-700">
          Running
        </Badge>
      );
    case "succeeded":
      return (
        <Badge variant="default" className="bg-green-600 hover:bg-green-700">
          Success
        </Badge>
      );
    case "failed":
      return <Badge variant="destructive">Failed</Badge>;
    case "cancelled":
      return <Badge variant="secondary">Cancelled</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

function ExecutionLogViewer({ executionId }: { executionId: string }) {
  const { logs, status, isConnected } = useCLIExecutionLogStream(executionId);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      const scrollElement = scrollRef.current.querySelector("[data-radix-scroll-area-viewport]");
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [logs, autoScroll]);

  // Detect if user scrolled up to disable auto-scroll
  const _handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = event.currentTarget;
    const atBottom = scrollHeight - scrollTop === clientHeight;
    setAutoScroll(atBottom);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-800 bg-gray-900 px-4 py-2 text-xs text-gray-400">
        <div className="flex items-center gap-2">
          <Terminal className="h-3 w-3" />
          <span>LOGS: {executionId.slice(0, 8)}...</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div
              className={cn(
                "h-2 w-2 rounded-full",
                isConnected ? "animate-pulse bg-green-500" : "bg-red-500"
              )}
            />
            <span>{status || "disconnected"}</span>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-1">
          {logs.map((log, i) => (
            <div key={i} className="flex gap-3">
              <span className="w-20 shrink-0 text-gray-600 select-none">
                {
                  new Date(log.timestamp)
                    .toLocaleTimeString([], {
                      hour12: false,
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                      fractionalSecondDigits: 3,
                    })
                    .split(" ")[0]
                }
              </span>
              <span
                className={cn(
                  "flex-1 break-all whitespace-pre-wrap",
                  log.level === "error"
                    ? "text-red-400"
                    : log.level === "warn"
                      ? "text-amber-400"
                      : log.level === "debug"
                        ? "text-gray-500"
                        : "text-gray-300"
                )}
              >
                {log.source && <span className="mr-2 text-gray-500">[{log.source}]</span>}
                {log.message}
              </span>
            </div>
          ))}
          {logs.length === 0 && <div className="text-gray-600 italic">Waiting for logs...</div>}
        </div>
      </ScrollArea>
    </div>
  );
}
