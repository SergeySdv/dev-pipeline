"use client"

import { useState } from "react"
import Link from "next/link"
import { useProtocols } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { StatusPill } from "@/components/ui/status-pill"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { Search, Filter, Play, Pause, CheckCircle, XCircle, AlertTriangle } from "lucide-react"
import { formatRelativeTime } from "@/lib/format"
import type { ProtocolRun } from "@/lib/api/types"

export default function ProtocolsPage() {
  const { data: protocols, isLoading, error } = useProtocols()
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")

  if (isLoading) return <LoadingState message="Loading protocols..." />
  if (error) return <EmptyState title="Error loading protocols" description={error.message} />

  // Filter protocols
  const filteredProtocols = protocols?.filter((protocol) => {
    const matchesSearch =
      search === "" ||
      protocol.name.toLowerCase().includes(search.toLowerCase()) ||
      protocol.id.toString().includes(search)
    const matchesStatus = statusFilter === "all" || protocol.status === statusFilter
    return matchesSearch && matchesStatus
  })

  // Count by status
  const statusCounts = protocols?.reduce(
    (acc, p) => {
      acc[p.status] = (acc[p.status] || 0) + 1
      return acc
    },
    {} as Record<string, number>,
  )

  return (
    <div className="container py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Protocols</h1>
        <p className="text-muted-foreground">View and manage all protocol executions</p>
      </div>

      {/* Status Overview */}
      <div className="grid gap-4 md:grid-cols-5 mb-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{protocols?.length || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground">Running</CardTitle>
            <Play className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{statusCounts?.running || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground">Paused</CardTitle>
            <Pause className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{statusCounts?.paused || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground">Completed</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{statusCounts?.completed || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{statusCounts?.failed || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search protocols by name or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="paused">Paused</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="blocked">Blocked</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Protocol List */}
      {!filteredProtocols || filteredProtocols.length === 0 ? (
        <EmptyState
          icon={AlertTriangle}
          title={search || statusFilter !== "all" ? "No protocols found" : "No protocols yet"}
          description={
            search || statusFilter !== "all"
              ? "Try adjusting your filters"
              : "Protocols will appear here when they are created"
          }
          action={
            search || statusFilter !== "all" ? (
              <Button
                variant="outline"
                onClick={() => {
                  setSearch("")
                  setStatusFilter("all")
                }}
              >
                Clear Filters
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredProtocols.map((protocol) => (
            <ProtocolCard key={protocol.id} protocol={protocol} />
          ))}
        </div>
      )}
    </div>
  )
}

function ProtocolCard({ protocol }: { protocol: ProtocolRun }) {
  return (
    <Link href={`/protocols/${protocol.id}`}>
      <Card className="h-full transition-colors hover:border-primary/50">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-lg truncate">{protocol.name}</CardTitle>
              <CardDescription className="text-xs">ID: {protocol.id}</CardDescription>
            </div>
            <StatusPill status={protocol.status} />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p className="text-muted-foreground text-xs">Project</p>
              <p className="font-medium">Project {protocol.project_id}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Branch</p>
              <p className="font-medium truncate">{protocol.branch || "main"}</p>
            </div>
          </div>

          {protocol.step_index !== undefined && protocol.total_steps !== undefined && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Progress</span>
                <span className="font-medium">
                  {protocol.step_index} / {protocol.total_steps}
                </span>
              </div>
              <div className="w-full bg-muted rounded-full h-1.5">
                <div
                  className="bg-primary h-1.5 rounded-full transition-all"
                  style={{
                    width: `${protocol.total_steps > 0 ? (protocol.step_index / protocol.total_steps) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          )}

          {protocol.blocked_reason && (
            <div className="flex items-start gap-2 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded text-xs">
              <AlertTriangle className="h-3 w-3 text-yellow-500 mt-0.5 shrink-0" />
              <p className="text-yellow-600 dark:text-yellow-400">{protocol.blocked_reason}</p>
            </div>
          )}

          <p className="text-xs text-muted-foreground">Updated {formatRelativeTime(protocol.updated_at)}</p>
        </CardContent>
      </Card>
    </Link>
  )
}
