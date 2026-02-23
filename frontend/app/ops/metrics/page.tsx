"use client";

import { Activity, BarChart3, Clock, Loader2,TrendingUp, Zap } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useMetricsSummary } from "@/lib/api";

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "N/A";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export default function MetricsPage() {
  const { data: metrics, isLoading, error } = useMetricsSummary(24);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">System Metrics</h2>
          <p className="text-destructive">Failed to load metrics: {error.message}</p>
        </div>
      </div>
    );
  }

  const jobMetrics = metrics?.job_type_metrics ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">System Metrics</h2>
        <p className="text-muted-foreground">Real-time system health and performance indicators</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Total Events
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.total_events ?? 0}</div>
            <p className="text-muted-foreground text-xs">Recent events tracked</p>
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
            <div className="text-2xl font-bold">{metrics?.success_rate ?? 100}%</div>
            <p className="text-muted-foreground text-xs">Protocol completion rate</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Protocol Runs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.total_protocol_runs ?? 0}</div>
            <p className="text-muted-foreground text-xs">Total protocols executed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Step Runs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.total_step_runs ?? 0}</div>
            <p className="text-muted-foreground text-xs">Total steps executed</p>
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
            {jobMetrics.length === 0 ? (
              <p className="text-muted-foreground text-sm">No job runs recorded yet.</p>
            ) : (
              <div className="space-y-4">
                {jobMetrics.slice(0, 10).map((metric) => (
                  <div key={metric.job_type} className="flex items-center justify-between">
                    <span className="font-mono text-sm">{metric.job_type}</span>
                    <div className="text-muted-foreground flex gap-4 text-sm">
                      <span>{metric.count} runs</span>
                      <span>avg {formatDuration(metric.avg_duration_seconds)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Overview</CardTitle>
            <CardDescription>Resource and activity metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-sm">Active Projects</span>
                  <span className="text-muted-foreground text-sm">
                    {metrics?.active_projects ?? 0}
                  </span>
                </div>
                <div className="bg-secondary h-2 overflow-hidden rounded-full">
                  <div
                    className="bg-primary h-full transition-all"
                    style={{ width: `${Math.min(100, (metrics?.active_projects ?? 0) * 10)}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-sm">Job Runs</span>
                  <span className="text-muted-foreground text-sm">
                    {metrics?.total_job_runs ?? 0}
                  </span>
                </div>
                <div className="bg-secondary h-2 overflow-hidden rounded-full">
                  <div
                    className="bg-primary h-full transition-all"
                    style={{ width: `${Math.min(100, metrics?.total_job_runs ?? 0)}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-sm">Recent Events</span>
                  <span className="text-muted-foreground text-sm">
                    {metrics?.recent_events_count ?? 0}
                  </span>
                </div>
                <div className="bg-secondary h-2 overflow-hidden rounded-full">
                  <div
                    className="bg-primary h-full transition-all"
                    style={{ width: `${Math.min(100, (metrics?.recent_events_count ?? 0) / 5)}%` }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Summary
          </CardTitle>
          <CardDescription>System-wide statistics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="bg-muted/50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold">{metrics?.active_projects ?? 0}</div>
              <div className="text-muted-foreground text-sm">Active Projects</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold">{metrics?.total_protocol_runs ?? 0}</div>
              <div className="text-muted-foreground text-sm">Protocol Runs</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold">{metrics?.total_step_runs ?? 0}</div>
              <div className="text-muted-foreground text-sm">Step Runs</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold">{metrics?.total_events ?? 0}</div>
              <div className="text-muted-foreground text-sm">Events</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
