"use client"

import { useState, type KeyboardEvent } from "react"
import { useRouter } from "next/navigation"
import {
  useProjects,
  useCreateProject,
  useArchiveProject,
  useUnarchiveProject,
  useDeleteProject,
  useOnboarding,
} from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Plus,
  GitBranch,
  FolderGit2,
  Search,
  Activity,
  TrendingUp,
  MoreVertical,
  Settings,
  Copy,
  Archive,
  ArchiveRestore,
  ExternalLink,
  Play,
  FileText,
  LayoutGrid,
  List,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertCircle,
  Cloud,
  FolderOpen,
} from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { formatRelativeTime } from "@/lib/format"
import type { Project } from "@/lib/api/types"
import { ProjectWizard } from "@/components/wizards/project-wizard"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

export default function ProjectsPage() {
  const { data: projects, isLoading, error } = useProjects()
  const createProject = useCreateProject()
  const archiveProject = useArchiveProject()
  const unarchiveProject = useUnarchiveProject()
  const deleteProject = useDeleteProject()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid")
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null)
  const router = useRouter()

  const filteredProjects =
    projects?.filter(
      (p) =>
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.git_url.toLowerCase().includes(searchQuery.toLowerCase()),
    ) || []

  if (isLoading) return <LoadingState message="Loading projects..." />
  if (error) return <EmptyState title="Error loading projects" description={error.message} />

  const stats = {
    total: projects?.length || 0,
    active:
      projects?.filter((p) => p.policy_enforcement_mode === "warn" || p.policy_enforcement_mode === "enforce")
        .length || 0,
    withPolicy: projects?.filter((p) => p.policy_pack_key).length || 0,
  }

  const handleOpenProject = (projectId: number) => {
    router.push(`/projects/${projectId}`)
  }

  const handleRunProtocol = (projectId: number) => {
    router.push(`/projects/${projectId}?tab=workflow`)
  }

  const handleViewSpecs = (projectId: number) => {
    router.push(`/projects/${projectId}?tab=spec`)
  }

  const handleSettings = (projectId: number) => {
    router.push(`/projects/${projectId}?tab=policy`)
  }

  const handleOpenGit = (project: Project) => {
    if (!project.git_url) {
      toast.error("No repository URL configured for this project.")
      return
    }
    window.open(project.git_url, "_blank", "noopener,noreferrer")
  }

  const handleArchiveToggle = async (project: Project) => {
    try {
      if (project.status === "archived") {
        await unarchiveProject.mutateAsync(project.id)
        toast.success(`Unarchived ${project.name}`)
      } else {
        await archiveProject.mutateAsync(project.id)
        toast.success(`Archived ${project.name}`)
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update project status")
    }
  }

  const handleDuplicate = async (project: Project) => {
    if (!project.git_url) {
      toast.error("Cannot duplicate a project without a repository URL.")
      return
    }
    const suggestedName = `${project.name} Copy`
    const name = window.prompt("Name for the duplicated project:", suggestedName)
    if (!name) return

    try {
      const created = await createProject.mutateAsync({
        name,
        git_url: project.git_url,
        base_branch: project.base_branch,
      })
      toast.success(`Created ${created.name}`)
      router.push(`/projects/${created.id}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to duplicate project")
    }
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    try {
      await deleteProject.mutateAsync(deleteTarget.id)
      toast.success(`Deleted ${deleteTarget.name}`)
      setDeleteTarget(null)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete project")
    }
  }

  return (
    <div className="container py-8 space-y-8">
      <div>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
            <p className="text-muted-foreground mt-1">Manage your registered repositories and development workflows</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center border rounded-lg p-1">
              <Button
                variant={viewMode === "grid" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("grid")}
                className="h-8 w-8 p-0"
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === "list" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("list")}
                className="h-8 w-8 p-0"
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
            <Button onClick={() => setIsCreateOpen(true)} size="lg">
              <Plus className="mr-2 h-4 w-4" />
              New Project
            </Button>
          </div>
        </div>

        <div className="bg-muted/50 border rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-md bg-blue-500/10 flex items-center justify-center">
                <FolderGit2 className="h-4 w-4 text-blue-500" />
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground">Total Projects</div>
                <div className="text-2xl font-bold">{stats.total}</div>
              </div>
            </div>

            <div className="h-12 w-px bg-border" />

            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-md bg-purple-500/10 flex items-center justify-center">
                <Activity className="h-4 w-4 text-purple-500" />
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground">Active</div>
                <div className="text-2xl font-bold">{stats.active}</div>
              </div>
            </div>

            <div className="h-12 w-px bg-border" />

            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-md bg-green-500/10 flex items-center justify-center">
                <TrendingUp className="h-4 w-4 text-green-500" />
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground">With Policy</div>
                <div className="text-2xl font-bold">{stats.withPolicy}</div>
              </div>
            </div>

            <div className="flex-1" />

            <div className="text-right">
              <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Quick Actions</div>
              <Button variant="outline" size="sm" onClick={() => setIsCreateOpen(true)}>
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                Add Project
              </Button>
            </div>
          </div>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search projects by name or repository..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-11"
          />
        </div>
      </div>

      {!filteredProjects || filteredProjects.length === 0 ? (
        <EmptyState
          icon={FolderGit2}
          title={searchQuery ? "No projects found" : "No projects yet"}
          description={
            searchQuery
              ? "Try adjusting your search query."
              : "Create your first project to get started with TasksGodzilla."
          }
          action={
            !searchQuery ? (
              <Button onClick={() => setIsCreateOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Project
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div
          className={cn(
            viewMode === "grid" && "grid gap-6 md:grid-cols-2 lg:grid-cols-3",
            viewMode === "list" && "space-y-4",
          )}
        >
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              viewMode={viewMode}
              onOpen={handleOpenProject}
              onRunProtocol={handleRunProtocol}
              onViewSpecs={handleViewSpecs}
              onSettings={handleSettings}
              onDuplicate={handleDuplicate}
              onOpenGit={handleOpenGit}
              onArchiveToggle={handleArchiveToggle}
              onDeleteRequest={setDeleteTarget}
            />
          ))}
        </div>
      )}

      <ProjectWizard open={isCreateOpen} onOpenChange={setIsCreateOpen} />
      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Project</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove {deleteTarget?.name} and all associated runs, specs, and events. Local
              repository files are not removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function OnboardingProgress({ projectId }: { projectId: number }) {
  const { data: onboarding, isLoading } = useOnboarding(projectId)

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Loading...</span>
      </div>
    )
  }

  if (!onboarding) return null

  const completedStages = onboarding.stages?.filter(s => s.status === "completed").length || 0
  const totalStages = onboarding.stages?.length || 4
  const progress = Math.round((completedStages / totalStages) * 100)

  const statusIcon = {
    pending: <AlertCircle className="h-3 w-3 text-muted-foreground" />,
    running: <Loader2 className="h-3 w-3 text-blue-500 animate-spin" />,
    completed: <CheckCircle2 className="h-3 w-3 text-green-500" />,
    failed: <XCircle className="h-3 w-3 text-red-500" />,
    blocked: <AlertCircle className="h-3 w-3 text-amber-500" />,
  }[onboarding.status] || <AlertCircle className="h-3 w-3 text-muted-foreground" />

  const statusLabel = {
    pending: "Pending",
    running: "Onboarding...",
    completed: "Ready",
    failed: "Failed",
    blocked: "Blocked",
  }[onboarding.status] || onboarding.status

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2 text-xs">
        {statusIcon}
        <span className={cn(
          "capitalize",
          onboarding.status === "completed" && "text-green-600",
          onboarding.status === "failed" && "text-red-600",
          onboarding.status === "blocked" && "text-amber-600",
          onboarding.status === "running" && "text-blue-600",
        )}>
          {statusLabel}
        </span>
        {onboarding.blocking_clarifications > 0 && (
          <Badge variant="destructive" className="h-4 text-[10px] px-1">
            {onboarding.blocking_clarifications} blocked
          </Badge>
        )}
      </div>
      {onboarding.status !== "completed" && onboarding.status !== "pending" && (
        <Progress value={progress} className="h-1" />
      )}
    </div>
  )
}

function CloneStatusIndicator({ localPath }: { localPath: string | null }) {
  if (localPath) {
    return (
      <div className="flex items-center gap-1 text-xs text-green-600" title={`Cloned: ${localPath}`}>
        <FolderOpen className="h-3 w-3" />
        <span>Local</span>
      </div>
    )
  }
  return (
    <div className="flex items-center gap-1 text-xs text-muted-foreground" title="Not cloned locally">
      <Cloud className="h-3 w-3" />
      <span>Remote</span>
    </div>
  )
}

type ProjectCardProps = {
  project: Project
  viewMode: "grid" | "list"
  onOpen: (projectId: number) => void
  onRunProtocol: (projectId: number) => void
  onViewSpecs: (projectId: number) => void
  onSettings: (projectId: number) => void
  onDuplicate: (project: Project) => void
  onOpenGit: (project: Project) => void
  onArchiveToggle: (project: Project) => void
  onDeleteRequest: (project: Project | null) => void
}

function ProjectCard({
  project,
  viewMode,
  onOpen,
  onRunProtocol,
  onViewSpecs,
  onSettings,
  onDuplicate,
  onOpenGit,
  onArchiveToggle,
  onDeleteRequest,
}: ProjectCardProps) {
  const [showActions, setShowActions] = useState(false)
  const isArchived = project.status === "archived"

  const handleCardKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      onOpen(project.id)
    }
  }

  return (
    <div
      className={cn("group relative", viewMode === "list" && "flex items-center gap-4")}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <Card
        role="button"
        tabIndex={0}
        onKeyDown={handleCardKeyDown}
        onClick={() => onOpen(project.id)}
        className={cn(
          "h-full transition-all hover:border-primary/50 hover:shadow-lg cursor-pointer",
          viewMode === "list" && "flex items-center flex-1",
        )}
      >
          <CardHeader className={cn("pb-4", viewMode === "list" && "flex-row items-center space-y-0 py-4")}>
            <div className="flex items-start justify-between flex-1">
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="relative">
                  <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-neutral-600 to-neutral-800 flex items-center justify-center text-white font-bold text-lg">
                    {project.name.charAt(0).toUpperCase()}
                  </div>
                  {project.policy_enforcement_mode && (
                    <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-neutral-700 rounded-full border-2 border-background flex items-center justify-center">
                      <Activity className="h-3 w-3 text-white" />
                    </div>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <CardTitle className="text-lg group-hover:text-primary transition-colors truncate">
                    {project.name}
                  </CardTitle>
                  <CardDescription className="flex items-center gap-2 text-xs mt-1">
                    <GitBranch className="h-3 w-3 flex-shrink-0" />
                    <span className="truncate">{project.base_branch}</span>
                  </CardDescription>
                </div>
              </div>

              {viewMode === "grid" && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild onClick={(event) => event.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="sm"
                      className={cn(
                        "h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity",
                        showActions && "opacity-100",
                      )}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem onClick={(event) => {
                      event.stopPropagation()
                      onRunProtocol(project.id)
                    }}>
                      <Play className="mr-2 h-4 w-4" />
                      Run Protocol
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={(event) => {
                      event.stopPropagation()
                      onViewSpecs(project.id)
                    }}>
                      <FileText className="mr-2 h-4 w-4" />
                      View Specs
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={(event) => {
                      event.stopPropagation()
                      onSettings(project.id)
                    }}>
                      <Settings className="mr-2 h-4 w-4" />
                      Settings
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={(event) => {
                      event.stopPropagation()
                      onDuplicate(project)
                    }}>
                      <Copy className="mr-2 h-4 w-4" />
                      Duplicate
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={(event) => {
                        event.stopPropagation()
                        onOpenGit(project)
                      }}
                      disabled={!project.git_url}
                    >
                      <ExternalLink className="mr-2 h-4 w-4" />
                      Open in GitHub
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={(event) => {
                      event.stopPropagation()
                      onArchiveToggle(project)
                    }}>
                      {isArchived ? <ArchiveRestore className="mr-2 h-4 w-4" /> : <Archive className="mr-2 h-4 w-4" />}
                      {isArchived ? "Unarchive" : "Archive"}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className="text-destructive"
                      onClick={(event) => {
                        event.stopPropagation()
                        onDeleteRequest(project)
                      }}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </CardHeader>

          {viewMode === "grid" && (
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-2">
                <OnboardingProgress projectId={project.id} />
                <CloneStatusIndicator localPath={project.local_path} />
              </div>

              <div className="flex items-center gap-2 text-xs">
                <code className="px-2 py-1.5 bg-muted rounded text-[10px] truncate flex-1 font-mono">
                  {project.git_url.replace("https://", "").replace("http://", "")}
                </code>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  onClick={(event) => {
                    event.stopPropagation()
                    onOpenGit(project)
                  }}
                  disabled={!project.git_url}
                >
                  <ExternalLink className="h-3 w-3" />
                </Button>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {project.policy_pack_key && (
                  <Badge variant="secondary" className="text-xs">
                    <TrendingUp className="mr-1 h-3 w-3" />
                    {project.policy_pack_key}
                  </Badge>
                )}
                {project.policy_enforcement_mode && (
                  <Badge
                    variant={
                      project.policy_enforcement_mode === "enforce"
                        ? "default"
                        : project.policy_enforcement_mode === "warn"
                          ? "secondary"
                          : "outline"
                    }
                    className="text-xs capitalize"
                  >
                    {project.policy_enforcement_mode}
                  </Badge>
                )}
                {project.project_classification && (
                  <Badge variant="outline" className="text-xs">
                    {project.project_classification}
                  </Badge>
                )}
              </div>

              <div className="pt-3 border-t flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Updated {formatRelativeTime(project.updated_at)}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={(event) => {
                    event.stopPropagation()
                    onOpen(project.id)
                  }}
                >
                  View Details →
                </Button>
              </div>
            </CardContent>
          )}

          {viewMode === "list" && (
            <CardContent className="py-4 flex items-center gap-4">
              <div className="flex items-center gap-2 flex-1">
                {project.policy_pack_key && (
                  <Badge variant="secondary" className="text-xs">
                    {project.policy_pack_key}
                  </Badge>
                )}
                {project.policy_enforcement_mode && (
                  <Badge variant="outline" className="text-xs capitalize">
                    {project.policy_enforcement_mode}
                  </Badge>
                )}
              </div>
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {formatRelativeTime(project.updated_at)}
              </span>
              <DropdownMenu>
                <DropdownMenuTrigger asChild onClick={(event) => event.stopPropagation()}>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem onClick={(event) => {
                    event.stopPropagation()
                    onRunProtocol(project.id)
                  }}>
                    <Play className="mr-2 h-4 w-4" />
                    Run Protocol
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={(event) => {
                    event.stopPropagation()
                    onViewSpecs(project.id)
                  }}>
                    <FileText className="mr-2 h-4 w-4" />
                    View Specs
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={(event) => {
                    event.stopPropagation()
                    onSettings(project.id)
                  }}>
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={(event) => {
                    event.stopPropagation()
                    onDuplicate(project)
                  }}>
                    <Copy className="mr-2 h-4 w-4" />
                    Duplicate
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={(event) => {
                      event.stopPropagation()
                      onOpenGit(project)
                    }}
                    disabled={!project.git_url}
                  >
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Open in GitHub
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={(event) => {
                    event.stopPropagation()
                    onArchiveToggle(project)
                  }}>
                    {isArchived ? <ArchiveRestore className="mr-2 h-4 w-4" /> : <Archive className="mr-2 h-4 w-4" />}
                    {isArchived ? "Unarchive" : "Archive"}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="text-destructive"
                    onClick={(event) => {
                      event.stopPropagation()
                      onDeleteRequest(project)
                    }}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardContent>
          )}
      </Card>
    </div>
  )
}
