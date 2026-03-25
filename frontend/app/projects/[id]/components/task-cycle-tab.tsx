"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import {
  Archive,
  ArrowUpRight,
  Ban,
  CheckCircle2,
  FileSearch,
  FileText,
  GitBranch,
  Layers3,
  PlayCircle,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  useAgents,
  useArchiveWorkItem,
  useBuildContextWorkItem,
  useCancelWorkItem,
  useImplementWorkItem,
  useMarkPrReady,
  usePlanWorkItem,
  useProjectProtocols,
  useProjectTaskCycle,
  useQaWorkItem,
  useReassignWorkItemOwner,
  useRefactorWorkItem,
  useReviewWorkItem,
  useStartBrownfieldRun,
} from "@/lib/api";

import { TaskCycleRuntimeDialog } from "./task-cycle-runtime-dialog";

interface TaskCycleTabProps {
  projectId: number;
}

function toneClass(value: string | null | undefined): string {
  const normalized = (value || "").toLowerCase();
  if (["done", "completed", "ready", "approved", "passed", "available", "legacy"].includes(normalized)) {
    return "bg-green-500/10 text-green-700";
  }
  if (["passed_with_debt", "warning", "needs_refactor", "required"].includes(normalized)) {
    return "bg-yellow-500/10 text-yellow-700";
  }
  if (["failed", "blocked", "needs_changes", "missing", "needs_split"].includes(normalized)) {
    return "bg-red-500/10 text-red-700";
  }
  if (["running", "in_progress", "review", "pending"].includes(normalized)) {
    return "bg-yellow-500/10 text-yellow-700";
  }
  return "bg-blue-500/10 text-blue-700";
}

