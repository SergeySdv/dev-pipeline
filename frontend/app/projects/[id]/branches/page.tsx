"use client";
import { use } from "react";
import Link from "next/link";

import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { useProjectDetail } from "@/lib/api";

import { BranchesTab } from "../components/branches-tab";

export default function ProjectBranchesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const projectId = Number.parseInt(id);
  const { data: project, isLoading } = useProjectDetail(projectId);

  if (isLoading) {
    return <LoadingState />;
  }

  if (!project) {
    return <EmptyState title="Project not found" />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href={`/projects/${id}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Project
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">{project.name} - Branches</h1>
          <p className="text-muted-foreground text-sm">{project.git_url}</p>
        </div>
      </div>

      <BranchesTab projectId={projectId} />
    </div>
  );
}
