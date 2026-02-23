"use client";

import { AlertTriangle, CheckCircle2, ShieldCheck,XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { useProtocolQualitySummary } from "@/lib/api";
import { cn } from "@/lib/utils";

interface QualityTabProps {
  protocolId: number;
}

function statusMeta(status: string) {
  if (status === "passed")
    {return { label: "Passed", icon: CheckCircle2, className: "text-green-600" };}
  if (status === "warning")
    {return { label: "Warning", icon: AlertTriangle, className: "text-amber-600" };}
  if (status === "failed") return { label: "Failed", icon: XCircle, className: "text-red-600" };
  return { label: status || "Unknown", icon: ShieldCheck, className: "text-muted-foreground" };
}

export function QualityTab({ protocolId }: QualityTabProps) {
  const { data: summary, isLoading } = useProtocolQualitySummary(protocolId);

  if (isLoading) return <LoadingState message="Loading quality..." />;
  if (!summary)
    {return (
      <EmptyState
        title="No quality data"
        description="Run QA for steps to populate quality results."
      />
    );}

  const overall = statusMeta(summary.overall_status);
  const OverallIcon = overall.icon;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <OverallIcon className={cn("h-5 w-5", overall.className)} />
            Protocol Quality
          </CardTitle>
          <CardDescription>Aggregated QA verdicts and constitutional gates</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-3">
            <Badge
              variant={summary.overall_status === "failed" ? "destructive" : "secondary"}
              className={cn(summary.overall_status === "passed" && "bg-green-500 text-white")}
            >
              {overall.label}
            </Badge>
            <div className="text-muted-foreground text-sm">
              Score:{" "}
              <span className="text-foreground font-medium">
                {Math.round(summary.score * 100)}%
              </span>
            </div>
            <div className="text-muted-foreground text-sm">
              Blocking:{" "}
              <span className="text-foreground font-medium">{summary.blocking_issues}</span>
            </div>
            <div className="text-muted-foreground text-sm">
              Warnings: <span className="text-foreground font-medium">{summary.warnings}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Gates</CardTitle>
          <CardDescription>{summary.gates.length} gate(s)</CardDescription>
        </CardHeader>
        <CardContent>
          {summary.gates.length === 0 ? (
            <div className="text-muted-foreground text-sm">No gates recorded yet.</div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {summary.gates.map((gate) => {
                const meta = statusMeta(gate.status);
                const Icon = meta.icon;
                return (
                  <div key={`${gate.article}:${gate.name}`} className="rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">
                          {gate.name}{" "}
                          <span className="text-muted-foreground">({gate.article})</span>
                        </div>
                        <div className="text-muted-foreground mt-1 text-xs">
                          Findings: {Array.isArray(gate.findings) ? gate.findings.length : 0}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Icon className={cn("h-4 w-4", meta.className)} />
                        <span className="text-muted-foreground text-xs">{meta.label}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Checklist</CardTitle>
          <CardDescription>
            {summary.checklist.passed}/{summary.checklist.total} passed
          </CardDescription>
        </CardHeader>
        <CardContent>
          {summary.checklist.items.length === 0 ? (
            <div className="text-muted-foreground text-sm">No checklist items.</div>
          ) : (
            <div className="space-y-2">
              {summary.checklist.items.map((item) => (
                <div key={item.id} className="flex items-start gap-3 rounded-lg border p-3">
                  {item.passed ? (
                    <CheckCircle2 className="mt-0.5 h-5 w-5 text-green-600" />
                  ) : (
                    <XCircle className="text-muted-foreground mt-0.5 h-5 w-5" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <div className="text-sm font-medium">{item.description}</div>
                      {item.required && (
                        <Badge variant="outline" className="text-[10px]">
                          Required
                        </Badge>
                      )}
                    </div>
                    <div className="text-muted-foreground mt-1 text-xs">ID: {item.id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
