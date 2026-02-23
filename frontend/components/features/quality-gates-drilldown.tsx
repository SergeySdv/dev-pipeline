"use client";

import { useMemo } from "react";

import { AlertTriangle, CheckCircle2, ChevronRight, Shield,XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useProtocolQualityGates } from "@/lib/api";
import type { ProtocolQualityGate } from "@/lib/api/hooks/use-quality";
import { cn } from "@/lib/utils";

/**
 * Represents the severity level of a finding
 */
export type FindingSeverity = "critical" | "high" | "medium" | "low" | "info" | "unknown";

/**
 * Represents a finding within a quality gate
 */
export interface QualityGateFinding {
  severity?: string;
  message?: string;
  [key: string]: unknown;
}

/**
 * Represents the data needed to render a quality gate list item
 */
export interface QualityGateListItemData {
  article: string;
  name: string;
  status: string;
  findings: QualityGateFinding[];
  findingsCount: number;
  hasSeverityIndicator: boolean;
  maxSeverity: FindingSeverity;
}

/**
 * Gets the status metadata for a given status string.
 * Exported for property-based testing.
 *
 * @param status - The status string
 * @returns Object with label, icon, and className
 */
export function getStatusMeta(status: string): {
  label: string;
  icon: typeof CheckCircle2;
  className: string;
} {
  if (status === "passed")
    {return { label: "Passed", icon: CheckCircle2, className: "text-green-600" };}
  if (status === "warning")
    {return { label: "Warning", icon: AlertTriangle, className: "text-amber-600" };}
  if (status === "failed") return { label: "Failed", icon: XCircle, className: "text-red-600" };
  return { label: status || "Unknown", icon: Shield, className: "text-muted-foreground" };
}

/**
 * Determines the severity level from a finding object.
 *
 * @param finding - The finding object
 * @returns The severity level
 */
export function getSeverityFromFinding(finding: QualityGateFinding): FindingSeverity {
  const severity = finding.severity?.toLowerCase();
  if (severity === "critical") return "critical";
  if (severity === "high") return "high";
  if (severity === "medium") return "medium";
  if (severity === "low") return "low";
  if (severity === "info") return "info";
  return "unknown";
}

/**
 * Gets the maximum severity from a list of findings.
 *
 * @param findings - Array of findings
 * @returns The highest severity level
 */
export function getMaxSeverity(findings: QualityGateFinding[]): FindingSeverity {
  const severityOrder: FindingSeverity[] = ["critical", "high", "medium", "low", "info", "unknown"];

  if (findings.length === 0) return "unknown";

  let maxIndex = severityOrder.length - 1;
  for (const finding of findings) {
    const severity = getSeverityFromFinding(finding);
    const index = severityOrder.indexOf(severity);
    if (index < maxIndex) {
      maxIndex = index;
    }
  }

  return severityOrder[maxIndex];
}

/**
 * Computes the list item data for a quality gate.
 * This function is exported for property-based testing.
 *
 * @param gate - The quality gate data
 * @returns The computed list item data
 */
export function computeQualityGateListItemData(gate: ProtocolQualityGate): QualityGateListItemData {
  const findings = Array.isArray(gate.findings)
    ? gate.findings.map((f) => f as QualityGateFinding)
    : [];
  const maxSeverity = getMaxSeverity(findings);

  return {
    article: gate.article,
    name: gate.name,
    status: gate.status,
    findings,
    findingsCount: findings.length,
    hasSeverityIndicator: findings.length > 0 && maxSeverity !== "unknown",
    maxSeverity,
  };
}

/**
 * Validates that a quality gate list item has all required fields for rendering.
 * Returns an object indicating which fields are present.
 *
 * @param itemData - The quality gate list item data to validate
 * @returns Object with boolean flags for each required field
 */
export function validateQualityGateListItemCompleteness(itemData: QualityGateListItemData): {
  hasName: boolean;
  hasStatus: boolean;
  hasSeverityIndicator: boolean;
  isComplete: boolean;
} {
  const hasName = typeof itemData.name === "string" && itemData.name.length > 0;
  const hasStatus = typeof itemData.status === "string" && itemData.status.length > 0;
  // Severity indicator is required only when there are findings with known severity
  const hasSeverityIndicator =
    itemData.findingsCount === 0 ||
    itemData.hasSeverityIndicator ||
    itemData.maxSeverity === "unknown";

  return {
    hasName,
    hasStatus,
    hasSeverityIndicator,
    isComplete: hasName && hasStatus,
  };
}

