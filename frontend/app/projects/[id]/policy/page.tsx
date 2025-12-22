"use client"
import { use } from "react"

import { useProjectDetail } from "@/lib/api"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"
import { PolicyTab } from "../components/policy-tab"

export default function ProjectPolicyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const projectId = Number.parseInt(id)
  const { data: project, isLoading } = useProjectDetail(projectId)

  if (isLoading) {
    return <LoadingState />
  }

  if (!project) {
    return <EmptyState title="Project not found" />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href={`/projects/${id}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Project
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">{project.name} - Policy</h1>
          <p className="text-sm text-muted-foreground">{project.git_url}</p>
        </div>
      </div>

      <PolicyTab projectId={projectId} />
    </div>
  )
}
