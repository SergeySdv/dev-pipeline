"use client";

import { AlertCircle, AlertTriangle, Info, Shield } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { useProtocolPolicyFindings, useProtocolPolicySnapshot } from "@/lib/api";
import type { PolicyFinding } from "@/lib/api/types";
import { truncateHash } from "@/lib/format";

interface PolicyTabProps {
  protocolId: number;
}

export function PolicyTab({ protocolId }: PolicyTabProps) {
  const { data: findings, isLoading: findingsLoading } = useProtocolPolicyFindings(protocolId);
  const { data: snapshot, isLoading: snapshotLoading } = useProtocolPolicySnapshot(protocolId);

  if (findingsLoading || snapshotLoading) return <LoadingState message="Loading policy..." />;

  return (
    <div className="space-y-6">
      {findings && findings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Policy Findings</CardTitle>
            <CardDescription>{findings.length} finding(s)</CardDescription>
          </CardHeader>
          <CardContent>
            <FindingsList findings={findings} />
          </CardContent>
        </Card>
      )}

      {snapshot ? (
        <Card>
          <CardHeader>
            <CardTitle>Policy Snapshot</CardTitle>
            <CardDescription>Hash: {truncateHash(snapshot.hash, 16)}</CardDescription>
          </CardHeader>
          <CardContent>
            <CodeBlock code={snapshot.policy} title="Policy Snapshot" maxHeight="400px" />
          </CardContent>
        </Card>
      ) : (
        <EmptyState
          icon={Shield}
          title="No policy snapshot"
          description="Policy snapshot not available for this protocol."
        />
      )}
    </div>
  );
}

function FindingsList({ findings }: { findings: PolicyFinding[] }) {
  return (
    <div className="space-y-3">
      {findings.map((finding, index) => (
        <div key={index} className="flex items-start gap-3 rounded-lg border p-3">
          {finding.severity === "error" ? (
            <AlertCircle className="text-destructive mt-0.5 h-5 w-5" />
          ) : finding.severity === "warning" ? (
            <AlertTriangle className="mt-0.5 h-5 w-5 text-yellow-500" />
          ) : (
            <Info className="mt-0.5 h-5 w-5 text-blue-500" />
          )}
          <div className="min-w-0 flex-1">
            <p className="text-muted-foreground font-mono text-sm">{finding.code}</p>
            <p className="mt-1">{finding.message}</p>
            {finding.location && (
              <p className="text-muted-foreground mt-1 text-sm">Location: {finding.location}</p>
            )}
            {finding.suggested_fix && (
              <p className="text-muted-foreground mt-1 text-sm">
                Suggested fix: {finding.suggested_fix}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