export function TaskCycleTab({ projectId }: TaskCycleTabProps) {
  const { data: protocols = [], isLoading: protocolsLoading } = useProjectProtocols(projectId);
  const { data: agents = [] } = useAgents(projectId);
  const [lifecycleFilter, setLifecycleFilter] = useState("active");
  const { data: workItems = [], isLoading: workItemsLoading } = useProjectTaskCycle(
    projectId,
    undefined,
    lifecycleFilter
  );
  const startBrownfieldRun = useStartBrownfieldRun();
  const buildContext = useBuildContextWorkItem();
  const planWorkItem = usePlanWorkItem();
  const implementWorkItem = useImplementWorkItem();
  const refactorWorkItem = useRefactorWorkItem();
  const reviewWorkItem = useReviewWorkItem();
  const qaWorkItem = useQaWorkItem();
  const markPrReady = useMarkPrReady();
  const archiveWorkItem = useArchiveWorkItem();
  const cancelWorkItem = useCancelWorkItem();
  const reassignWorkItemOwner = useReassignWorkItemOwner();

  const [featureName, setFeatureName] = useState("");
  const [featureRequest, setFeatureRequest] = useState("");
  const [ownerDrafts, setOwnerDrafts] = useState<Record<number, string>>({});
  const [selectedWorkItemId, setSelectedWorkItemId] = useState<number | null>(null);
  const [selectedRuntimeTab, setSelectedRuntimeTab] = useState<string>("overview");
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);

  const protocolNames = useMemo(
    () =>
      new Map(
        protocols.map((protocol) => [protocol.id, protocol.protocol_name || `Protocol ${protocol.id}`])
      ),
    [protocols]
  );
  const enabledAgents = useMemo(
    () => agents.filter((agent) => agent.enabled !== false),
    [agents]
  );
  const agentNameById = useMemo(
    () => new Map(enabledAgents.map((agent) => [agent.id, agent.name || agent.id])),
    [enabledAgents]
  );

  if (protocolsLoading || workItemsLoading) {
    return <LoadingState message="Loading task cycle..." />;
  }

  const openRuntime = (workItemId: number, tab = "overview", artifactId: string | null = null) => {
    setSelectedRuntimeTab(tab);
    setSelectedArtifactId(artifactId);
    setSelectedWorkItemId(workItemId);
  };

  const handleStart = async () => {
    const trimmedRequest = featureRequest.trim();
    if (!trimmedRequest) {
      toast.error("Describe the brownfield change before starting");
      return;
    }

    try {
      const result = await startBrownfieldRun.mutateAsync({
        projectId,
        data: {
          feature_request: trimmedRequest,
          feature_name: featureName.trim() || undefined,
        },
      });
      if (result.protocol) {
        toast.success(`Brownfield run created: ${result.protocol.protocol_name}`);
      } else {
        toast.success("Brownfield run created");
      }
      setFeatureRequest("");
      setFeatureName("");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to start brownfield run");
    }
  };

  const withToast = async (
    action: () => Promise<unknown>,
    successMessage: string,
    fallbackMessage: string
  ) => {
    try {
      await action();
      toast.success(successMessage);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : fallbackMessage);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold">Task Cycle</h3>
          <p className="text-muted-foreground text-sm">
            Run the brownfield discovery to work-item loop and move items through context,
            planning, implementation, review, QA, and PR readiness.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={lifecycleFilter} onValueChange={setLifecycleFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter lifecycle" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="active">Active only</SelectItem>
              <SelectItem value="all">All work items</SelectItem>
              <SelectItem value="archived">Archived only</SelectItem>
              <SelectItem value="canceled">Canceled only</SelectItem>
            </SelectContent>
          </Select>
          <Badge variant="secondary">{workItems.length} work items</Badge>
          <Badge variant="outline">{protocols.length} protocols</Badge>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Start Brownfield Run</CardTitle>
          <CardDescription>
            Seed a brownfield task-cycle protocol from a concrete feature request.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder="Feature name"
            value={featureName}
            onChange={(event) => setFeatureName(event.target.value)}
          />
          <Textarea
            placeholder="Describe the brownfield change, expected behavior, and constraints"
            value={featureRequest}
            onChange={(event) => setFeatureRequest(event.target.value)}
            rows={5}
          />
          <div className="flex justify-end">
            <Button onClick={handleStart} disabled={startBrownfieldRun.isPending}>
              <PlayCircle className="mr-2 h-4 w-4" />
              {startBrownfieldRun.isPending ? "Starting..." : "Start Brownfield Run"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Context Active</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {workItems.filter((item) => item.active_stage === "build_context").length}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Review / QA Active</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {workItems.filter((item) => ["review", "qa"].includes(item.active_stage ?? "")).length}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">PR Ready</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {workItems.filter((item) => item.pr_ready).length}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Work Items</CardTitle>
          <CardDescription>
            {lifecycleFilter === "active"
              ? "Active task-cycle work items for this project, across all linked protocols."
              : "Task-cycle work items for this project, including archived and canceled history."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {workItems.length === 0 ? (
            <div className="text-muted-foreground rounded-lg border border-dashed p-6 text-sm">
              No brownfield work items yet. Start a run above to create the first task-cycle
              protocol.
            </div>
          ) : (
            workItems.map((item) => (
              <div key={item.id} className="space-y-3 rounded-lg border p-4">
                {(() => {
                  const bootstrapRunning =
                    item.active_stage === "build_context" &&
                    item.active_stage_status === "running" &&
                    item.context_status === "missing";
                  const canBuildContext = !bootstrapRunning;
                  const canPlan = !bootstrapRunning && item.context_status === "ready";
                  const canImplement =
                    !bootstrapRunning &&
                    item.context_status === "ready" &&
                    item.plan_status === "ready";
                  const canReview =
                    !bootstrapRunning &&
                    item.context_status === "ready" &&
                    ["awaiting_review", "needs_rework", "needs_qa", "ready_for_pr"].includes(
                      item.status
                    );
                  const reviewPassed = ["passed", "passed_with_debt"].includes(item.review_status);
                  const reviewAllowsQa = ["passed", "passed_with_debt", "needs_refactor"].includes(
                    item.review_status
                  );
                  const canQa =
                    !bootstrapRunning && item.context_status === "ready" && reviewAllowsQa;
                  const canRefactor =
                    !bootstrapRunning &&
                    item.context_status === "ready" &&
                    item.review_status === "needs_refactor" &&
                    item.qa_status === "passed";
                  const canMarkPrReady =
                    !bootstrapRunning &&
                    item.context_status === "ready" &&
                    item.status === "ready_for_pr" &&
                    reviewPassed &&
                    item.qa_status === "passed";
                  const cardArtifacts = [
                    item.context_status === "ready"
                      ? { key: "context_pack_md", label: "context_pack.md" }
                      : null,
                    item.context_status === "ready"
                      ? { key: "context_pack_json", label: "context_pack.json" }
                      : null,
                    item.plan_status === "ready"
                      ? { key: "plan_pack_md", label: "plan_pack.md" }
                      : null,
                    item.plan_status === "ready"
                      ? { key: "plan_pack_json", label: "plan_pack.json" }
                      : null,
                    item.review_status !== "pending"
                      ? { key: "review_report_md", label: "review_report.md" }
                      : null,
                    item.review_status !== "pending"
                      ? { key: "review_report_json", label: "review_report.json" }
                      : null,
                    item.qa_status !== "pending"
                      ? { key: "test_report_md", label: "test_report.md" }
                      : null,
                    item.qa_status !== "pending"
                      ? { key: "test_report_json", label: "test_report.json" }
                      : null,
                    item.pr_ready || item.active_stage === "pr_ready" || item.latest_completed_stage === "PR Ready"
                      ? { key: "pr_ready_report_md", label: "pr_ready_report.md" }
                      : null,
                    item.pr_ready || item.active_stage === "pr_ready" || item.latest_completed_stage === "PR Ready"
                      ? { key: "pr_ready_report_json", label: "pr_ready_report.json" }
                      : null,
                  ].filter((artifact): artifact is { key: string; label: string } => Boolean(artifact));
                  return (
                    <>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="font-medium">{item.title}</h4>
                      <Badge className={toneClass(item.status)}>{item.status}</Badge>
                      {item.lifecycle_state !== "active" && (
                        <Badge variant="outline">{item.lifecycle_state}</Badge>
                      )}
                      {item.active_stage_label && (
                        <Badge className={toneClass(item.active_stage_status)}>
                          {item.active_stage_label}
                        </Badge>
                      )}
                      <Badge className={toneClass(item.context_status)}>
                        Context {item.context_status}
                      </Badge>
                      <Badge className={toneClass(item.plan_status)}>Plan {item.plan_status}</Badge>
                      <Badge className={toneClass(item.review_status)}>
                        Review {item.review_status}
                      </Badge>
                      <Badge className={toneClass(item.qa_status)}>QA {item.qa_status}</Badge>
                      <Badge className={toneClass(item.refactor_status)}>
                        Refactor {item.refactor_status}
                      </Badge>
                    </div>
                    {item.summary && !item.progress_summary && (
                      <p className="text-muted-foreground text-sm">{item.summary}</p>
                    )}
                    {item.progress_summary && (
                      <p className="text-sm font-medium">{item.progress_summary}</p>
                    )}
                    {item.lifecycle_reason && item.lifecycle_state !== "active" && (
                      <p className="text-muted-foreground text-sm">{item.lifecycle_reason}</p>
                    )}
                    {item.blocking_reason && item.lifecycle_state === "active" && (
                      <p className="text-sm text-red-700">{item.blocking_reason}</p>
                    )}
                    <div className="text-muted-foreground flex flex-wrap items-center gap-3 text-xs">
                      <span>Iterations: {item.iteration_count}/{item.max_iterations}</span>
                      <span>Clarifications: {item.blocking_clarifications}</span>
                      <span>Policy findings: {item.blocking_policy_findings}</span>
                      {item.owner_agent && <span>Owner: {item.owner_agent}</span>}
                      {item.latest_completed_stage && <span>Latest stage: {item.latest_completed_stage}</span>}
                      {item.latest_artifact_summary && (
                        <span>Latest artifact: {item.latest_artifact_summary}</span>
                      )}
                    </div>
                    {cardArtifacts.length > 0 && (
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        <span className="text-muted-foreground">Artifacts:</span>
                        {cardArtifacts.map((artifact) => (
                          <Button
                            key={artifact.key}
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            onClick={() => openRuntime(item.id, "artifacts", artifact.key)}
                          >
                            <FileText className="mr-1 h-3.5 w-3.5" />
                            {artifact.label}
                          </Button>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => openRuntime(item.id)}
                    >
                      <Layers3 className="mr-2 h-3.5 w-3.5" />
                      Runtime
                    </Button>
                    <Link href={`/protocols/${item.protocol_run_id}`}>
                      <Button variant="outline" size="sm">
                        <GitBranch className="mr-2 h-3.5 w-3.5" />
                        {protocolNames.get(item.protocol_run_id) || `Protocol ${item.protocol_run_id}`}
                        <ArrowUpRight className="ml-2 h-3.5 w-3.5" />
                      </Button>
                    </Link>
                    {item.pr_ready && (
                      <Badge variant="secondary" className="bg-green-500/10 text-green-700">
                        <CheckCircle2 className="mr-1 h-3 w-3" />
                        PR Ready
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-end gap-2">
                  <div className="min-w-[220px] space-y-1">
                    <div className="text-muted-foreground text-xs">Owner Agent</div>
                    <Select
                      value={ownerDrafts[item.id] ?? item.owner_agent ?? "__current_unset__"}
                      onValueChange={(value) =>
                        setOwnerDrafts((current) => ({ ...current, [item.id]: value }))
                      }
                      disabled={item.lifecycle_state !== "active"}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select owner agent" />
                      </SelectTrigger>
                      <SelectContent>
                        {!agentNameById.has(item.owner_agent || "") && item.owner_agent && (
                          <SelectItem value={item.owner_agent}>{item.owner_agent} (current)</SelectItem>
                        )}
                        {enabledAgents.map((agent) => (
                          <SelectItem key={agent.id} value={agent.id}>
                            {agent.name || agent.id}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={
                      item.lifecycle_state !== "active" ||
                      !(ownerDrafts[item.id] ?? item.owner_agent) ||
                      (ownerDrafts[item.id] ?? item.owner_agent) === item.owner_agent
                    }
                    onClick={() =>
                      withToast(
                        () =>
                          reassignWorkItemOwner.mutateAsync({
                            projectId,
                            workItemId: item.id,
                            protocolRunId: item.protocol_run_id,
                            data: {
                              owner_agent: ownerDrafts[item.id] ?? item.owner_agent ?? "",
                            },
                          }),
                        "Owner reassigned",
                        "Failed to reassign owner"
                      )
                    }
                  >
                    Save Owner
                  </Button>
                </div>

                {item.lifecycle_state === "active" ? (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!canBuildContext}
                      onClick={() =>
                        withToast(
                          () =>
                            buildContext.mutateAsync({
                              projectId,
                              workItemId: item.id,
                              protocolRunId: item.protocol_run_id,
                            }),
                          "Context pack refreshed",
                          "Failed to build context"
                        )
                      }
                    >
                      <FileSearch className="mr-2 h-3.5 w-3.5" />
                      Build Context
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!canPlan}
                      onClick={() =>
                        withToast(
                          () =>
                            planWorkItem.mutateAsync({
                              projectId,
                              workItemId: item.id,
                              protocolRunId: item.protocol_run_id,
                            }),
                          "Plan generated",
                          "Failed to generate plan"
                        )
                      }
                    >
                      <FileText className="mr-2 h-3.5 w-3.5" />
                      Plan
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!canImplement}
                      onClick={() =>
                        withToast(
                          () =>
                            implementWorkItem.mutateAsync({
                              projectId,
                              workItemId: item.id,
                              protocolRunId: item.protocol_run_id,
                            }),
                          "Implementation started",
                          "Failed to start implementation"
                        )
                      }
                    >
                      <Wrench className="mr-2 h-3.5 w-3.5" />
                      Implement
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!canReview}
                      onClick={() =>
                        withToast(
                          () =>
                            reviewWorkItem.mutateAsync({
                              projectId,
                              workItemId: item.id,
                              protocolRunId: item.protocol_run_id,
                            }),
                          "Review generated",
                          "Failed to run review"
                        )
                      }
                    >
                      Review
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!canQa}
                      onClick={() =>
                        withToast(
                          () =>
                            qaWorkItem.mutateAsync({
                              projectId,
                              workItemId: item.id,
                              protocolRunId: item.protocol_run_id,
                            }),
                          "QA completed",
                          "Failed to run QA"
                        )
                      }
                    >
                      <ShieldCheck className="mr-2 h-3.5 w-3.5" />
                      QA
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!canRefactor}
                      onClick={() =>
                        withToast(
                          () =>
                            refactorWorkItem.mutateAsync({
                              projectId,
                              workItemId: item.id,
                              protocolRunId: item.protocol_run_id,
                              data: { owner_agent: item.owner_agent },
                            }),
                          "Refactor started",
                          "Failed to start refactor"
                        )
                      }
                    >
                      <Wrench className="mr-2 h-3.5 w-3.5" />
                      Refactor
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!canMarkPrReady}
                      onClick={async () => {
                        try {
                          const result = await markPrReady.mutateAsync({
                            projectId,
                            workItemId: item.id,
                            protocolRunId: item.protocol_run_id,
                          });
                          if (result.pr_ready) {
                            toast.success("Marked PR ready and opened PR");
                            return;
                          }
                          toast.error(
                            result.blocking_reason || "PR-ready checks failed; rework is required"
                          );
                        } catch (error) {
                          toast.error(error instanceof Error ? error.message : "Failed to mark PR ready");
                        }
                      }}
                    >
                      Mark PR Ready
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        withToast(
                          () =>
                            archiveWorkItem.mutateAsync({
                              projectId,
                              workItemId: item.id,
                              protocolRunId: item.protocol_run_id,
                              data: {},
                            }),
                          "Work item archived",
                          "Failed to archive work item"
                        )
                      }
                    >
                      <Archive className="mr-2 h-3.5 w-3.5" />
                      Archive
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        withToast(
                          () =>
                            cancelWorkItem.mutateAsync({
                              projectId,
                              workItemId: item.id,
                              protocolRunId: item.protocol_run_id,
                              data: {},
                            }),
                          "Work item canceled",
                          "Failed to cancel work item"
                        )
                      }
                    >
                      <Ban className="mr-2 h-3.5 w-3.5" />
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <div className="text-muted-foreground text-sm">
                    This work item is {item.lifecycle_state} and is now read-only.
                  </div>
                )}
                    </>
                  );
                })()}
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <TaskCycleRuntimeDialog
        workItemId={selectedWorkItemId}
        open={selectedWorkItemId !== null}
        initialTab={selectedRuntimeTab}
        initialArtifactId={selectedArtifactId}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedWorkItemId(null);
            setSelectedRuntimeTab("overview");
            setSelectedArtifactId(null);
          }
        }}
      />
    </div>
  );
}
