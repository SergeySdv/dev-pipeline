"use client"

import { useMemo } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Activity, Bot, Clock, XCircle } from "lucide-react"
import { useAgents, useAgentHealth, useAgentMetrics } from "@/lib/api"

export function AgentHealthDashboard({ projectId }: { projectId?: number }) {
  const { data: agents = [] } = useAgents(projectId)
  const { data: health = [] } = useAgentHealth(projectId)
  const { data: metrics = [] } = useAgentMetrics(projectId)

  const healthById = useMemo(() => new Map(health.map((h) => [h.agent_id, h])), [health])
  const metricsById = useMemo(() => new Map(metrics.map((m) => [m.agent_id, m])), [metrics])

  if (agents.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Agent Health
          </CardTitle>
          <CardDescription>No agents configured</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="h-5 w-5" />
          Agent Health
        </CardTitle>
        <CardDescription>Availability, response time, and step execution metrics</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => {
            const h = healthById.get(agent.id)
            const m = metricsById.get(agent.id)
            const available = h?.available ?? agent.status === "available"
            const responseTime = h?.response_time_ms ?? null
            const enabled = agent.enabled ?? agent.status !== "unavailable"

            return (
              <div key={agent.id} className="rounded-lg border bg-card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-medium truncate">{agent.name}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <Badge variant="secondary" className="text-[10px]">
                        {agent.kind}
                      </Badge>
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[10px]",
                          !enabled && "text-muted-foreground",
                          enabled && available && "border-green-500 text-green-700",
                          enabled && !available && "border-red-500 text-red-700",
                        )}
                      >
                        {!enabled ? "disabled" : available ? "available" : "unavailable"}
                      </Badge>
                      {responseTime != null && (
                        <Badge variant="outline" className="text-[10px]">
                          <Clock className="h-3 w-3 mr-1" />
                          {Math.round(responseTime)}ms
                        </Badge>
                      )}
                    </div>
                    {h?.error && (
                      <div className="mt-2 flex items-start gap-2 rounded border border-red-500/20 bg-red-500/5 p-2 text-xs text-red-700">
                        <XCircle className="h-4 w-4 mt-0.5" />
                        <div className="min-w-0 break-words">{h.error}</div>
                      </div>
                    )}
                  </div>
                  <Activity className={cn("h-5 w-5", available ? "text-green-600" : "text-muted-foreground")} />
                </div>

                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <div className="rounded bg-muted/50 p-2 text-center">
                    <div className="font-semibold">{m?.active_steps ?? 0}</div>
                    <div className="text-muted-foreground">active</div>
                  </div>
                  <div className="rounded bg-muted/50 p-2 text-center">
                    <div className="font-semibold">{m?.completed_steps ?? 0}</div>
                    <div className="text-muted-foreground">done</div>
                  </div>
                  <div className="rounded bg-muted/50 p-2 text-center">
                    <div className="font-semibold">{m?.failed_steps ?? 0}</div>
                    <div className="text-muted-foreground">failed</div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

