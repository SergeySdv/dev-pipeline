"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, FileText, CheckCircle2, Play, ListTodo, Target, TrendingUp, ExternalLink } from "lucide-react"
import Link from "next/link"

export default function SpecificationDetailPage({
  params,
}: {
  params: { id: string }
}) {
  const id = params.id

  // Mock data
  const spec = {
    id: Number.parseInt(id),
    path: ".specify/specs/feature-auth/spec.md",
    title: "User Authentication",
    projectId: 1,
    projectName: "tasksgodzilla-web",
    status: "completed",
    content: `# Feature Specification: User Authentication

## Overview
Implement secure user authentication system with JWT tokens.

## Requirements
- Email/password login
- JWT token generation
- Protected routes
- Session management

## Acceptance Criteria
- [ ] Users can register with email
- [ ] Users can login with credentials
- [ ] JWT tokens are securely generated
- [ ] Protected routes verify tokens`,
    tasksGenerated: true,
    protocolId: 42,
    sprintId: 3,
    sprintName: "Sprint 3",
    linkedTasks: [
      { id: 1, title: "Setup authentication service", status: "done", points: 3 },
      { id: 2, title: "Implement JWT generation", status: "done", points: 5 },
      { id: 3, title: "Create login UI", status: "in_progress", points: 3 },
      { id: 4, title: "Add protected routes", status: "todo", points: 2 },
    ],
    totalPoints: 13,
    completedPoints: 8,
  }

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/specifications">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Link>
          </Button>
          <FileText className="h-5 w-5 text-blue-500" />
          <div>
            <h1 className="text-2xl font-semibold">{spec.title}</h1>
            <p className="text-sm text-muted-foreground">{spec.path}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="bg-green-500 text-white">
            {spec.status}
          </Badge>
          {spec.protocolId && (
            <Button size="sm" asChild>
              <Link href={`/protocols/${spec.protocolId}`}>
                <Play className="mr-2 h-4 w-4" />
                View Protocol
              </Link>
            </Button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3 text-sm">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-purple-400" />
          <span className="font-medium">Sprint:</span>
          <Link href={`/sprints?sprint=${spec.sprintId}`} className="text-purple-400 hover:underline">
            {spec.sprintName}
          </Link>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <ListTodo className="h-4 w-4 text-blue-400" />
          <span className="font-medium">Tasks:</span>
          <span className="text-muted-foreground">
            {spec.linkedTasks.filter((t) => t.status === "done").length}/{spec.linkedTasks.length}
          </span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-green-400" />
          <span className="font-medium">Story Points:</span>
          <span className="text-muted-foreground">
            {spec.completedPoints}/{spec.totalPoints}
          </span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <span className="font-medium">Progress:</span>
          <span className="text-green-400">{Math.round((spec.completedPoints / spec.totalPoints) * 100)}%</span>
        </div>
      </div>

      <Tabs defaultValue="content" className="flex-1">
        <TabsList>
          <TabsTrigger value="content">Content</TabsTrigger>
          <TabsTrigger value="tasks">Tasks ({spec.linkedTasks.length})</TabsTrigger>
          <TabsTrigger value="protocol">Protocol</TabsTrigger>
          <TabsTrigger value="sprint">Sprint Board</TabsTrigger>
        </TabsList>

        <TabsContent value="content" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Specification Content</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">{spec.content}</pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tasks" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Generated Tasks</CardTitle>
              <CardDescription>
                {spec.linkedTasks.length} task(s) • {spec.completedPoints}/{spec.totalPoints} story points
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {spec.linkedTasks.map((task) => (
                  <div key={task.id} className="flex items-center justify-between rounded-lg border p-3">
                    <div className="flex items-center gap-3">
                      <CheckCircle2
                        className={`h-4 w-4 ${task.status === "done" ? "text-green-500" : "text-muted-foreground"}`}
                      />
                      <div>
                        <p className="font-medium text-sm">{task.title}</p>
                        <p className="text-xs text-muted-foreground capitalize">{task.status.replace("_", " ")}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-muted-foreground">{task.points} pts</span>
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/sprints?task=${task.id}`}>View</Link>
                      </Button>
                    </div>
                  </div>
                ))}
                <div className="mt-4">
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/sprints?sprint=${spec.sprintId}`}>
                      View in Sprint Board
                      <ExternalLink className="ml-2 h-3 w-3" />
                    </Link>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="protocol" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Protocol Execution</CardTitle>
            </CardHeader>
            <CardContent>
              {spec.protocolId ? (
                <div className="space-y-2">
                  <p className="text-sm">Protocol ID: #{spec.protocolId}</p>
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/protocols/${spec.protocolId}`}>View Protocol Details</Link>
                  </Button>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">No protocol created yet</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sprint" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Sprint Context</CardTitle>
              <CardDescription>View this specification's tasks in the sprint board</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="rounded-lg border bg-muted/50 p-4">
                  <h3 className="mb-2 font-semibold">{spec.sprintName}</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Sprint Progress:</span>
                      <span className="font-medium">
                        {Math.round((spec.completedPoints / spec.totalPoints) * 100)}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-muted">
                      <div
                        className="h-2 rounded-full bg-green-500 transition-all"
                        style={{ width: `${(spec.completedPoints / spec.totalPoints) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
                <Button asChild>
                  <Link href={`/sprints?sprint=${spec.sprintId}`}>
                    <Target className="mr-2 h-4 w-4" />
                    Open Sprint Board
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
