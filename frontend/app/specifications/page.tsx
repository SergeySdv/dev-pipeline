"use client"

import { useState, useMemo } from "react"
import { useSpecificationsWithMeta, useProjects, useSprints, type SpecificationFilters } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar } from "@/components/ui/calendar"
import { Separator } from "@/components/ui/separator"
import {
  FileText,
  Search,
  Plus,
  Filter,
  ListTodo,
  Target,
  Calendar as CalendarIcon,
  X,
  FolderKanban,
  CheckCircle2,
  ClipboardList,
  Layers,
} from "lucide-react"
import Link from "next/link"
import { format } from "date-fns"

export default function SpecificationsPage() {
  // Filter state
  const [searchQuery, setSearchQuery] = useState("")
  const [projectFilter, setProjectFilter] = useState<string>("all")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [workflowFilter, setWorkflowFilter] = useState<string>("all")
  const [dateFrom, setDateFrom] = useState<Date | undefined>()
  const [dateTo, setDateTo] = useState<Date | undefined>()
  const [showFilters, setShowFilters] = useState(false)

  // Build filters for API
  const filters: SpecificationFilters = useMemo(() => {
    const f: SpecificationFilters = {}
    if (projectFilter !== "all") f.project_id = parseInt(projectFilter)
    if (statusFilter !== "all") f.status = statusFilter as "draft" | "in-progress" | "completed"
    if (workflowFilter === "has_plan") f.has_plan = true
    if (workflowFilter === "has_tasks") f.has_tasks = true
    if (workflowFilter === "spec_only") {
      f.has_plan = false
      f.has_tasks = false
    }
    if (dateFrom) f.date_from = dateFrom.toISOString().split("T")[0]
    if (dateTo) f.date_to = dateTo.toISOString().split("T")[0]
    if (searchQuery) f.search = searchQuery
    return f
  }, [projectFilter, statusFilter, workflowFilter, dateFrom, dateTo, searchQuery])

  // Fetch data
  const { data: specsData, isLoading } = useSpecificationsWithMeta(filters)
  const { data: projects } = useProjects()
  const { data: sprints } = useSprints()

  const specifications = specsData?.items || []
  const total = specsData?.total || 0

  const activeFiltersCount = [
    projectFilter !== "all",
    statusFilter !== "all",
    workflowFilter !== "all",
    dateFrom,
    dateTo,
  ].filter(Boolean).length

  const clearFilters = () => {
    setProjectFilter("all")
    setStatusFilter("all")
    setWorkflowFilter("all")
    setDateFrom(undefined)
    setDateTo(undefined)
    setSearchQuery("")
  }

  const statusColors: Record<string, string> = {
    draft: "bg-slate-500",
    "in-progress": "bg-blue-500",
    completed: "bg-green-500",
  }

  const statusLabels: Record<string, string> = {
    draft: "Draft",
    "in-progress": "In Progress",
    completed: "Completed",
  }

  if (isLoading) {
    return <LoadingState message="Loading specifications..." />
  }

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Specifications</h1>
          <p className="text-sm text-muted-foreground">
            Feature specifications and implementation plans across all projects
          </p>
        </div>
        <Button asChild>
          <Link href="/projects">
            <Plus className="mr-2 h-4 w-4" />
            New Spec
          </Link>
        </Button>
      </div>

      {/* Stats Bar */}
      <div className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3 text-sm">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-500" />
          <span className="font-medium">Total:</span>
          <span className="text-muted-foreground">{total}</span>
        </div>
        <Separator orientation="vertical" className="h-4" />
        <div className="flex items-center gap-2">
          <ClipboardList className="h-4 w-4 text-amber-500" />
          <span className="font-medium">With Plan:</span>
          <span className="text-muted-foreground">
            {specifications.filter((s) => s.has_plan).length}
          </span>
        </div>
        <Separator orientation="vertical" className="h-4" />
        <div className="flex items-center gap-2">
          <ListTodo className="h-4 w-4 text-green-500" />
          <span className="font-medium">With Tasks:</span>
          <span className="text-muted-foreground">
            {specifications.filter((s) => s.has_tasks).length}
          </span>
        </div>
        {activeFiltersCount > 0 && (
          <>
            <Separator orientation="vertical" className="h-4" />
            <Badge variant="secondary" className="gap-1">
              <Filter className="h-3 w-3" />
              {activeFiltersCount} filter{activeFiltersCount > 1 ? "s" : ""} active
            </Badge>
          </>
        )}
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by title, path, or project name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Project Filter */}
          <Select value={projectFilter} onValueChange={setProjectFilter}>
            <SelectTrigger className="w-[200px]">
              <FolderKanban className="mr-2 h-4 w-4" />
              <SelectValue placeholder="All Projects" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Projects</SelectItem>
              <Separator className="my-1" />
              {projects?.map((project) => (
                <SelectItem key={project.id} value={project.id.toString()}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Status Filter */}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <Separator className="my-1" />
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="in-progress">In Progress</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant={showFilters ? "secondary" : "outline"}
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="mr-2 h-4 w-4" />
            More Filters
            {activeFiltersCount > 0 && (
              <Badge variant="default" className="ml-2 h-5 px-1.5">
                {activeFiltersCount}
              </Badge>
            )}
          </Button>

          {activeFiltersCount > 0 && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X className="mr-2 h-4 w-4" />
              Clear
            </Button>
          )}
        </div>

        {/* Expanded Filters */}
        {showFilters && (
          <Card>
            <CardContent className="pt-4">
              <div className="grid gap-4 md:grid-cols-4">
                {/* Workflow Stage */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Workflow Stage</label>
                  <Select value={workflowFilter} onValueChange={setWorkflowFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder="All Stages" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Stages</SelectItem>
                      <Separator className="my-1" />
                      <SelectItem value="spec_only">Spec Only</SelectItem>
                      <SelectItem value="has_plan">Has Plan</SelectItem>
                      <SelectItem value="has_tasks">Has Tasks</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Date From */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Created From</label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="w-full justify-start text-left font-normal">
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {dateFrom ? format(dateFrom, "PP") : "Pick a date"}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={dateFrom}
                        onSelect={setDateFrom}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                {/* Date To */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Created To</label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="w-full justify-start text-left font-normal">
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {dateTo ? format(dateTo, "PP") : "Pick a date"}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={dateTo}
                        onSelect={setDateTo}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Empty State */}
      {specifications.length === 0 && (
        <EmptyState
          icon={FileText}
          title={activeFiltersCount > 0 ? "No matching specifications" : "No specifications found"}
          description={
            activeFiltersCount > 0
              ? "Try adjusting your filters to find specifications."
              : "Create specifications using SpecKit to see them here."
          }
          action={
            activeFiltersCount > 0 ? (
              <Button variant="outline" onClick={clearFilters}>
                Clear Filters
              </Button>
            ) : (
              <Button asChild>
                <Link href="/projects">
                  <Plus className="mr-2 h-4 w-4" />
                  Go to Projects
                </Link>
              </Button>
            )
          }
        />
      )}

      {/* Specifications List */}
      <div className="grid gap-4">
        {specifications.map((spec) => (
          <Card key={spec.id} className="transition-colors hover:bg-muted/50">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <FileText className="mt-0.5 h-5 w-5 text-blue-500" />
                  <div>
                    <CardTitle className="text-base">{spec.title}</CardTitle>
                    <CardDescription className="mt-1 font-mono text-xs">
                      {spec.path}
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {/* Workflow Status Badges */}
                  <div className="flex items-center gap-1">
                    <Badge
                      variant={spec.has_tasks ? "default" : spec.has_plan ? "secondary" : "outline"}
                      className="text-xs"
                    >
                      {spec.has_tasks ? (
                        <>
                          <CheckCircle2 className="mr-1 h-3 w-3" />
                          Tasks
                        </>
                      ) : spec.has_plan ? (
                        <>
                          <ClipboardList className="mr-1 h-3 w-3" />
                          Plan
                        </>
                      ) : (
                        <>
                          <Layers className="mr-1 h-3 w-3" />
                          Spec
                        </>
                      )}
                    </Badge>
                  </div>
                  <Badge
                    variant="secondary"
                    className={`${statusColors[spec.status] || "bg-slate-500"} text-white`}
                  >
                    {statusLabels[spec.status] || spec.status}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <Link
                    href={`/projects/${spec.project_id}`}
                    className="flex items-center gap-1 hover:text-foreground transition-colors"
                  >
                    <FolderKanban className="h-3 w-3" />
                    {spec.project_name}
                  </Link>
                  {spec.created_at && (
                    <>
                      <span>•</span>
                      <span>{spec.created_at.split("T")[0]}</span>
                    </>
                  )}
                  {spec.sprint_name && (
                    <>
                      <span>•</span>
                      <div className="flex items-center gap-1">
                        <Target className="h-3 w-3 text-purple-500" />
                        <span className="text-purple-500">{spec.sprint_name}</span>
                      </div>
                    </>
                  )}
                  {spec.story_points > 0 && (
                    <>
                      <span>•</span>
                      <span className="font-medium">{spec.story_points} pts</span>
                    </>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" asChild>
                    <Link href={`/specifications/${spec.id}`}>View</Link>
                  </Button>
                  <Button variant="ghost" size="sm" asChild>
                    <Link href={`/projects/${spec.project_id}?tab=spec`}>Project</Link>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