// Keep the original function for internal use
function statusMeta(status: string) {
  return getStatusMeta(status);
}

/**
 * Gets the severity badge variant and class for a severity level.
 *
 * @param severity - The severity level
 * @returns Object with variant and className for the badge
 */
export function getSeverityBadgeProps(severity: FindingSeverity): {
  variant: "destructive" | "secondary" | "outline";
  className: string;
} {
  switch (severity) {
    case "critical":
      return { variant: "destructive", className: "bg-red-600" };
    case "high":
      return { variant: "destructive", className: "" };
    case "medium":
      return { variant: "secondary", className: "bg-amber-500 text-white" };
    case "low":
      return { variant: "secondary", className: "bg-blue-500 text-white" };
    case "info":
      return { variant: "outline", className: "" };
    default:
      return { variant: "outline", className: "" };
  }
}

export function QualityGatesDrilldown({ protocolId }: { protocolId: number }) {
  const { data, isLoading } = useProtocolQualityGates(protocolId);

  const gates = useMemo(() => data?.gates ?? [], [data]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Quality Gates</CardTitle>
          <CardDescription>Loading…</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!gates || gates.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Quality Gates</CardTitle>
          <CardDescription>
            No gate results yet. Run QA for steps to populate gates.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quality Gates</CardTitle>
        <CardDescription>{gates.length} gate(s)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {gates.map((gate) => {
            const itemData = computeQualityGateListItemData(gate);
            const meta = statusMeta(gate.status);
            const Icon = meta.icon;
            const severityBadgeProps = getSeverityBadgeProps(itemData.maxSeverity);

            return (
              <Collapsible key={`${gate.article}:${gate.name}`} defaultOpen={false}>
                <div className="rounded-lg border">
                  <div className="flex items-center justify-between gap-3 p-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <CollapsibleTrigger className="flex items-center gap-1 text-left">
                          <ChevronRight className="text-muted-foreground h-4 w-4" />
                          <span className="font-medium">{gate.name}</span>
                        </CollapsibleTrigger>
                        <Badge variant="outline" className="text-[10px]">
                          {gate.article}
                        </Badge>
                        <Badge
                          variant={gate.status === "failed" ? "destructive" : "secondary"}
                          className={cn(gate.status === "passed" && "bg-green-500 text-white")}
                        >
                          <Icon className={cn("mr-1 h-4 w-4", meta.className)} />
                          {meta.label}
                        </Badge>
                        {itemData.hasSeverityIndicator && (
                          <Badge
                            variant={severityBadgeProps.variant}
                            className={cn("text-[10px]", severityBadgeProps.className)}
                          >
                            {itemData.maxSeverity.toUpperCase()}
                          </Badge>
                        )}
                      </div>
                      <div className="text-muted-foreground mt-1 text-xs">
                        Findings: {itemData.findingsCount}
                      </div>
                    </div>
                  </div>
                  <CollapsibleContent className="border-t p-3">
                    {itemData.findingsCount === 0 ? (
                      <div className="text-muted-foreground text-sm">
                        No findings recorded for this gate.
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {itemData.findings.map((finding, idx) => {
                          const findingSeverity = getSeverityFromFinding(finding);
                          const findingBadgeProps = getSeverityBadgeProps(findingSeverity);
                          return (
                            <div key={idx} className="bg-muted/40 rounded border p-3">
                              <div className="flex items-start gap-2">
                                {finding.severity && (
                                  <Badge
                                    variant={findingBadgeProps.variant}
                                    className={cn(
                                      "shrink-0 text-[10px]",
                                      findingBadgeProps.className
                                    )}
                                  >
                                    {findingSeverity.toUpperCase()}
                                  </Badge>
                                )}
                                <div className="min-w-0 flex-1">
                                  {finding.message ? (
                                    <div className="text-sm">{finding.message}</div>
                                  ) : (
                                    <pre className="overflow-auto text-xs">
                                      {JSON.stringify(finding, null, 2)}
                                    </pre>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </CollapsibleContent>
                </div>
              </Collapsible>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
