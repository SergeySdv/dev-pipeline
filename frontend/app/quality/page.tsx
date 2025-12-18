"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { CheckCircle2, AlertTriangle, XCircle, Shield, FileCheck, RefreshCw } from "lucide-react"

export default function QualityPage() {
  // Mock QA data
  const qaOverview = {
    totalProtocols: 12,
    passed: 8,
    warnings: 3,
    failed: 1,
    averageScore: 87,
  }

  const recentFindings = [
    {
      id: 1,
      protocolId: 42,
      projectName: "tasksgodzilla-web",
      article: "III",
      articleName: "Code Quality",
      severity: "error",
      message: "Test coverage below 80%",
      timestamp: "2025-01-20 14:30",
    },
    {
      id: 2,
      protocolId: 43,
      projectName: "api-service",
      article: "IV",
      articleName: "Security",
      severity: "warning",
      message: "Deprecated dependency detected",
      timestamp: "2025-01-20 12:15",
    },
    {
      id: 3,
      protocolId: 44,
      projectName: "tasksgodzilla-web",
      article: "IX",
      articleName: "Documentation",
      severity: "warning",
      message: "Missing API documentation",
      timestamp: "2025-01-19 16:45",
    },
  ]

  const constitutionalGates = [
    { article: "I", name: "No Breaking Changes", status: "passed", checks: 45 },
    { article: "II", name: "Backward Compatibility", status: "passed", checks: 38 },
    { article: "III", name: "Code Quality", status: "failed", checks: 52 },
    { article: "IV", name: "Security", status: "warning", checks: 41 },
    { article: "V", name: "Scope Control", status: "passed", checks: 29 },
    { article: "IX", name: "Documentation", status: "warning", checks: 35 },
  ]

  const statusIcons = {
    passed: <CheckCircle2 className="h-4 w-4 text-green-500" />,
    warning: <AlertTriangle className="h-4 w-4 text-amber-500" />,
    failed: <XCircle className="h-4 w-4 text-red-500" />,
  }

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Quality Assurance</h1>
        <p className="text-sm text-muted-foreground">Constitutional gates and quality metrics</p>
      </div>

      <div className="bg-muted/50 border rounded-lg p-4">
        <div className="flex items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-md bg-blue-500/10 flex items-center justify-center">
              <Shield className="h-4 w-4 text-blue-500" />
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">Total Protocols</div>
              <div className="text-2xl font-bold">{qaOverview.totalProtocols}</div>
            </div>
          </div>

          <div className="h-12 w-px bg-border" />

          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-md bg-green-500/10 flex items-center justify-center">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">Passed</div>
              <div className="text-2xl font-bold">{qaOverview.passed}</div>
            </div>
          </div>

          <div className="h-12 w-px bg-border" />

          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-md bg-amber-500/10 flex items-center justify-center">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">Warnings</div>
              <div className="text-2xl font-bold">{qaOverview.warnings}</div>
            </div>
          </div>

          <div className="h-12 w-px bg-border" />

          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-md bg-red-500/10 flex items-center justify-center">
              <XCircle className="h-4 w-4 text-red-500" />
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">Failed</div>
              <div className="text-2xl font-bold">{qaOverview.failed}</div>
            </div>
          </div>

          <div className="h-12 w-px bg-border" />

          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-md bg-purple-500/10 flex items-center justify-center">
              <FileCheck className="h-4 w-4 text-purple-500" />
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">Avg Score</div>
              <div className="text-2xl font-bold">{qaOverview.averageScore}%</div>
            </div>
          </div>

          <div className="flex-1" />

          <div className="text-right">
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Quick Actions</div>
            <Button variant="outline" size="sm">
              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
              Refresh All
            </Button>
          </div>
        </div>
      </div>

      <Tabs defaultValue="gates" className="flex-1">
        <TabsList>
          <TabsTrigger value="gates">Constitutional Gates</TabsTrigger>
          <TabsTrigger value="findings">Recent Findings</TabsTrigger>
        </TabsList>

        <TabsContent value="gates" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Gate Status</CardTitle>
              <CardDescription>Status of all constitutional quality gates</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {constitutionalGates.map((gate) => (
                  <div key={gate.article} className="flex items-center justify-between rounded-lg border p-4">
                    <div className="flex items-center gap-3">
                      {statusIcons[gate.status]}
                      <div>
                        <div className="font-medium">
                          Article {gate.article}: {gate.name}
                        </div>
                        <div className="text-sm text-muted-foreground">{gate.checks} checks performed</div>
                      </div>
                    </div>
                    <Badge
                      variant={
                        gate.status === "passed" ? "default" : gate.status === "warning" ? "secondary" : "destructive"
                      }
                    >
                      {gate.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="findings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Findings</CardTitle>
              <CardDescription>Latest quality issues and warnings</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recentFindings.map((finding) => (
                  <div key={finding.id} className="flex items-start gap-3 rounded-lg border p-4">
                    {finding.severity === "error" ? (
                      <XCircle className="mt-0.5 h-5 w-5 text-red-500" />
                    ) : (
                      <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-500" />
                    )}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{finding.message}</span>
                        <Badge variant="outline" className="text-xs">
                          Article {finding.article}
                        </Badge>
                      </div>
                      <div className="mt-1 text-sm text-muted-foreground">
                        {finding.projectName} • Protocol #{finding.protocolId} • {finding.timestamp}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
