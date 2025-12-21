"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useProjects, useProtocols, useRuns } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Activity, FolderGit2, PlayCircle, TrendingUp, AlertCircle } from "lucide-react"
import Link from "next/link"
import { formatRelativeTime } from "@/lib/format"

export default function DashboardPage() {
  const { data: projects } = useProjects()
  const { data: protocols } = useProtocols()
  const { data: runs } = useRuns()

  const activeProtocols = protocols?.filter((p) => p.status === "running") || []
  const recentRuns = runs?.slice(0, 5) || []
  const failedRuns = runs?.filter((r) => r.status === "failed").length || 0

  const stats = [
    {
      label: "Total Projects",
      value: projects?.length || 0,
      icon: FolderGit2,
      color: "text-blue-500",
      href: "/projects",
    },
    {
      label: "Active Protocols",
      value: activeProtocols.length,
      icon: Activity,
      color: "text-green-500",
      href: "/protocols",
    },
    {
      label: "Total Runs",
      value: runs?.length || 0,
      icon: PlayCircle,
      color: "text-purple-500",
      href: "/runs",
    },
    {
      label: "Failed Runs",
      value: failedRuns,
      icon: AlertCircle,
      color: "text-red-500",
      href: "/runs?status=failed",
    },
  ]

  return (
    <div className="container py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your DevGodzilla workspace</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Link key={stat.label} href={stat.href}>
              <Card className="transition-colors hover:border-primary/50">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">{stat.label}</CardTitle>
                  <Icon className={`h-4 w-4 ${stat.color}`} />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stat.value}</div>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Active Protocols
            </CardTitle>
            <CardDescription>Protocols currently running</CardDescription>
          </CardHeader>
          <CardContent>
            {activeProtocols.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4">No active protocols</p>
            ) : (
              <div className="space-y-3">
                {activeProtocols.slice(0, 5).map((protocol) => (
                  <Link key={protocol.id} href={`/protocols/${protocol.id}`}>
                    <div className="flex items-center justify-between rounded-lg border p-3 hover:bg-accent">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">{protocol.name}</p>
                        <p className="text-xs text-muted-foreground">
                          Project: {projects?.find((p) => p.id === protocol.project_id)?.name}
                        </p>
                      </div>
                      <Badge variant="secondary">{protocol.status}</Badge>
                    </div>
                  </Link>
                ))}
                {activeProtocols.length > 5 && (
                  <Link href="/protocols">
                    <Button variant="ghost" size="sm" className="w-full">
                      View all active protocols
                    </Button>
                  </Link>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlayCircle className="h-5 w-5" />
              Recent Runs
            </CardTitle>
            <CardDescription>Latest execution runs</CardDescription>
          </CardHeader>
          <CardContent>
            {recentRuns.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4">No recent runs</p>
            ) : (
              <div className="space-y-3">
                {recentRuns.map((run) => (
                  <Link key={run.run_id} href={`/runs/${run.run_id}`}>
                    <div className="flex items-center justify-between rounded-lg border p-3 hover:bg-accent">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">{run.job_type}</p>
                        <p className="text-xs text-muted-foreground">{formatRelativeTime(run.created_at)}</p>
                      </div>
                      <Badge
                        variant={
                          run.status === "completed" ? "default" : run.status === "failed" ? "destructive" : "secondary"
                        }
                      >
                        {run.status}
                      </Badge>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Quick Actions
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Link href="/projects">
            <Button variant="outline">View Projects</Button>
          </Link>
          <Link href="/runs">
            <Button variant="outline">View All Runs</Button>
          </Link>
          <Link href="/ops">
            <Button variant="outline">Operations Dashboard</Button>
          </Link>
          <Link href="/policy-packs">
            <Button variant="outline">Policy Packs</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}
