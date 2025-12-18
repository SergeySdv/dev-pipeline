"use client"

import { useProtocolPolicyFindings, useProtocolPolicySnapshot } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CodeBlock } from "@/components/ui/code-block"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { AlertCircle, AlertTriangle, Info, Shield } from "lucide-react"
import { truncateHash } from "@/lib/format"
import type { PolicyFinding } from "@/lib/api/types"

interface PolicyTabProps {
  protocolId: number
}

export function PolicyTab({ protocolId }: PolicyTabProps) {
  const { data: findings, isLoading: findingsLoading } = useProtocolPolicyFindings(protocolId)
  const { data: snapshot, isLoading: snapshotLoading } = useProtocolPolicySnapshot(protocolId)

  if (findingsLoading || snapshotLoading) return <LoadingState message="Loading policy..." />

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
  )
}

function FindingsList({ findings }: { findings: PolicyFinding[] }) {
  return (
    <div className="space-y-3">
      {findings.map((finding, index) => (
        <div key={index} className="flex items-start gap-3 rounded-lg border p-3">
          {finding.severity === "error" ? (
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
          ) : finding.severity === "warning" ? (
            <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
          ) : (
            <Info className="h-5 w-5 text-blue-500 mt-0.5" />
          )}
          <div className="flex-1 min-w-0">
            <p className="font-mono text-sm text-muted-foreground">{finding.code}</p>
            <p className="mt-1">{finding.message}</p>
            {finding.location && <p className="text-sm text-muted-foreground mt-1">Location: {finding.location}</p>}
            {finding.suggested_fix && (
              <p className="text-sm text-muted-foreground mt-1">Suggested fix: {finding.suggested_fix}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
