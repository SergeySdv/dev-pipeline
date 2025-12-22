"use client"

import { useMemo } from "react"
import type { StepRun } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { StatusPill } from "@/components/ui/status-pill"

interface PipelineDagProps {
  steps: StepRun[]
  onStepClick?: (step: StepRun) => void
  className?: string
}

type DagNode = {
  id: number
  step: StepRun
  level: number
}

type StepIndexMap = Map<number, number>
type StepIdMap = Map<number, StepRun>

function buildLookupMaps(steps: StepRun[]): { stepById: StepIdMap; idByIndex: StepIndexMap } {
  const stepById = new Map<number, StepRun>()
  const idByIndex = new Map<number, number>()
  for (const step of steps) {
    stepById.set(step.id, step)
    idByIndex.set(step.step_index, step.id)
  }
  return { stepById, idByIndex }
}

function resolveDependencyStepId(stepById: StepIdMap, idByIndex: StepIndexMap, dep: number): number | null {
  if (stepById.has(dep)) return dep
  return idByIndex.get(dep) ?? null
}

function computeDagLevels(steps: StepRun[]) {
  const { stepById, idByIndex } = buildLookupMaps(steps)
  const incoming = new Map<number, Set<number>>()

  for (const step of steps) {
    const deps = (step.depends_on ?? [])
      .map((d) => resolveDependencyStepId(stepById, idByIndex, d))
      .filter((v): v is number => v != null)
    incoming.set(step.id, new Set(deps))
  }

  const visiting = new Set<number>()
  const memo = new Map<number, number>()

  const levelOf = (id: number): number => {
    if (memo.has(id)) return memo.get(id)!
    if (visiting.has(id)) {
      // Cycle: degrade to a stable but safe layout.
      const fallback = stepById.get(id)?.step_index ?? 0
      memo.set(id, fallback)
      return fallback
    }

    visiting.add(id)
    const deps = incoming.get(id) ?? new Set<number>()
    let level = 0
    for (const depId of deps) {
      level = Math.max(level, levelOf(depId) + 1)
    }
    visiting.delete(id)
    memo.set(id, level)
    return level
  }

  return steps.map((step) => ({ id: step.id, step, level: levelOf(step.id) }))
}

export function PipelineDag({ steps, onStepClick, className }: PipelineDagProps) {
  const { stepById, idByIndex } = useMemo(() => buildLookupMaps(steps), [steps])
  const nodes = useMemo<DagNode[]>(() => computeDagLevels(steps), [steps])

  const columns = useMemo(() => {
    const byLevel = new Map<number, DagNode[]>()
    for (const node of nodes) {
      const group = byLevel.get(node.level) ?? []
      group.push(node)
      byLevel.set(node.level, group)
    }
    const levels = Array.from(byLevel.keys()).sort((a, b) => a - b)
    return levels.map((lvl) => ({
      level: lvl,
      nodes: (byLevel.get(lvl) ?? []).slice().sort((a, b) => a.step.step_index - b.step.step_index),
    }))
  }, [nodes])

  if (steps.length === 0) {
    return <div className={cn("rounded-lg border bg-muted/20 p-6 text-sm text-muted-foreground", className)}>No steps</div>
  }

  return (
    <div className={cn("rounded-lg border bg-muted/10 overflow-auto", className)}>
      <div className="p-3 border-b bg-muted/30 text-xs text-muted-foreground">
        DAG view (beta) • Nodes are grouped by dependency depth • Click a node to open its step
      </div>
      <div className="p-4">
        <div
          className="grid gap-4"
          style={{
            gridTemplateColumns: `repeat(${Math.max(1, columns.length)}, minmax(260px, 1fr))`,
          }}
        >
          {columns.map((col) => (
            <div key={col.level} className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs font-medium text-muted-foreground">Level {col.level}</div>
                <Badge variant="secondary" className="text-[10px] h-5 px-1.5">
                  {col.nodes.length}
                </Badge>
              </div>
              {col.nodes.map((node) => (
                <button
                  type="button"
                  key={node.id}
                  className={cn(
                    "w-full text-left rounded-md border bg-card p-3 shadow-sm transition-colors hover:bg-muted/40",
                    node.step.status === "running" && "border-blue-500/30",
                    node.step.status === "completed" && "border-green-500/30",
                    node.step.status === "failed" && "border-red-500/40",
                  )}
                  onClick={() => onStepClick?.(node.step)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px] font-mono">
                          Step {node.step.step_index}
                        </Badge>
                        {node.step.parallel_group && (
                          <Badge variant="secondary" className="text-[10px]">
                            Group: {node.step.parallel_group}
                          </Badge>
                        )}
                        {(node.step.engine_id || node.step.assigned_agent) && (
                          <Badge variant="outline" className="text-[10px]">
                            Agent: {node.step.engine_id ?? node.step.assigned_agent}
                          </Badge>
                        )}
                      </div>
                      <div className="mt-1 font-medium truncate">{node.step.step_name}</div>
                      {node.step.summary && (
                        <div className="mt-1 text-xs text-muted-foreground line-clamp-2">{node.step.summary}</div>
                      )}
                      {node.step.depends_on && node.step.depends_on.length > 0 && (
                        <div className="mt-2 text-[10px] text-muted-foreground">
                          Depends on:{" "}
                          {node.step.depends_on
                            .map((dep) => resolveDependencyStepId(stepById, idByIndex, dep))
                            .map((depId, i) => {
                              if (depId == null) return `?(${node.step.depends_on?.[i] ?? "unknown"})`
                              return stepById.get(depId)?.step_name ?? String(depId)
                            })
                            .join(", ")}
                        </div>
                      )}
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
                        <span className="capitalize">Type: {node.step.step_type}</span>
                        {node.step.model && <span>• Model: {node.step.model}</span>}
                        {node.step.retries > 0 && <span className="text-yellow-700">• Retries: {node.step.retries}</span>}
                      </div>
                    </div>
                    <StatusPill status={node.step.status} size="sm" />
                  </div>
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
