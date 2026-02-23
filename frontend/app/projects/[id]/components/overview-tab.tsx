"use client";

import type React from "react";
import { useMemo, useState } from "react";
import Link from "next/link";

import {
  Activity,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Cloud,
  FileCode2,
  FileSearch,
  FolderOpen,
  GitCommit,
  GitPullRequest,
  Lightbulb,
  MessageCircle,
  MessageSquare,
  PlayCircle,
  Shield,
  Wand2,
  Workflow,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { SpecWorkflow } from "@/components/speckit";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingState } from "@/components/ui/loading-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { StatusPill } from "@/components/ui/status-pill";
import { Textarea } from "@/components/ui/textarea";
import {
  useAnalyzeSpec,
  useClarifySpec,
  useCreateProtocol,
  useGenerateChecklist,
  useOnboarding,
  usePolicyFindings,
  useProject,
  useProjectCommits,
  useProjectProtocols,
  useProjectPulls,
  useRunImplement,
  useSpecKitStatus,
} from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";

interface OverviewTabProps {
  projectId: number;
}

export function OverviewTab({ projectId }: OverviewTabProps) {
  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: onboarding, isLoading: onboardingLoading } = useOnboarding(projectId);
  const { data: protocols } = useProjectProtocols(projectId);
  const { data: specKitStatus } = useSpecKitStatus(projectId);
  const { data: policyFindings } = usePolicyFindings(projectId);
  const { data: commits } = useProjectCommits(projectId);
  const { data: pulls } = useProjectPulls(projectId);
  const [isCreateProtocolOpen, setIsCreateProtocolOpen] = useState(false);
  const [selectedSpecPath, setSelectedSpecPath] = useState("");
  const [clarifyOpen, setClarifyOpen] = useState(false);
  const [clarifyQuestion, setClarifyQuestion] = useState("");
  const [clarifyAnswer, setClarifyAnswer] = useState("");
  const [clarifyNotes, setClarifyNotes] = useState("");
  const clarifySpec = useClarifySpec();
  const generateChecklist = useGenerateChecklist();
  const analyzeSpec = useAnalyzeSpec();
  const runImplement = useRunImplement();

  const specOptions = useMemo(
    () =>
      (specKitStatus?.specs ?? []).filter((s) => s.status !== "cleaned" && (s.spec_path || s.path)),
    [specKitStatus]
  );
  const activeSpecPath =
    selectedSpecPath || specOptions[0]?.spec_path || specOptions[0]?.path || "";
  const workflowStatus = useMemo(() => {
    const hasSpec = (specKitStatus?.spec_count || 0) > 0;
    const hasPlan = specOptions.some((spec) => spec.has_plan);
    const hasTasks = specOptions.some((spec) => spec.has_tasks);
    return {
      spec: hasSpec ? "completed" : "pending",
      clarify: hasSpec ? "in-progress" : "pending",
      plan: hasPlan ? "completed" : "pending",
      checklist: hasPlan ? "in-progress" : "pending",
      tasks: hasTasks ? "completed" : "pending",
      analyze: hasTasks ? "in-progress" : "pending",
      implement: hasTasks ? "in-progress" : "pending",
      sprint: "pending",
    } as const;
  }, [specKitStatus, specOptions]);

  if (projectLoading || onboardingLoading) return <LoadingState message="Loading overview..." />;

  const handleClarify = async () => {
    if (!activeSpecPath) {
      toast.error("Select a specification to clarify");
      return;
    }

    const hasEntry = clarifyQuestion.trim() && clarifyAnswer.trim();
    const hasNotes = clarifyNotes.trim();
    const specMeta = specOptions.find(
      (spec) => spec.spec_path === activeSpecPath || spec.path === activeSpecPath
    );

    if (!hasEntry && !hasNotes) {
      toast.error("Provide a question/answer or notes");
      return;
    }

    try {
      const result = await clarifySpec.mutateAsync({
        project_id: projectId,
        spec_path: activeSpecPath,
        entries: hasEntry
          ? [{ question: clarifyQuestion.trim(), answer: clarifyAnswer.trim() }]
          : [],
        notes: hasNotes ? clarifyNotes.trim() : undefined,
        spec_run_id: specMeta?.spec_run_id ?? undefined,
      });
      if (result.success) {
        toast.success(`Clarifications added (${result.clarifications_added})`);
        setClarifyOpen(false);
        setClarifyQuestion("");
        setClarifyAnswer("");
        setClarifyNotes("");
      } else {
        toast.error(result.error || "Clarification failed");
      }
    } catch {
      toast.error("Clarification failed");
    }
  };

  const handleChecklist = async () => {
    if (!activeSpecPath) {
      toast.error("Select a specification to run checklist");
      return;
    }

    const specMeta = specOptions.find(
      (spec) => spec.spec_path === activeSpecPath || spec.path === activeSpecPath
    );
    try {
      const result = await generateChecklist.mutateAsync({
        project_id: projectId,
        spec_path: activeSpecPath,
        spec_run_id: specMeta?.spec_run_id ?? undefined,
      });
      if (result.success) {
        toast.success(`Checklist generated (${result.item_count} items)`);
      } else {
        toast.error(result.error || "Checklist generation failed");
      }
    } catch {
      toast.error("Checklist generation failed");
    }
  };

  const handleAnalyze = async () => {
    if (!activeSpecPath) {
      toast.error("Select a specification to analyze");
      return;
    }

    const specMeta = specOptions.find(
      (spec) => spec.spec_path === activeSpecPath || spec.path === activeSpecPath
    );
    try {
      const result = await analyzeSpec.mutateAsync({
        project_id: projectId,
        spec_path: activeSpecPath,
        plan_path: specMeta?.plan_path || undefined,
        tasks_path: specMeta?.tasks_path || undefined,
        spec_run_id: specMeta?.spec_run_id ?? undefined,
      });
      if (result.success) {
        toast.success("Analysis report generated");
      } else {
        toast.error(result.error || "Analysis failed");
      }
    } catch {
      toast.error("Analysis failed");
    }
  };

  const handleImplement = async () => {
    if (!activeSpecPath) {
      toast.error("Select a specification to implement");
      return;
    }

    const specMeta = specOptions.find(
      (spec) => spec.spec_path === activeSpecPath || spec.path === activeSpecPath
    );
    try {
      const result = await runImplement.mutateAsync({
        project_id: projectId,
        spec_path: activeSpecPath,
        spec_run_id: specMeta?.spec_run_id ?? undefined,
      });
      if (result.success) {
        toast.success("Implementation run initialized");
      } else {
        toast.error(result.error || "Implement init failed");
      }
    } catch {
      toast.error("Implement init failed");
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-card/50 flex flex-wrap items-center gap-6 rounded-lg border p-4 backdrop-blur">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-blue-500" />
          <span className="text-muted-foreground text-xs tracking-wider uppercase">
            Onboarding:
          </span>
          {onboarding ? (
            <StatusPill status={onboarding.status} size="sm" />
          ) : (
            <span className="text-muted-foreground text-sm">not started</span>
          )}
        </div>

        <Separator orientation="vertical" className="h-6" />

        <div className="flex items-center gap-2">
          <Workflow className="h-4 w-4 text-purple-500" />
          <span className="text-muted-foreground text-xs tracking-wider uppercase">Protocols:</span>
          <span className="text-sm font-semibold">{protocols?.length || 0}</span>
        </div>

        <Separator orientation="vertical" className="h-6" />

        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-green-500" />
          <span className="text-muted-foreground text-xs tracking-wider uppercase">
            Policy Pack:
          </span>
          <code className="bg-muted rounded px-1.5 py-0.5 font-mono text-xs">
            {project?.policy_pack_key || "none"}
          </code>
        </div>

        <Separator orientation="vertical" className="h-6" />

        <div className="flex items-center gap-2">
          <MessageCircle className="h-4 w-4 text-amber-500" />
          <span className="text-muted-foreground text-xs tracking-wider uppercase">Blockers:</span>
          <span className="text-sm font-semibold">{onboarding?.blocking_clarifications || 0}</span>
        </div>

        <Separator orientation="vertical" className="h-6" />

        <div className="flex items-center gap-2">
          {project?.local_path ? (
            <>
              <FolderOpen className="h-4 w-4 text-green-500" />
              <span className="text-muted-foreground text-xs tracking-wider uppercase">Repo:</span>
              <span className="text-sm text-green-600">Local</span>
            </>
          ) : (
            <>
              <Cloud className="text-muted-foreground h-4 w-4" />
              <span className="text-muted-foreground text-xs tracking-wider uppercase">Repo:</span>
              <span className="text-muted-foreground text-sm">Remote</span>
            </>
          )}
        </div>
      </div>

      <SpecWorkflow projectId={projectId} stepStatus={workflowStatus} showActions />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <GitCommit className="text-muted-foreground h-4 w-4" />
              Last Commit
            </CardTitle>
          </CardHeader>
          <CardContent>
            {commits && commits.length > 0 ? (
              <div className="space-y-1">
                <p className="truncate font-mono text-sm">{commits[0].sha.slice(0, 7)}</p>
                <p className="text-muted-foreground truncate text-xs">{commits[0].message}</p>
                <p className="text-muted-foreground text-xs">
                  {formatRelativeTime(commits[0].date)}
                </p>
              </div>
            ) : (
              <p className="text-muted-foreground text-xs">No commits</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <GitPullRequest className="text-muted-foreground h-4 w-4" />
              Open PRs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {pulls?.filter((p) => p.status === "open").length || 0}
            </p>
            <p className="text-muted-foreground text-xs">
              {pulls && pulls.length > 0 ? (
                <Link href={`/projects/${projectId}?tab=branches`} className="hover:underline">
                  View all →
                </Link>
              ) : (
                "No pull requests"
              )}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Shield className="text-muted-foreground h-4 w-4" />
              Policy Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            {policyFindings && policyFindings.length > 0 ? (
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  {policyFindings.some((f) => f.severity === "error") ? (
                    <XCircle className="h-4 w-4 text-red-500" />
                  ) : policyFindings.some((f) => f.severity === "warning") ? (
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  )}
                  <span className="text-sm font-medium">{policyFindings.length} findings</span>
                </div>
                <div className="flex gap-2 text-xs">
                  {policyFindings.filter((f) => f.severity === "error").length > 0 && (
                    <Badge variant="destructive" className="h-5">
                      {policyFindings.filter((f) => f.severity === "error").length} errors
                    </Badge>
                  )}
                  {policyFindings.filter((f) => f.severity === "warning").length > 0 && (
                    <Badge variant="secondary" className="h-5">
                      {policyFindings.filter((f) => f.severity === "warning").length} warnings
                    </Badge>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <span className="text-sm">No issues</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Workflow className="text-muted-foreground h-4 w-4" />
              Running
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {protocols?.filter((p) => p.status === "running").length || 0}
            </p>
            <p className="text-muted-foreground text-xs">
              {protocols?.filter((p) => p.status === "failed").length || 0} failed
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks for this project</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button variant="outline" className="w-full justify-start bg-transparent" asChild>
              <Link href={`/projects/${projectId}?wizard=implement-feature`}>
                <Wand2 className="mr-2 h-4 w-4" />
                Implement a Feature
              </Link>
            </Button>
            <Button variant="outline" className="w-full justify-start bg-transparent" asChild>
              <Link href={`/projects/${projectId}?wizard=generate-specs`}>
                <FileCode2 className="mr-2 h-4 w-4" />
                Generate Specs Wizard
              </Link>
            </Button>
            <Button variant="outline" className="w-full justify-start bg-transparent" asChild>
              <Link href={`/projects/${projectId}?wizard=design-solution`}>
                <Lightbulb className="mr-2 h-4 w-4" />
                Design A Solution
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>SpecKit Actions</CardTitle>
            <CardDescription>Quick access to clarify/checklist/analyze/implement</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="spec-select">Active Spec</Label>
              <Select value={selectedSpecPath} onValueChange={setSelectedSpecPath}>
                <SelectTrigger id="spec-select">
                  <SelectValue placeholder="Select a spec" />
                </SelectTrigger>
                <SelectContent>
                  {specOptions.length === 0 && (
                    <SelectItem value="__no_specs__" disabled>
                      No specs available
                    </SelectItem>
                  )}
                  {specOptions.map((spec) => (
                    <SelectItem key={spec.path} value={spec.spec_path || spec.path}>
                      {spec.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setClarifyOpen(true)}
                disabled={!activeSpecPath}
              >
                <MessageSquare className="mr-2 h-4 w-4" />
                Clarify
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleChecklist}
                disabled={!activeSpecPath}
              >
                <ClipboardCheck className="mr-2 h-4 w-4" />
                Checklist
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleAnalyze}
                disabled={!activeSpecPath}
              >
                <FileSearch className="mr-2 h-4 w-4" />
                Analyze
              </Button>
              <Button size="sm" onClick={handleImplement} disabled={!activeSpecPath}>
                <PlayCircle className="mr-2 h-4 w-4" />
                Implement
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Protocols</CardTitle>
            <CardDescription>Latest protocol activity</CardDescription>
          </CardHeader>
          <CardContent>
            {protocols && protocols.length > 0 ? (
              <div className="space-y-3">
                {protocols.slice(0, 3).map((protocol) => (
                  <Link
                    key={protocol.id}
                    href={`/protocols/${protocol.id}`}
                    className="hover:bg-accent flex items-center justify-between rounded-lg p-2 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <FileCode2 className="text-muted-foreground h-4 w-4" />
                      <div>
                        <p className="text-sm font-medium">{protocol.protocol_name}</p>
                        <p className="text-muted-foreground text-xs">
                          {formatRelativeTime(protocol.created_at)}
                        </p>
                      </div>
                    </div>
                    <StatusPill status={protocol.status} size="sm" />
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No protocols yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {onboarding && onboarding.blocking_clarifications > 0 && (
        <Card className="border-yellow-500/50 bg-yellow-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-yellow-500" />
              Attention Required
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">
              This project has {onboarding.blocking_clarifications} blocking clarification
              {onboarding.blocking_clarifications > 1 ? "s" : ""} that need your response.
            </p>
            <Button variant="outline" className="mt-4 bg-transparent" asChild>
              <Link href={`/projects/${projectId}?tab=clarifications`}>View Clarifications</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <CreateProtocolDialog
        projectId={projectId}
        open={isCreateProtocolOpen}
        onClose={() => setIsCreateProtocolOpen(false)}
      />

      <Dialog open={clarifyOpen} onOpenChange={setClarifyOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Clarify Specification</DialogTitle>
            <DialogDescription>
              Add a clarification entry or notes to the selected spec.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="clarify-question">Question (optional)</Label>
              <Input
                id="clarify-question"
                placeholder="What needs clarification?"
                value={clarifyQuestion}
                onChange={(event) => setClarifyQuestion(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="clarify-answer">Answer (optional)</Label>
              <Input
                id="clarify-answer"
                placeholder="Provide the resolved answer"
                value={clarifyAnswer}
                onChange={(event) => setClarifyAnswer(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="clarify-notes">Notes (optional)</Label>
              <Textarea
                id="clarify-notes"
                placeholder="Additional clarification notes"
                rows={4}
                value={clarifyNotes}
                onChange={(event) => setClarifyNotes(event.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setClarifyOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleClarify} disabled={clarifySpec.isPending}>
                {clarifySpec.isPending ? "Saving..." : "Save Clarification"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CreateProtocolDialog({
  projectId,
  open,
  onClose,
}: {
  projectId: number;
  open: boolean;
  onClose: () => void;
}) {
  const createProtocol = useCreateProtocol();
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    spec: "{}",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createProtocol.mutateAsync({
        projectId: projectId,
        data: {
          protocol_name: formData.name,
          description: formData.description || undefined,
        },
      });
      toast.success("Protocol created successfully");
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create protocol");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create New Protocol</DialogTitle>
          <DialogDescription>Define a new protocol for this project.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Protocol Name</Label>
              <Input
                id="name"
                placeholder="0001-feature-auth"
                value={formData.name}
                onChange={(e) => setFormData((p) => ({ ...p, name: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                placeholder="Implement authentication system"
                value={formData.description}
                onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="spec">Spec (JSON)</Label>
              <Textarea
                id="spec"
                className="min-h-48 font-mono text-sm"
                placeholder='{ "steps": [] }'
                value={formData.spec}
                onChange={(e) => setFormData((p) => ({ ...p, spec: e.target.value }))}
                required
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={createProtocol.isPending}>
              {createProtocol.isPending ? "Creating..." : "Create Protocol"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
