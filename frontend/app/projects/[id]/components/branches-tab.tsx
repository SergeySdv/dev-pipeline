"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import type { ColumnDef } from "@tanstack/react-table";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileCode2,
  GitBranch,
  GitCommit,
  GitMerge,
  GitPullRequest,
  HelpCircle,
  Plus,
  Trash2,
  Workflow,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingState } from "@/components/ui/loading-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  useCreateBranch,
  useDeleteBranch,
  useProjectBranches,
  useProjectCommits,
  useProjectPulls,
  useProjectWorktrees,
} from "@/lib/api";
import type { Branch, Commit, PullRequest, Worktree } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface BranchesTabProps {
  projectId: number;
}

function formatCreatedAt(dateStr: string): string {
  if (!dateStr) return "";
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return "just now";
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    return date.toLocaleDateString();
  } catch {
    return dateStr;
  }
}

function getStatusColor(status: string | null) {
  switch (status) {
    case "running":
      return "bg-blue-500/10 text-blue-600 border-blue-500/20";
    case "completed":
      return "bg-green-500/10 text-green-600 border-green-500/20";
    case "failed":
      return "bg-red-500/10 text-red-600 border-red-500/20";
    case "pending":
    case "paused":
      return "bg-yellow-500/10 text-yellow-600 border-yellow-500/20";
    default:
      return "bg-gray-500/10 text-gray-600 border-gray-500/20";
  }
}

