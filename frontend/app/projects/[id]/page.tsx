"use client"
import { use } from "react"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useProject, useOnboarding, useStartOnboarding, useProjectProtocols } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { StatusPill } from "@/components/ui/status-pill"
import { LoadingState } from "@/components/ui/loading-state"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  ArrowLeft,
  Play,
  GitBranch,
  ExternalLink,
  Settings2,
  FileCode2,
  AlertCircle,
  LayoutDashboard,
  Workflow,
  Shield,
  MessageSquare,
  GitPullRequest,
  CheckCircle2,
  XCircle,
  Clock,
  Kanban,
} from "lucide-react"
import { toast } from "sonner"
import { formatRelativeTime } from "@/lib/format"
import { OnboardingTab } from "./components/onboarding-tab"
import { SpecTab } from "./components/spec-tab"
import { PolicyTab } from "./components/policy-tab"
import { ClarificationsTab } from "./components/clarifications-tab"
import { BranchesTab } from "./components/branches-tab"
import { OverviewTab } from "./components/overview-tab"
import { SprintTab } from "./components/sprint-tab"
import { WorkflowTab } from "./components/workflow-tab"
import { cn } from "@/lib/utils"
import { GenerateSpecsWizardModal } from "@/components/wizards/generate-specs-wizard"
import { DesignSolutionWizardModal } from "@/components/wizards/design-solution-wizard"
import { ImplementFeatureWizardModal } from "@/components/wizards/implement-feature-wizard"

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const projectId = Number.parseInt(id, 10)
  const router = useRouter()
  const searchParams = useSearchParams()
  const { data: project, isLoading: projectLoading } = useProject(projectId)
  const { data: onboarding, isLoading: onboardingLoading, error: onboardingError } = useOnboarding(projectId)
  const { data: protocols } = useProjectProtocols(projectId)
  const startOnboarding = useStartOnboarding()

  if (projectLoading || (onboardingLoading && !onboardingError)) {
    return <LoadingState message="Loading project..." />
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <h2 className="text-2xl font-bold">Project not found</h2>
          <p className="text-muted-foreground">The project with ID {projectId} does not exist.</p>
          <Link href="/projects">
            <Button>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Projects
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  const handleStartOnboarding = async () => {
    try {
      await startOnboarding.mutateAsync(projectId)
      toast.success("Onboarding started")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to start onboarding")
    }
  }

  const protocolStats = {
    running: protocols?.filter((p) => p.status === "running").length || 0,
    completed: protocols?.filter((p) => p.status === "completed").length || 0,
    failed: protocols?.filter((p) => p.status === "failed").length || 0,
  }

  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard, description: "Project summary and quick actions" },
    {
      id: "workflow",
      label: "Workflow Pipeline",
      icon: Workflow,
      description: "Visual pipeline with agent assignment",
    },
    { id: "execution", label: "Execution", icon: Kanban, description: "Protocol-driven execution cycles" },
    { id: "onboarding", label: "Onboarding", icon: Workflow, description: "Setup progress and stages" },
    { id: "spec", label: "Specification", icon: FileCode2, description: "Technical specs and features" },
    { id: "policy", label: "Policy", icon: Shield, description: "Compliance and rules" },
    {
      id: "clarifications",
      label: "Clarifications",
      icon: MessageSquare,
      description: "Questions and blockers",
      badge: onboarding?.blocking_clarifications || 0,
    },
    { id: "branches", label: "Branches & PRs", icon: GitPullRequest, description: "Git workflow and CI" },
  ]

  const tabParam = searchParams.get("tab")
  const normalizedTab = tabParam === "sprints" ? "execution" : tabParam
  const activeTab =
    normalizedTab && navItems.some((item) => item.id === normalizedTab) ? normalizedTab : "overview"
  const wizardParam = searchParams.get("wizard")

  const updateQuery = (updates: Record<string, string | null>, replace = false) => {
    const params = new URLSearchParams(searchParams.toString())
    Object.entries(updates).forEach(([key, value]) => {
      if (!value) {
        params.delete(key)
      } else {
        params.set(key, value)
      }
    })
    const query = params.toString()
    const url = query ? `/projects/${projectId}?${query}` : `/projects/${projectId}`
    if (replace) {
      router.replace(url)
    } else {
      router.push(url)
    }
  }

  const handleTabClick = (tabId: string) => {
    updateQuery({ tab: tabId, wizard: null })
  }

  const closeWizard = () => {
    updateQuery({ wizard: null }, true)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/50">
        <div className="container py-6">
          <Link
            href="/projects"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Projects
          </Link>

          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold tracking-tight">{project.name}</h1>
              {onboarding && <StatusPill status={onboarding.status} size="sm" />}
              <Separator orientation="vertical" className="h-5" />
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <GitBranch className="h-3.5 w-3.5" />
                <code className="px-1 py-0.5 bg-muted rounded font-mono">{project.base_branch}</code>
              </div>
              <Separator orientation="vertical" className="h-5" />
              <a
                href={project.git_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1 group"
              >
                <span className="truncate max-w-[200px]">{project.git_url.replace("https://github.com/", "")}</span>
                <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
              </a>
              <Separator orientation="vertical" className="h-5" />
              {project.policy_pack_key && (
                <>
                  <Badge variant="secondary" className="h-5 text-xs font-normal">
                    <Settings2 className="mr-1 h-3 w-3" />
                    {project.policy_pack_key}
                  </Badge>
                  <Separator orientation="vertical" className="h-5" />
                </>
              )}
              {project.policy_enforcement_mode && (
                <>
                  <Badge variant="outline" className="h-5 text-xs capitalize font-normal">
                    {project.policy_enforcement_mode}
                  </Badge>
                  <Separator orientation="vertical" className="h-5" />
                </>
              )}
              <div className="flex items-center gap-3 text-xs">
                <div className="flex items-center gap-1">
                  <div className="h-2 w-2 rounded-full bg-purple-500 animate-pulse" />
                  <span className="text-muted-foreground">Running:</span>
                  <span className="font-semibold">{protocolStats.running}</span>
                </div>
                <div className="flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3 text-green-500" />
                  <span className="text-muted-foreground">Done:</span>
                  <span className="font-semibold">{protocolStats.completed}</span>
                </div>
                <div className="flex items-center gap-1">
                  <XCircle className="h-3 w-3 text-red-500" />
                  <span className="text-muted-foreground">Failed:</span>
                  <span className="font-semibold">{protocolStats.failed}</span>
                </div>
              </div>
              <Separator orientation="vertical" className="h-5" />
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span>{formatRelativeTime(project.updated_at)}</span>
              </div>
              {onboarding && onboarding.blocking_clarifications > 0 && (
                <>
                  <Separator orientation="vertical" className="h-5" />
                  <Badge variant="destructive" className="h-5 text-xs">
                    <AlertCircle className="mr-1 h-3 w-3" />
                    {onboarding.blocking_clarifications} Clarifications
                  </Badge>
                </>
              )}
            </div>

            {onboarding?.status === "pending" && (
              <Button
                onClick={handleStartOnboarding}
                disabled={startOnboarding.isPending}
                size="sm"
                className="shrink-0"
              >
                <Play className="mr-2 h-3.5 w-3.5" />
                Start Onboarding
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="container py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
          <aside className="space-y-2">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Navigation</div>
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = activeTab === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => handleTabClick(item.id)}
                  className={cn(
                    "w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors group",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted text-muted-foreground hover:text-foreground",
                  )}
                >
                  <Icon
                    className={cn(
                      "h-5 w-5 shrink-0 mt-0.5",
                      isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-foreground",
                    )}
                  />
                  <div className="flex-1 text-left">
                    <div className="flex items-center gap-2">
                      <span className={cn("font-medium", isActive && "text-primary-foreground")}>{item.label}</span>
                      {item.badge && item.badge > 0 && (
                        <Badge variant={isActive ? "secondary" : "destructive"} className="h-5 min-w-5 px-1.5 text-xs">
                          {item.badge}
                        </Badge>
                      )}
                    </div>
                    <p
                      className={cn(
                        "text-xs mt-0.5",
                        isActive ? "text-primary-foreground/80" : "text-muted-foreground",
                      )}
                    >
                      {item.description}
                    </p>
                  </div>
                </button>
              )
            })}
          </aside>

          <main>
            {activeTab === "overview" && <OverviewTab projectId={projectId} />}
            {activeTab === "workflow" && <WorkflowTab projectId={projectId} />}
            {activeTab === "execution" && <SprintTab projectId={projectId} />}
            {activeTab === "onboarding" && <OnboardingTab projectId={projectId} />}
            {activeTab === "spec" && <SpecTab projectId={projectId} />}
            {activeTab === "policy" && <PolicyTab projectId={projectId} />}
            {activeTab === "clarifications" && <ClarificationsTab projectId={projectId} />}
            {activeTab === "branches" && <BranchesTab projectId={projectId} />}
          </main>
        </div>
      </div>

      <GenerateSpecsWizardModal
        projectId={projectId}
        open={wizardParam === "generate-specs"}
        onOpenChange={(open) => {
          if (!open) closeWizard()
        }}
      />
      <DesignSolutionWizardModal
        projectId={projectId}
        open={wizardParam === "design-solution"}
        onOpenChange={(open) => {
          if (!open) closeWizard()
        }}
      />
      <ImplementFeatureWizardModal
        projectId={projectId}
        open={wizardParam === "implement-feature"}
        onOpenChange={(open) => {
          if (!open) closeWizard()
        }}
      />
    </div>
  )
}
