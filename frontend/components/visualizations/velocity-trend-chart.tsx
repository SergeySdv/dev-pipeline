"use client"

import { useMemo } from "react"
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { cn } from "@/lib/utils"

/**
 * VelocityPoint represents a single sprint's velocity data
 */
export interface VelocityPoint {
  sprintName: string
  velocity: number
  sprintId?: number
}

/**
 * Calculate the arithmetic mean of velocity values
 * Used for property testing to verify average calculation
 * **Validates: Requirements 6.3**
 */
export function calculateVelocityAverage(data: VelocityPoint[]): number | null {
  if (!data || data.length === 0) return null
  const total = data.reduce((sum, point) => sum + point.velocity, 0)
  return total / data.length
}

/**
 * Calculate trend line points using linear regression
 * Returns an array of y-values for each x position
 */
export function calculateTrendLine(data: VelocityPoint[]): number[] {
  if (!data || data.length < 2) return []
  
  const n = data.length
  const velocities = data.map(d => d.velocity)
  
  // Calculate linear regression: y = mx + b
  // Using least squares method
  let sumX = 0
  let sumY = 0
  let sumXY = 0
  let sumX2 = 0
  
  for (let i = 0; i < n; i++) {
    sumX += i
    sumY += velocities[i]
    sumXY += i * velocities[i]
    sumX2 += i * i
  }
  
  const denominator = n * sumX2 - sumX * sumX
  if (denominator === 0) {
    // All x values are the same, return flat line at average
    const avg = sumY / n
    return velocities.map(() => avg)
  }
  
  const slope = (n * sumXY - sumX * sumY) / denominator
  const intercept = (sumY - slope * sumX) / n
  
  // Generate trend line values
  return velocities.map((_, i) => intercept + slope * i)
}

/**
 * Custom tooltip component for velocity chart
 * Shows sprint name and velocity points
 */
interface VelocityTooltipProps {
  active?: boolean
  payload?: Array<{
    name: string
    value: number
    color: string
    payload: { sprintName: string; velocity: number; trend?: number }
  }>
  label?: string
}

function VelocityTooltip({ active, payload }: VelocityTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  const data = payload[0]?.payload
  if (!data) return null

  return (
    <div className="bg-background border border-border rounded-md shadow-md p-3 text-sm">
      <p className="font-medium mb-2">{data.sprintName}</p>
      <div className="space-y-1">
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-muted-foreground">{entry.name}:</span>
            <span className="font-medium">
              {typeof entry.value === 'number' ? entry.value.toFixed(1) : entry.value} points
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export interface VelocityChartProps {
  /** Velocity data points with sprint name and velocity */
  data?: VelocityPoint[]
  /** Legacy: array of velocity values (will be converted to VelocityPoint[]) */
  values?: number[]
  /** Additional CSS classes */
  className?: string
  /** Chart height in pixels */
  height?: number
  /** Whether to show the trend line */
  showTrendLine?: boolean
  /** Whether to show the average reference line */
  showAverage?: boolean
}

/**
 * VelocityChart Component (VelocityTrendChart)
 * 
 * Renders a composed chart showing velocity per sprint with:
 * - Bars for velocity per sprint
 * - Trend line overlay showing velocity direction
 * - Average reference line
 * 
 * **Validates: Requirements 6.1, 6.2, 6.3**
 */
export function VelocityChart({
  data,
  values,
  className,
  height = 240,
  showTrendLine = true,
  showAverage = true,
}: VelocityChartProps) {
  // Convert legacy values array to VelocityPoint[] if needed
  const normalizedData = useMemo((): VelocityPoint[] => {
    if (data && data.length > 0) {
      return data
    }
    if (values && values.length > 0) {
      return values.map((v, i) => ({
        sprintName: `S${i + 1}`,
        velocity: v,
        sprintId: i + 1
      }))
    }
    return []
  }, [data, values])

  // Calculate average velocity
  const average = useMemo(() => {
    return calculateVelocityAverage(normalizedData)
  }, [normalizedData])

  // Calculate trend line values
  const trendValues = useMemo(() => {
    return calculateTrendLine(normalizedData)
  }, [normalizedData])

  // Prepare chart data with trend values
  const chartData = useMemo(() => {
    return normalizedData.map((point, index) => ({
      ...point,
      trend: trendValues[index] ?? null
    }))
  }, [normalizedData, trendValues])

  if (!chartData || chartData.length === 0) {
    return (
      <div className={cn("text-sm text-muted-foreground py-6", className)}>
        No velocity trend data available.
      </div>
    )
  }

  return (
    <div className={cn(className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="sprintName"
            tick={{ fontSize: 11 }}
            className="text-muted-foreground"
          />
          <YAxis
            tick={{ fontSize: 11 }}
            width={36}
            className="text-muted-foreground"
          />
          <Tooltip content={<VelocityTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          
          {/* Average reference line */}
          {showAverage && average != null && (
            <ReferenceLine
              y={average}
              stroke="#10b981"
              strokeDasharray="4 4"
              label={{
                value: `Avg: ${average.toFixed(1)}`,
                fontSize: 11,
                fill: "#10b981",
                position: "right"
              }}
            />
          )}
          
          {/* Velocity bars */}
          <Bar
            dataKey="velocity"
            fill="#a855f7"
            name="Velocity"
            radius={[4, 4, 0, 0]}
          />
          
          {/* Trend line overlay */}
          {showTrendLine && trendValues.length >= 2 && (
            <Line
              type="monotone"
              dataKey="trend"
              stroke="#f97316"
              strokeWidth={2}
              dot={false}
              name="Trend"
              connectNulls
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

// Legacy export for backward compatibility
export { VelocityChart as VelocityTrendChart }
export { VelocityChart as default }
