"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { ArrowLeft, ExternalLink, FileText, ListTodo, Package, Target } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { StatusPill } from "@/components/ui/status-pill";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRun, useRunArtifacts,useRunLogs } from "@/lib/api";
import {
  formatBytes,
  formatCost,
  formatDateTime,
  formatDuration,
  formatTokens,
} from "@/lib/format";

export default function RunDetailPage() {
  const params = useParams();
  const runIdParam = params?.runId;
  const runId = Array.isArray(runIdParam) ? runIdParam[0] : runIdParam;
  const { data: run, isLoading: runLoading, error: runError } = useRun(runId);
  const { data: logs, isLoading: logsLoading } = useRunLogs(run ? runId : undefined);
  const { data: artifacts, isLoading: artifactsLoading } = useRunArtifacts(run ? runId : undefined);

  const linkedTask = {
    id: 42,
    title: "Implement user authentication",
    sprint: "Sprint 3",
    status: "in_progress",
    storyPoints: 5,
  };

  if (!runId || runLoading) return <LoadingState message="Loading run..." />;
  if (runError) {
    const message = runError instanceof Error ? runError.message : "Run not found";
    return (
      <div className="container py-8">
        <EmptyState title="Run not found" description={message} />
      </div>
    );
  }
  if (!run) return <LoadingState message="Run not found" />;

  return (
    <div className="container py-8">
      <div className="mb-6">
        <Link
          href="/runs"
          className="text-muted-foreground hover:text-foreground mb-4 inline-flex items-center gap-1 text-sm"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Runs
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-3 text-2xl font-bold">
              <span className="font-mono">{run.run_id.slice(0, 16)}...</span>
              <StatusPill status={run.status} />
            </h1>
            <p className="text-muted-foreground mt-1 flex items-center gap-2">
              <span className="font-mono">{run.job_type}</span>
              <span className="text-muted-foreground">•</span>
              <span className="capitalize">{run.run_kind}</span>
              {run.worker_id && (
                <>
                  <span className="text-muted-foreground">•</span>
                  <span>Worker: {run.worker_id}</span>
                </>
              )}
            </p>
            <div className="mt-2 flex items-center gap-2 text-sm">
              <ListTodo className="h-4 w-4 text-blue-400" />
              <span className="text-muted-foreground">Linked Task:</span>
              <Link
                href={`/sprints?task=${linkedTask.id}`}
                className="text-blue-400 hover:underline"
              >
                {linkedTask.title}
              </Link>
              <span className="text-muted-foreground">•</span>
              <Target className="h-3 w-3 text-purple-400" />
              <span className="text-muted-foreground">{linkedTask.sprint}</span>
              <span className="text-muted-foreground">• {linkedTask.storyPoints} pts</span>
            </div>
          </div>

          <div className="flex gap-2">
            {run.project_id && (
              <Link href={`/projects/${run.project_id}`}>
                <Button variant="outline" size="sm">
                  Project
                  <ExternalLink className="ml-2 h-3 w-3" />
                </Button>
              </Link>
            )}
            {run.protocol_run_id && (
              <Link href={`/protocols/${run.protocol_run_id}`}>
                <Button variant="outline" size="sm">
                  Protocol
                  <ExternalLink className="ml-2 h-3 w-3" />
                </Button>
              </Link>
            )}
            {run.step_run_id && (
              <Link href={`/steps/${run.step_run_id}`}>
                <Button variant="outline" size="sm">
                  Step
                  <ExternalLink className="ml-2 h-3 w-3" />
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="mb-8 grid gap-4 md:grid-cols-6">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Status</CardDescription>
          </CardHeader>
          <CardContent>
            <StatusPill status={run.status} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Attempt</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="font-medium">{run.attempt}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Queue</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="font-medium">{run.queue || "-"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Duration</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="font-medium">
              {run.started_at ? formatDuration(run.started_at, run.finished_at) : "-"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Tokens</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="font-medium">{formatTokens(run.cost_tokens)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Cost</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="font-medium">{formatCost(run.cost_cents)}</p>
          </CardContent>
        </Card>
      </div>

      <div className="mb-8 grid gap-4 text-sm md:grid-cols-3">
        <div>
          <span className="text-muted-foreground">Created:</span> {formatDateTime(run.created_at)}
        </div>
        <div>
          <span className="text-muted-foreground">Started:</span> {formatDateTime(run.started_at)}
        </div>
        <div>
          <span className="text-muted-foreground">Finished:</span> {formatDateTime(run.finished_at)}
        </div>
      </div>

      <Tabs defaultValue="params" className="space-y-4">
        <TabsList>
          <TabsTrigger value="params">Params</TabsTrigger>
          <TabsTrigger value="result">Result</TabsTrigger>
          {run.error && <TabsTrigger value="error">Error</TabsTrigger>}
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts ({artifacts?.length || 0})</TabsTrigger>
          <TabsTrigger value="agile">Agile Context</TabsTrigger>
        </TabsList>

        <TabsContent value="params">
          <Card>
            <CardHeader>
              <CardTitle>Parameters</CardTitle>
              {run.prompt_version && (
                <CardDescription>Prompt Version: {run.prompt_version}</CardDescription>
              )}
            </CardHeader>
            <CardContent>
              {run.params ? (
                <CodeBlock code={run.params} maxHeight="400px" />
              ) : (
                <EmptyState title="No parameters" description="This run has no parameters." />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="result">
          <Card>
            <CardHeader>
              <CardTitle>Result</CardTitle>
            </CardHeader>
            <CardContent>
              {run.result ? (
                <CodeBlock code={run.result} maxHeight="500px" />
              ) : (
                <EmptyState title="No result" description="This run has no result data." />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {run.error && (
          <TabsContent value="error">
            <Card className="border-destructive/50">
              <CardHeader>
                <CardTitle className="text-destructive">Error</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-destructive bg-destructive/10 rounded-lg p-4 text-sm whitespace-pre-wrap">
                  {run.error}
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
        )}

        <TabsContent value="logs">
          <Card>
            <CardHeader>
              <CardTitle>Execution Logs</CardTitle>
              {run.log_path && <CardDescription>Path: {run.log_path}</CardDescription>}
            </CardHeader>
            <CardContent>
              {logsLoading ? (
                <LoadingState message="Loading logs..." />
              ) : logs?.content ? (
                <pre className="bg-muted max-h-96 overflow-auto rounded-lg p-4 font-mono text-sm whitespace-pre-wrap">
                  {logs.content}
                </pre>
              ) : (
                <EmptyState
                  icon={FileText}
                  title="No logs available"
                  description="Logs have not been recorded for this run."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="artifacts">
          <Card>
            <CardHeader>
              <CardTitle>Artifacts</CardTitle>
              <CardDescription>{artifacts?.length || 0} artifact(s)</CardDescription>
            </CardHeader>
            <CardContent>
              {artifactsLoading ? (
                <LoadingState message="Loading artifacts..." />
              ) : !artifacts || artifacts.length === 0 ? (
                <EmptyState
                  icon={Package}
                  title="No artifacts"
                  description="No artifacts for this run."
                />
              ) : (
                <div className="space-y-2">
                  {artifacts.map((artifact) => (
                    <div
                      key={artifact.id}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="flex items-center gap-3">
                        <Package className="text-muted-foreground h-4 w-4" />
                        <div>
                          <p className="font-medium">{artifact.name}</p>
                          <p className="text-muted-foreground text-sm">
                            {artifact.kind} • {formatBytes(artifact.bytes)}
                          </p>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        View
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="agile">
          <Card>
            <CardHeader>
              <CardTitle>Agile Context</CardTitle>
              <CardDescription>Sprint and task information for this run</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-muted/50 rounded-lg border p-4">
                <div className="mb-3 flex items-center gap-2">
                  <ListTodo className="h-5 w-5 text-blue-400" />
                  <h3 className="font-semibold">Linked Task</h3>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Title:</span>
                    <Link
                      href={`/sprints?task=${linkedTask.id}`}
                      className="text-blue-400 hover:underline"
                    >
                      {linkedTask.title}
                    </Link>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Sprint:</span>
                    <span>{linkedTask.sprint}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Status:</span>
                    <StatusPill status={linkedTask.status} size="sm" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Story Points:</span>
                    <span className="font-medium">{linkedTask.storyPoints}</span>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border p-4">
                <h3 className="mb-2 font-semibold">Sprint Progress</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Total Tasks:</span>
                    <span>12</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Completed:</span>
                    <span className="text-green-400">7</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Velocity:</span>
                    <span>34 points</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
