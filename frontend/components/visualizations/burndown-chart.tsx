"use client"

import { useMemo } from "react"
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { BurndownPoint } from "@/lib/api/types"

function formatDateLabel(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

export function BurndownChart({
  points,
  height = 240,
}: {
  points: BurndownPoint[]
  height?: number
}) {
  const data = useMemo(() => {
    return (points || []).map((p) => ({
      date: p.date,
      ideal: p.ideal,
      actual: p.actual,
      label: formatDateLabel(p.date),
    }))
  }, [points])

  if (!data || data.length === 0) {
    return <div className="text-sm text-muted-foreground py-6">No burndown data available.</div>
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} width={36} />
          <Tooltip
            labelFormatter={(_, payload) => {
              const first = payload?.[0]?.payload as { date?: string } | undefined
              return first?.date ? `Date: ${first.date}` : "Date"
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="ideal" stroke="#64748b" strokeWidth={2} dot={false} name="Ideal" />
          <Line type="monotone" dataKey="actual" stroke="#3b82f6" strokeWidth={2} dot={false} name="Actual" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

