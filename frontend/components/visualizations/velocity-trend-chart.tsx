"use client"

import { useMemo } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

export function VelocityTrendChart({
  values,
  height = 240,
}: {
  values: number[]
  height?: number
}) {
  const data = useMemo(() => {
    return (values || []).map((v, i) => ({ sprint: `S${i + 1}`, velocity: v }))
  }, [values])

  const average = useMemo(() => {
    if (!values || values.length === 0) return null
    const total = values.reduce((sum, v) => sum + v, 0)
    return total / values.length
  }, [values])

  if (!data || data.length === 0) {
    return <div className="text-sm text-muted-foreground py-6">No velocity trend data available.</div>
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="sprint" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} width={36} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {average != null && (
            <ReferenceLine y={average} stroke="#10b981" strokeDasharray="4 4" label={{ value: "Avg", fontSize: 11 }} />
          )}
          <Bar dataKey="velocity" fill="#a855f7" name="Velocity" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

