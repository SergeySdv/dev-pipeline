"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Activity, TrendingUp, Zap, Clock } from "lucide-react"

export default function MetricsPage() {
  // Note: This would connect to Prometheus metrics endpoint
  // For now, showing placeholder structure

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">System Metrics</h2>
        <p className="text-muted-foreground">Prometheus metrics and performance indicators</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Total Requests
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12,543</div>
            <p className="text-xs text-muted-foreground">Last 24 hours</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Success Rate
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">99.2%</div>
            <p className="text-xs text-muted-foreground">Last 24 hours</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Avg Response Time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">124ms</div>
            <p className="text-xs text-muted-foreground">p95: 285ms</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Queue Throughput
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">42/min</div>
            <p className="text-xs text-muted-foreground">Jobs processed</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Job Execution Metrics</CardTitle>
            <CardDescription>Performance by job type</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { type: "execute_step_job", count: 342, avgTime: "45s" },
                { type: "plan_protocol_job", count: 118, avgTime: "38s" },
                { type: "open_pr_job", count: 52, avgTime: "12s" },
              ].map((metric) => (
                <div key={metric.type} className="flex items-center justify-between">
                  <span className="font-mono text-sm">{metric.type}</span>
                  <div className="flex gap-4 text-sm text-muted-foreground">
                    <span>{metric.count} runs</span>
                    <span>avg {metric.avgTime}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Resource Usage</CardTitle>
            <CardDescription>System resource metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm">CPU Usage</span>
                  <span className="text-sm text-muted-foreground">42%</span>
                </div>
                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary" style={{ width: "42%" }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm">Memory Usage</span>
                  <span className="text-sm text-muted-foreground">68%</span>
                </div>
                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary" style={{ width: "68%" }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm">Queue Depth</span>
                  <span className="text-sm text-muted-foreground">15 jobs</span>
                </div>
                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary" style={{ width: "30%" }} />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API Endpoints</CardTitle>
          <CardDescription>Top endpoints by request volume</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { path: "GET /runs", calls: 2534, avg: "45ms" },
              { path: "POST /protocols/{id}/actions/run_next_step", calls: 1872, avg: "120ms" },
              { path: "GET /projects", calls: 1243, avg: "23ms" },
              { path: "GET /protocols/{id}/steps", calls: 987, avg: "56ms" },
            ].map((endpoint) => (
              <div key={endpoint.path} className="flex items-center justify-between py-2 border-b last:border-0">
                <span className="font-mono text-sm">{endpoint.path}</span>
                <div className="flex gap-6 text-sm text-muted-foreground">
                  <span>{endpoint.calls} calls</span>
                  <span>avg {endpoint.avg}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
