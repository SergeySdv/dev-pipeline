"use client"

import { useMemo } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronRight, CheckCircle2, AlertTriangle, XCircle, Shield } from "lucide-react"
import { useProtocolQualityGates } from "@/lib/api"

function statusMeta(status: string) {
  if (status === "passed") return { label: "Passed", icon: CheckCircle2, className: "text-green-600" }
  if (status === "warning") return { label: "Warning", icon: AlertTriangle, className: "text-amber-600" }
  if (status === "failed") return { label: "Failed", icon: XCircle, className: "text-red-600" }
  return { label: status || "Unknown", icon: Shield, className: "text-muted-foreground" }
}

export function QualityGatesDrilldown({ protocolId }: { protocolId: number }) {
  const { data, isLoading } = useProtocolQualityGates(protocolId)

  const gates = useMemo(() => data?.gates ?? [], [data])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Quality Gates</CardTitle>
          <CardDescription>Loading…</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!gates || gates.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Quality Gates</CardTitle>
          <CardDescription>No gate results yet. Run QA for steps to populate gates.</CardDescription>
        </CardHeader>
      </Card>
    )
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
            const meta = statusMeta(gate.status)
            const Icon = meta.icon
            const findings = Array.isArray(gate.findings) ? gate.findings : []
            return (
              <Collapsible key={`${gate.article}:${gate.name}`} defaultOpen={false}>
                <div className="rounded-lg border">
                  <div className="flex items-center justify-between gap-3 p-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <CollapsibleTrigger className="flex items-center gap-1 text-left">
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{gate.name}</span>
                        </CollapsibleTrigger>
                        <Badge variant="outline" className="text-[10px]">
                          {gate.article}
                        </Badge>
                        <Badge
                          variant={gate.status === "failed" ? "destructive" : "secondary"}
                          className={cn(gate.status === "passed" && "bg-green-500 text-white")}
                        >
                          <Icon className={cn("h-4 w-4 mr-1", meta.className)} />
                          {meta.label}
                        </Badge>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">Findings: {findings.length}</div>
                    </div>
                  </div>
                  <CollapsibleContent className="border-t p-3">
                    {findings.length === 0 ? (
                      <div className="text-sm text-muted-foreground">No findings recorded for this gate.</div>
                    ) : (
                      <pre className="text-xs bg-muted/40 rounded p-3 overflow-auto">
                        {JSON.stringify(findings, null, 2)}
                      </pre>
                    )}
                  </CollapsibleContent>
                </div>
              </Collapsible>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

