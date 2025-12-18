"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { FileText, Search, Plus, Filter, ListTodo, Target } from "lucide-react"
import Link from "next/link"

export default function SpecificationsPage() {
  const [searchQuery, setSearchQuery] = useState("")

  // Mock data
  const specifications = [
    {
      id: 1,
      path: ".specify/specs/feature-auth/spec.md",
      title: "User Authentication",
      projectId: 1,
      projectName: "tasksgodzilla-web",
      status: "completed",
      createdAt: "2025-01-15",
      tasksGenerated: true,
      protocolId: 42,
      sprintId: 3,
      sprintName: "Sprint 3",
      linkedTasks: 5,
      completedTasks: 3,
      storyPoints: 13,
    },
    {
      id: 2,
      path: ".specify/specs/feature-dashboard/spec.md",
      title: "Admin Dashboard",
      projectId: 1,
      projectName: "tasksgodzilla-web",
      status: "in-progress",
      createdAt: "2025-01-18",
      tasksGenerated: true,
      protocolId: 43,
      sprintId: 4,
      sprintName: "Sprint 4",
      linkedTasks: 8,
      completedTasks: 2,
      storyPoints: 21,
    },
    {
      id: 3,
      path: ".specify/specs/feature-api/spec.md",
      title: "REST API Endpoints",
      projectId: 2,
      projectName: "api-service",
      status: "draft",
      createdAt: "2025-01-20",
      tasksGenerated: false,
      protocolId: null,
      sprintId: null,
      sprintName: null,
      linkedTasks: 0,
      completedTasks: 0,
      storyPoints: 0,
    },
  ]

  const statusColors = {
    draft: "bg-gray-500",
    "in-progress": "bg-blue-500",
    completed: "bg-green-500",
    failed: "bg-red-500",
  }

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Specifications</h1>
        <p className="text-sm text-muted-foreground">Feature specifications and implementation plans</p>
      </div>

      <div className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3 text-sm">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-400" />
          <span className="font-medium">Total Specs:</span>
          <span className="text-muted-foreground">{specifications.length}</span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <ListTodo className="h-4 w-4 text-green-400" />
          <span className="font-medium">With Tasks:</span>
          <span className="text-muted-foreground">{specifications.filter((s) => s.tasksGenerated).length}</span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-purple-400" />
          <span className="font-medium">In Sprints:</span>
          <span className="text-muted-foreground">{specifications.filter((s) => s.sprintId).length}</span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <span className="font-medium">Total Story Points:</span>
          <span className="text-muted-foreground">{specifications.reduce((sum, s) => sum + s.storyPoints, 0)}</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search specifications..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button variant="outline" size="sm">
          <Filter className="mr-2 h-4 w-4" />
          Filter
        </Button>
        <Button size="sm">
          <Plus className="mr-2 h-4 w-4" />
          New Spec
        </Button>
      </div>

      <div className="grid gap-4">
        {specifications.map((spec) => (
          <Card key={spec.id} className="transition-colors hover:bg-muted/50">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <FileText className="mt-0.5 h-5 w-5 text-blue-500" />
                  <div>
                    <CardTitle className="text-base">{spec.title}</CardTitle>
                    <CardDescription className="mt-1 font-mono text-xs">{spec.path}</CardDescription>
                  </div>
                </div>
                <Badge variant="secondary" className={`${statusColors[spec.status]} text-white`}>
                  {spec.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>Project: {spec.projectName}</span>
                  <span>•</span>
                  <span>Created: {spec.createdAt}</span>
                  {spec.sprintName && (
                    <>
                      <span>•</span>
                      <div className="flex items-center gap-1">
                        <Target className="h-3 w-3 text-purple-400" />
                        <span className="text-purple-400">{spec.sprintName}</span>
                      </div>
                    </>
                  )}
                  {spec.linkedTasks > 0 && (
                    <>
                      <span>•</span>
                      <div className="flex items-center gap-1">
                        <ListTodo className="h-3 w-3 text-green-400" />
                        <span className="text-green-400">
                          {spec.completedTasks}/{spec.linkedTasks} tasks
                        </span>
                      </div>
                    </>
                  )}
                  {spec.storyPoints > 0 && (
                    <>
                      <span>•</span>
                      <span className="font-medium">{spec.storyPoints} pts</span>
                    </>
                  )}
                  {spec.protocolId && (
                    <>
                      <span>•</span>
                      <span>Protocol: #{spec.protocolId}</span>
                    </>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" asChild>
                    <Link href={`/specifications/${spec.id}`}>View</Link>
                  </Button>
                  {spec.protocolId && (
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/protocols/${spec.protocolId}`}>Protocol</Link>
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
