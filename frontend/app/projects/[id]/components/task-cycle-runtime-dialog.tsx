"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { AlertCircle, Bot, ExternalLink, FileText, GitBranch, Layers3, ShieldAlert } from "lucide-react";

import { useWorkItemRuntime, useWorkItemArtifactContent, useStepArtifactContent } from "@/lib/api";
import type { WorkItemRuntimeArtifact } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/ui/code-block";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { LoadingState } from "@/components/ui/loading-state";
import { ScrollArea } from "@/components/ui/scroll-area";
import { StatusPill } from "@/components/ui/status-pill";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface TaskCycleRuntimeDialogProps {
  workItemId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "Not available";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function artifactPreviewTitle(artifact: WorkItemRuntimeArtifact | null): string {
  if (!artifact) return "Artifact preview";
  return `${artifact.name} · ${artifact.source === "step" ? "step artifact" : "task-cycle artifact"}`;
}

export function TaskCycleRuntimeDialog({
  workItemId,
  open,
  onOpenChange,
}: TaskCycleRuntimeDialogProps) {
  const { data: runtime, isLoading } = useWorkItemRuntime(open ? workItemId ?? undefined : undefined);
  const allArtifacts = useMemo(
    () => runtime?.stage_runs.flatMap((stageRun) => stageRun.artifacts.filter((artifact) => artifact.exists)) ?? [],
    [runtime]
  );
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setSelectedArtifactId(null);
      return;
    }
    if (!allArtifacts.length) {
      setSelectedArtifactId(null);
      return;
    }
    if (!selectedArtifactId || !allArtifacts.some((artifact) => artifact.id === selectedArtifactId)) {
      setSelectedArtifactId(allArtifacts[0].id);
    }
  }, [allArtifacts, open, selectedArtifactId]);

  const selectedArtifact =
    allArtifacts.find((artifact) => artifact.id === selectedArtifactId) ?? allArtifacts[0] ?? null;

  const taskCycleArtifactContent = useWorkItemArtifactContent(
    runtime?.work_item.id,
    selectedArtifact?.content_source === "work_item" ? selectedArtifact.content_id ?? null : null,
    open && selectedArtifact?.content_source === "work_item"
  );
  const stepArtifactContent = useStepArtifactContent(
    runtime?.work_item.id,
    selectedArtifact?.content_source === "step" ? selectedArtifact.content_id ?? undefined : undefined
  );

  const previewContent =
    selectedArtifact?.content_source === "work_item"
      ? taskCycleArtifactContent.data
      : stepArtifactContent.data;
  const previewLoading =
    selectedArtifact?.content_source === "work_item"
      ? taskCycleArtifactContent.isLoading
      : stepArtifactContent.isLoading;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="6xl" className="max-h-[90vh] overflow-hidden p-0">
        <DialogHeader className="border-b px-6 pt-6 pb-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-2">
              <DialogTitle>{runtime?.work_item.title ?? "Work Item Runtime"}</DialogTitle>
              <DialogDescription>
                {runtime
                  ? `${runtime.active_stage_label} · ${runtime.active_stage_status.replace(/_/g, " ")}`
                  : "Loading runtime projection"}
              </DialogDescription>
            </div>
            {runtime && (
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill status={runtime.active_stage_status} size="sm" />
                <Badge variant="outline">Stage: {runtime.active_stage_label}</Badge>
                <Link href={`/protocols/${runtime.work_item.protocol_run_id}`}>
                  <Badge variant="secondary" className="gap-1">
                    <GitBranch className="h-3 w-3" />
                    Protocol {runtime.work_item.protocol_run_id}
                    <ExternalLink className="h-3 w-3" />
                  </Badge>
                </Link>
              </div>
            )}
          </div>
        </DialogHeader>

        <ScrollArea className="h-[calc(90vh-92px)]">
          <div className="px-6 py-5">
            {isLoading || !runtime ? (
              <LoadingState message="Loading work-item runtime..." />
            ) : (
              <Tabs defaultValue="overview" className="gap-4">
                <TabsList>
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="timeline">Timeline</TabsTrigger>
                  <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
                  <TabsTrigger value="activity">Activity</TabsTrigger>
                  <TabsTrigger value="technical">Technical</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-4">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Current Stage</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-lg font-semibold">{runtime.active_stage_label}</div>
                        <div className="text-muted-foreground text-sm">{runtime.progress_summary}</div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Owner</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-lg font-semibold">
                          {runtime.work_item.owner_agent ?? "Unassigned"}
                        </div>
                        <div className="text-muted-foreground text-sm">
                          Iteration {runtime.work_item.iteration_count}/{runtime.work_item.max_iterations}
                        </div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Latest Completed</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-lg font-semibold">
                          {runtime.latest_completed_stage
                            ? runtime.latest_completed_stage.replace(/_/g, " ")
                            : "Nothing complete yet"}
                        </div>
                        <div className="text-muted-foreground text-sm">
                          {runtime.work_item.latest_artifact_summary ?? "No artifact summary yet"}
                        </div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Blockers</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-lg font-semibold">{runtime.blocking_reasons.length}</div>
                        <div className="text-muted-foreground text-sm">
                          {runtime.blocking_reasons[0] ?? "No active blockers"}
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  {runtime.blocking_reasons.length > 0 && (
                    <Alert variant="destructive">
                      <ShieldAlert className="h-4 w-4" />
                      <AlertTitle>Blocking Conditions</AlertTitle>
                      <AlertDescription>
                        <ul className="space-y-1">
                          {runtime.blocking_reasons.map((reason) => (
                            <li key={reason}>{reason}</li>
                          ))}
                        </ul>
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Active Agents</CardTitle>
                        <CardDescription>Agents responsible for the current stage</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {runtime.active_agents.length === 0 ? (
                          <div className="text-muted-foreground text-sm">No active agents projected.</div>
                        ) : (
                          runtime.active_agents.map((agent) => (
                            <div
                              key={`${agent.role}-${agent.agent_id}`}
                              className="flex items-center justify-between rounded-lg border p-3"
                            >
                              <div className="space-y-1">
                                <div className="flex items-center gap-2 font-medium">
                                  <Bot className="h-4 w-4" />
                                  {agent.agent_id}
                                </div>
                                <div className="text-muted-foreground text-sm capitalize">
                                  {agent.role.replace(/_/g, " ")}
                                </div>
                                {(agent.model_override || agent.reasoning_effort) && (
                                  <div className="text-muted-foreground text-xs">
                                    {[agent.model_override, agent.reasoning_effort]
                                      .filter(Boolean)
                                      .join(" · ")}
                                  </div>
                                )}
                              </div>
                              <StatusPill status={agent.status} size="sm" />
                            </div>
                          ))
                        )}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Latest Artifacts</CardTitle>
                        <CardDescription>Newest stage outputs across the task cycle</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        {runtime.latest_artifacts.length === 0 ? (
                          <div className="text-muted-foreground text-sm">No artifacts yet.</div>
                        ) : (
                          runtime.latest_artifacts.slice(0, 6).map((artifact) => (
                            <button
                              key={artifact.id}
                              type="button"
                              className="hover:bg-muted/50 flex w-full items-start justify-between rounded-lg border p-3 text-left"
                              onClick={() => setSelectedArtifactId(artifact.id)}
                            >
                              <div>
                                <div className="font-medium">{artifact.name}</div>
                                <div className="text-muted-foreground text-xs">
                                  {artifact.stage_id.replace(/_/g, " ")} · {formatDate(artifact.created_at)}
                                </div>
                              </div>
                              <Badge variant="outline">{artifact.type}</Badge>
                            </button>
                          ))
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="timeline" className="space-y-3">
                  {runtime.stage_runs.map((stageRun) => (
                    <Card key={stageRun.stage_id}>
                      <CardHeader className="pb-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <CardTitle className="text-base">{stageRun.stage_name}</CardTitle>
                            <CardDescription>{stageRun.summary}</CardDescription>
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            {stageRun.mode && <Badge variant="outline">{stageRun.mode.replace(/_/g, " ")}</Badge>}
                            <StatusPill status={stageRun.status} size="sm" />
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-muted-foreground">Started:</span>{" "}
                            {formatDate(stageRun.started_at)}
                          </div>
                          <div>
                            <span className="text-muted-foreground">Finished:</span>{" "}
                            {formatDate(stageRun.finished_at)}
                          </div>
                          <div>
                            <span className="text-muted-foreground">Artifacts:</span>{" "}
                            {stageRun.artifacts.filter((artifact) => artifact.exists).length}
                          </div>
                          {stageRun.run_ids.length > 0 && (
                            <div>
                              <span className="text-muted-foreground">Run IDs:</span>{" "}
                              {stageRun.run_ids.join(", ")}
                            </div>
                          )}
                          {stageRun.windmill_job_id && (
                            <div>
                              <span className="text-muted-foreground">Windmill:</span>{" "}
                              {stageRun.windmill_job_id}
                              {stageRun.windmill_module_id ? ` · ${stageRun.windmill_module_id}` : ""}
                            </div>
                          )}
                        </div>
                        <div className="space-y-2">
                          {stageRun.agent_assignments.length > 0 && (
                            <div className="rounded-lg border p-3">
                              <div className="mb-2 text-sm font-medium">Assigned Agents</div>
                              <div className="space-y-2">
                                {stageRun.agent_assignments.map((agent) => (
                                  <div
                                    key={`${stageRun.stage_id}-${agent.agent_id}-${agent.role}`}
                                    className="flex items-center justify-between text-sm"
                                  >
                                    <span>{agent.agent_id}</span>
                                    <Badge variant="outline">{agent.role}</Badge>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {stageRun.blocking_reasons.length > 0 && (
                            <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                              <div className="mb-2 text-sm font-medium text-red-700">Blocking reasons</div>
                              <div className="space-y-1 text-sm text-red-700">
                                {stageRun.blocking_reasons.map((reason) => (
                                  <div key={reason}>{reason}</div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </TabsContent>

                <TabsContent value="artifacts">
                  <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Artifacts by Stage</CardTitle>
                        <CardDescription>Select an artifact to preview its contents</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {runtime.stage_runs.map((stageRun) => {
                          const visibleArtifacts = stageRun.artifacts.filter((artifact) => artifact.exists);
                          return (
                            <div key={stageRun.stage_id} className="space-y-2">
                              <div className="flex items-center justify-between">
                                <div className="font-medium">{stageRun.stage_name}</div>
                                <Badge variant="outline">{visibleArtifacts.length}</Badge>
                              </div>
                              {visibleArtifacts.length === 0 ? (
                                <div className="text-muted-foreground text-sm">No artifacts</div>
                              ) : (
                                visibleArtifacts.map((artifact) => (
                                  <button
                                    key={artifact.id}
                                    type="button"
                                    className="hover:bg-muted/50 w-full rounded-lg border p-3 text-left"
                                    onClick={() => setSelectedArtifactId(artifact.id)}
                                  >
                                    <div className="flex items-start justify-between gap-2">
                                      <div className="space-y-1">
                                        <div className="font-medium">{artifact.name}</div>
                                        <div className="text-muted-foreground text-xs">
                                          {formatDate(artifact.created_at)}
                                        </div>
                                      </div>
                                      <Badge variant="secondary">{artifact.type}</Badge>
                                    </div>
                                  </button>
                                ))
                              )}
                            </div>
                          );
                        })}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Artifact Preview</CardTitle>
                        <CardDescription>{artifactPreviewTitle(selectedArtifact)}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {!selectedArtifact ? (
                          <div className="text-muted-foreground text-sm">Select an artifact to preview it.</div>
                        ) : previewLoading ? (
                          <LoadingState message="Loading artifact preview..." />
                        ) : previewContent ? (
                          <CodeBlock
                            code={previewContent.content}
                            language={selectedArtifact.type === "json" ? "json" : "text"}
                            maxHeight="520px"
                          />
                        ) : (
                          <Alert>
                            <FileText className="h-4 w-4" />
                            <AlertTitle>No preview available</AlertTitle>
                            <AlertDescription>
                              This artifact exists but its preview endpoint returned no content.
                            </AlertDescription>
                          </Alert>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="activity">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Runtime Activity</CardTitle>
                      <CardDescription>Derived stage, artifact, and Windmill updates</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {runtime.activity.length === 0 ? (
                        <div className="text-muted-foreground text-sm">No runtime activity available.</div>
                      ) : (
                        runtime.activity.map((item) => (
                          <div key={item.id} className="flex gap-3 rounded-lg border p-3">
                            <div className="mt-0.5">
                              {item.kind === "blocker" ? (
                                <AlertCircle className="h-4 w-4 text-red-600" />
                              ) : item.kind === "artifact" ? (
                                <FileText className="h-4 w-4 text-blue-600" />
                              ) : (
                                <Layers3 className="h-4 w-4 text-muted-foreground" />
                              )}
                            </div>
                            <div className="min-w-0 flex-1 space-y-1">
                              <div className="text-sm font-medium">{item.message}</div>
                              <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-xs">
                                {item.stage_id && <span>{item.stage_id.replace(/_/g, " ")}</span>}
                                {item.agent_id && <span>Agent: {item.agent_id}</span>}
                                {item.run_id && <span>Run: {item.run_id}</span>}
                                {item.windmill_job_id && <span>Windmill: {item.windmill_job_id}</span>}
                                {item.created_at && <span>{formatDate(item.created_at)}</span>}
                              </div>
                            </div>
                            {item.status && <StatusPill status={item.status} size="sm" />}
                          </div>
                        ))
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="technical">
                  <div className="grid gap-4 lg:grid-cols-2">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Protocol Linkage</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3 text-sm">
                        <div>
                          <span className="text-muted-foreground">Protocol run:</span>{" "}
                          {runtime.work_item.protocol_run_id}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Step run:</span> {runtime.work_item.id}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Lifecycle:</span>{" "}
                          {runtime.work_item.lifecycle_state}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Task dir:</span>{" "}
                          <span className="break-all">{runtime.work_item.task_dir ?? "Not available"}</span>
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Windmill Detail</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3 text-sm">
                        <div>
                          <span className="text-muted-foreground">Flow:</span>{" "}
                          {runtime.windmill?.flow_id ?? "Not linked"}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Job:</span>{" "}
                          {runtime.windmill?.job_id ?? "Not linked"}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Module:</span>{" "}
                          {runtime.windmill?.module_id ?? "Not available"}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Run ID:</span>{" "}
                          {runtime.windmill?.run_id ?? "Not available"}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>
              </Tabs>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