export function BranchesTab({ projectId }: BranchesTabProps) {
  const { data: branches, isLoading: branchesLoading } = useProjectBranches(projectId);
  const { data: commits, isLoading: commitsLoading } = useProjectCommits(projectId);
  const { data: pulls, isLoading: pullsLoading } = useProjectPulls(projectId);
  const { data: worktrees, isLoading: worktreesLoading } = useProjectWorktrees(projectId);
  const deleteBranch = useDeleteBranch();
  const createBranch = useCreateBranch();

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createBaseRef, setCreateBaseRef] = useState("main");
  const [createCheckout, setCreateCheckout] = useState(false);
  const [createPush, setCreatePush] = useState(false);

  const pullsByBranch = useMemo(() => {
    return new Map((pulls || []).map((pr) => [pr.branch, pr]));
  }, [pulls]);

  const handleDelete = async (branch: string) => {
    try {
      await deleteBranch.mutateAsync({ projectId, branch });
      toast.success(`Branch ${branch} deleted`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete branch");
    }
  };

  // Get branches that aren't associated with protocols
  const worktreeBranchNames = new Set(worktrees?.map((w) => w.branch_name) || []);
  const unassociatedBranches = branches?.filter((b) => !worktreeBranchNames.has(b.name)) || [];

  const handleCreateBranch = async () => {
    const name = createName.trim();
    if (!name) {
      toast.error("Branch name is required");
      return;
    }
    try {
      await createBranch.mutateAsync({
        projectId,
        name,
        baseRef: createBaseRef.trim() || undefined,
        checkout: createCheckout,
        push: createPush,
      });
      toast.success(`Branch created: ${name}`);
      setCreateOpen(false);
      setCreateName("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create branch");
    }
  };

  const columns: ColumnDef<Branch>[] = [
    {
      accessorKey: "name",
      header: "Branch Name",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <GitBranch className="text-muted-foreground h-4 w-4" />
          <span className="font-mono">{row.original.name}</span>
        </div>
      ),
    },
    {
      accessorKey: "sha",
      header: "SHA",
      cell: ({ row }) => (
        <span className="text-muted-foreground font-mono text-sm">
          {row.original.sha.slice(0, 8)}
        </span>
      ),
    },
    {
      accessorKey: "is_remote",
      header: "Type",
      cell: ({ row }) => (
        <span className="text-sm">{row.original.is_remote ? "Remote" : "Local"}</span>
      ),
    },
    {
      id: "ci",
      header: "CI",
      cell: ({ row }) => {
        const pr = pullsByBranch.get(row.original.name);
        if (!pr) return <span className="text-muted-foreground text-xs">—</span>;
        if (pr.checks === "passing") {
          return (
            <div className="flex items-center gap-1 text-xs text-green-600">
              <CheckCircle2 className="h-3 w-3" />
              Passing
            </div>
          );
        }
        if (pr.checks === "failing") {
          return (
            <div className="flex items-center gap-1 text-xs text-red-600">
              <XCircle className="h-3 w-3" />
              Failing
            </div>
          );
        }
        if (pr.checks === "pending") {
          return (
            <div className="flex items-center gap-1 text-xs text-yellow-600">
              <Clock className="h-3 w-3" />
              Pending
            </div>
          );
        }
        return (
          <div className="text-muted-foreground flex items-center gap-1 text-xs">
            <HelpCircle className="h-3 w-3" />
            Unknown
          </div>
        );
      },
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
              <Trash2 className="h-4 w-4" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Branch</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete the branch &quot;{row.original.name}&quot;? This
                action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => handleDelete(row.original.name)}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      ),
    },
  ];

  if (branchesLoading && worktreesLoading) return <LoadingState message="Loading branches..." />;

  return (
    <div className="space-y-6">
      {/* Protocol Workflow Section - Shows Protocol → Branch → PR flow */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Workflow className="h-5 w-5" />
            Protocol Workflows
          </CardTitle>
          <CardDescription>Active protocols with their branches and pull requests</CardDescription>
        </CardHeader>
        <CardContent>
          {worktreesLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          ) : !worktrees || worktrees.length === 0 ? (
            <div className="text-muted-foreground py-8 text-center">
              <Workflow className="mx-auto mb-3 h-12 w-12 opacity-50" />
              <p className="text-sm">No active protocol workflows</p>
              <p className="mt-1 text-xs">Start a protocol to create a dedicated branch</p>
            </div>
          ) : (
            <div className="space-y-4">
              {worktrees.map((wt: Worktree) => (
                <div
                  key={wt.branch_name}
                  className="hover:border-primary/30 rounded-lg border p-4 transition-colors"
                >
                  {/* Visual Flow: Protocol → Branch → PR */}
                  <div className="mb-4 flex flex-wrap items-center gap-3">
                    {/* Protocol Step */}
                    <div
                      className={cn(
                        "flex items-center gap-2 rounded-md border px-3 py-1.5",
                        wt.protocol_status === "completed" && "border-green-500/30 bg-green-500/10",
                        wt.protocol_status === "running" && "border-blue-500/30 bg-blue-500/10",
                        wt.protocol_status === "failed" && "border-red-500/30 bg-red-500/10",
                        !wt.protocol_status && "bg-muted"
                      )}
                    >
                      <FileCode2 className="h-4 w-4" />
                      <div className="text-sm">
                        <span className="font-medium">{wt.protocol_name || "Protocol"}</span>
                        {wt.protocol_status && (
                          <Badge
                            variant="outline"
                            className={cn("ml-2 text-xs", getStatusColor(wt.protocol_status))}
                          >
                            {wt.protocol_status}
                          </Badge>
                        )}
                      </div>
                    </div>

                    <ArrowRight className="text-muted-foreground h-4 w-4 flex-shrink-0" />

                    {/* Branch Step */}
                    <div className="bg-primary/5 border-primary/30 flex items-center gap-2 rounded-md border px-3 py-1.5">
                      <GitBranch className="text-primary h-4 w-4" />
                      <span className="font-mono text-sm font-medium">{wt.branch_name}</span>
                    </div>

                    <ArrowRight className="text-muted-foreground h-4 w-4 flex-shrink-0" />

                    {/* PR Step */}
                    {wt.pr_url ? (
                      <a
                        href={wt.pr_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 rounded-md border border-purple-500/30 bg-purple-500/10 px-3 py-1.5 transition-colors hover:bg-purple-500/20"
                      >
                        <GitMerge className="h-4 w-4 text-purple-600" />
                        <span className="text-sm font-medium text-purple-600">PR Open</span>
                        {pullsByBranch.get(wt.branch_name)?.checks === "passing" && (
                          <Badge
                            variant="outline"
                            className="border-green-500 text-[10px] text-green-700"
                          >
                            passing
                          </Badge>
                        )}
                        {pullsByBranch.get(wt.branch_name)?.checks === "failing" && (
                          <Badge
                            variant="outline"
                            className="border-red-500 text-[10px] text-red-700"
                          >
                            failing
                          </Badge>
                        )}
                        {pullsByBranch.get(wt.branch_name)?.checks === "pending" && (
                          <Badge
                            variant="outline"
                            className="border-yellow-500 text-[10px] text-yellow-700"
                          >
                            pending
                          </Badge>
                        )}
                        <ExternalLink className="h-3 w-3 text-purple-600" />
                      </a>
                    ) : (
                      <div className="bg-muted/50 flex items-center gap-2 rounded-md border border-dashed px-3 py-1.5">
                        <GitPullRequest className="text-muted-foreground h-4 w-4" />
                        <span className="text-muted-foreground text-sm">No PR</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-xs"
                          onClick={() => {
                            toast.info("Create a PR from your Git provider for this branch");
                          }}
                        >
                          <Plus className="mr-1 h-3 w-3" />
                          Create
                        </Button>
                      </div>
                    )}
                  </div>

                  {/* Commit Info */}
                  {wt.last_commit_sha && (
                    <div className="text-muted-foreground mt-2 flex items-center gap-3 border-t pt-3 text-xs">
                      <GitCommit className="h-3.5 w-3.5" />
                      <code className="bg-muted rounded px-1.5 py-0.5 font-mono">
                        {wt.last_commit_sha.slice(0, 7)}
                      </code>
                      <span className="max-w-[400px] truncate">{wt.last_commit_message}</span>
                      {wt.last_commit_date && (
                        <span className="text-muted-foreground/70 ml-auto">
                          {wt.last_commit_date}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="mt-3 flex items-center gap-2 border-t pt-3">
                    {wt.protocol_run_id && (
                      <Link href={`/protocols/${wt.protocol_run_id}`}>
                        <Button variant="outline" size="sm">
                          <Workflow className="mr-1.5 h-4 w-4" />
                          View Protocol
                        </Button>
                      </Link>
                    )}
                    {wt.spec_run_id && (
                      <Link href={`/specifications/${wt.spec_run_id}`}>
                        <Button variant="ghost" size="sm">
                          <FileCode2 className="mr-1.5 h-4 w-4" />
                          View Spec
                        </Button>
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pull Requests Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitPullRequest className="h-5 w-5" />
            Pull Requests
          </CardTitle>
          <CardDescription>Open pull requests and their CI status</CardDescription>
        </CardHeader>
        <CardContent>
          {pullsLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : !pulls || pulls.length === 0 ? (
            <p className="text-muted-foreground text-sm">No open pull requests</p>
          ) : (
            <div className="space-y-3">
              {pulls.map((pr: PullRequest) => (
                <div key={pr.id} className="flex items-start justify-between rounded-lg border p-3">
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{pr.title}</p>
                      <Badge
                        variant={pr.status === "open" ? "default" : "secondary"}
                        className="text-xs"
                      >
                        {pr.status}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground text-xs">
                      {pr.branch} by {pr.author} • {formatCreatedAt(pr.created_at)}
                    </p>
                    <div className="mt-2 flex items-center gap-2">
                      {pr.checks === "passing" && (
                        <div className="flex items-center gap-1 text-xs text-green-600">
                          <CheckCircle2 className="h-3 w-3" />
                          All checks passing
                        </div>
                      )}
                      {pr.checks === "failing" && (
                        <div className="flex items-center gap-1 text-xs text-red-600">
                          <XCircle className="h-3 w-3" />
                          Some checks failing
                        </div>
                      )}
                      {pr.checks === "pending" && (
                        <div className="flex items-center gap-1 text-xs text-yellow-600">
                          <Clock className="h-3 w-3" />
                          Checks pending
                        </div>
                      )}
                      {pr.checks === "unknown" && (
                        <div className="text-muted-foreground flex items-center gap-1 text-xs">
                          <HelpCircle className="h-3 w-3" />
                          No checks
                        </div>
                      )}
                    </div>
                  </div>
                  <Button variant="ghost" size="sm" asChild>
                    <a href={pr.url} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Commits Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitCommit className="h-5 w-5" />
            Recent Commits
          </CardTitle>
          <CardDescription>Latest commits across all branches</CardDescription>
        </CardHeader>
        <CardContent>
          {commitsLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </div>
          ) : !commits || commits.length === 0 ? (
            <p className="text-muted-foreground text-sm">No commits found</p>
          ) : (
            <div className="space-y-3">
              {commits.slice(0, 10).map((commit: Commit) => (
                <div key={commit.sha} className="flex items-start gap-3 rounded-lg border p-3">
                  <code className="text-muted-foreground mt-0.5 font-mono text-xs">
                    {commit.sha.slice(0, 7)}
                  </code>
                  <div className="flex-1 space-y-1">
                    <p className="text-sm font-medium">{commit.message}</p>
                    <p className="text-muted-foreground text-xs">
                      {commit.author} • {commit.date}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Unassociated Branches Section */}
      {unassociatedBranches.length > 0 && (
        <div>
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="text-lg font-semibold">Other Branches</h3>
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
              <DialogTrigger asChild>
                <Button size="sm" variant="outline" className="gap-2">
                  <Plus className="h-4 w-4" />
                  New Branch
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Branch</DialogTitle>
                  <DialogDescription>
                    Create a new local branch in the project repository.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
                  <div className="space-y-2">
                    <Label htmlFor="branch-name">Branch Name</Label>
                    <Input
                      id="branch-name"
                      value={createName}
                      onChange={(e) => setCreateName(e.target.value)}
                      placeholder="feature/my-change"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="base-ref">Base Ref</Label>
                    <Input
                      id="base-ref"
                      value={createBaseRef}
                      onChange={(e) => setCreateBaseRef(e.target.value)}
                      placeholder="main"
                    />
                    <p className="text-muted-foreground text-xs">
                      Branch, tag, or commit SHA (defaults to project base branch)
                    </p>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <Label htmlFor="checkout" className="text-sm">
                      Checkout after create
                    </Label>
                    <Switch
                      id="checkout"
                      checked={createCheckout}
                      onCheckedChange={setCreateCheckout}
                    />
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <Label htmlFor="push" className="text-sm">
                      Push to origin
                    </Label>
                    <Switch id="push" checked={createPush} onCheckedChange={setCreatePush} />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setCreateOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateBranch} disabled={createBranch.isPending}>
                    {createBranch.isPending ? "Creating..." : "Create Branch"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          <DataTable
            columns={columns}
            data={unassociatedBranches}
            enableSearch
            enableExport
            enableColumnFilters
            exportFilename={`project-${projectId}-branches.csv`}
          />
        </div>
      )}
    </div>
  );
}
