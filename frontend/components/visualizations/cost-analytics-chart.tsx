"use client"

import { useMemo } from "react"
import {
  Area,
  ComposedChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Bar,
  CartesianGrid,
} from "recharts"
import type { CodexRun } from "@/lib/api/types"
import { formatCost } from "@/lib/format"

type DailyCostRow = {
  date: string
  total_cents: number
  cumulative_cents: number
  by_type: Record<string, number>
}

function toDateKey(timestamp: string | null) {
  if (!timestamp) return null
  const d = new Date(timestamp)
  if (Number.isNaN(d.getTime())) return null
  return d.toISOString().slice(0, 10)
}

function pickTopTypes(byTypeTotals: Map<string, number>, topN: number) {
  return Array.from(byTypeTotals.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([k]) => k)
}

export function CostAnalyticsChart({
  runs,
  height = 260,
  topTypes = 5,
}: {
  runs: CodexRun[]
  height?: number
  topTypes?: number
}) {
  const { rows, keys } = useMemo(() => {
    const byDay = new Map<string, DailyCostRow>()
    const totalsByType = new Map<string, number>()

    for (const r of runs || []) {
      const day = toDateKey(r.created_at) ?? toDateKey(r.started_at) ?? toDateKey(r.finished_at)
      if (!day) continue
      const cents = r.cost_cents ?? 0
      if (cents <= 0) continue
      const jobType = r.job_type || "unknown"

      totalsByType.set(jobType, (totalsByType.get(jobType) ?? 0) + cents)

      const row = byDay.get(day) ?? { date: day, total_cents: 0, cumulative_cents: 0, by_type: {} }
      row.total_cents += cents
      row.by_type[jobType] = (row.by_type[jobType] ?? 0) + cents
      byDay.set(day, row)
    }

    const top = pickTopTypes(totalsByType, topTypes)
    const rowsSorted = Array.from(byDay.values()).sort((a, b) => (a.date < b.date ? -1 : 1))

    let cumulative = 0
    const normalized = rowsSorted.map((row) => {
      cumulative += row.total_cents
      const next: Record<string, unknown> = {
        date: row.date,
        total_cents: row.total_cents,
        cumulative_cents: cumulative,
      }
      let other = 0
      for (const [type, cents] of Object.entries(row.by_type)) {
        if (top.includes(type)) {
          next[type] = cents
        } else {
          other += cents
        }
      }
      if (other > 0) next.other = other
      return next
    })

    const stackKeys = [...top, ...(normalized.some((r) => "other" in r) ? ["other"] : [])]
    return { rows: normalized, keys: stackKeys }
  }, [runs, topTypes])

  if (!rows || rows.length === 0) {
    return <div className="text-sm text-muted-foreground py-6">No cost data in the current run set.</div>
  }

  const colors = ["#3b82f6", "#a855f7", "#10b981", "#f59e0b", "#ef4444", "#64748b"]

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis
            yAxisId="cents"
            tick={{ fontSize: 11 }}
            width={48}
            tickFormatter={(v) => `$${(Number(v) / 100).toFixed(0)}`}
          />
          <Tooltip
            formatter={(value, name) => {
              if (typeof value !== "number") return [value, name]
              if (name === "cumulative_cents") return [formatCost(value), "Cumulative"]
              if (name === "total_cents") return [formatCost(value), "Total"]
              return [formatCost(value), String(name)]
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />

          {keys.map((k, i) => (
            <Bar
              key={k}
              yAxisId="cents"
              dataKey={k}
              stackId="cost"
              fill={colors[i % colors.length]}
              name={k}
              radius={i === keys.length - 1 ? [4, 4, 0, 0] : 0}
            />
          ))}

          <Area
            yAxisId="cents"
            type="monotone"
            dataKey="cumulative_cents"
            stroke="#111827"
            fill="#111827"
            fillOpacity={0.06}
            name="cumulative_cents"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

