"use client"

import { useRef, useEffect, useMemo, useCallback } from "react"
import * as d3 from "d3"
import { graphStratify, sugiyama, decrossOpt, coordCenter } from "d3-dag"
import type { StepRun } from "@/lib/api/types"
import { cn } from "@/lib/utils"

interface PipelineDagProps {
  steps: StepRun[]
  onStepClick?: (step: StepRun) => void
  className?: string
  /** Currently selected step ID - used for highlighting */
  selectedStepId?: number | null
}

// Status color mapping per requirements 3.3
export function getStatusColor(status: string): string {
  switch (status) {
    case "running":
      return "#3b82f6" // blue
    case "completed":
      return "#22c55e" // green
    case "failed":
      return "#ef4444" // red
    case "pending":
    default:
      return "#9ca3af" // gray
  }
}

// Calculate duration from started_at and finished_at per requirements 3.6
export function calculateDuration(startedAt: string | null | undefined, finishedAt: string | null | undefined): string | null {
  if (!startedAt || !finishedAt) return null

  const start = new Date(startedAt).getTime()
  const end = new Date(finishedAt).getTime()

  if (isNaN(start) || isNaN(end)) return null

  const durationMs = end - start
  if (durationMs < 0) return null

  const seconds = Math.floor(durationMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  } else {
    return `${seconds}s`
  }
}

// Group steps by parallel_group for swimlane rendering per requirements 3.2
export function groupByParallelGroup(steps: StepRun[]): Map<string | null, StepRun[]> {
  const groups = new Map<string | null, StepRun[]>()

  for (const step of steps) {
    const group = step.parallel_group ?? null
    const existing = groups.get(group) ?? []
    existing.push(step)
    groups.set(group, existing)
  }

  return groups
}

// Build edges from depends_on relationships per requirements 3.1
export function buildEdges(steps: StepRun[]): Array<{ source: number; target: number }> {
  const edges: Array<{ source: number; target: number }> = []
  const stepById = new Map<number, StepRun>()
  const idByIndex = new Map<number, number>()

  for (const step of steps) {
    stepById.set(step.id, step)
    idByIndex.set(step.step_index, step.id)
  }

  for (const step of steps) {
    const deps = step.depends_on ?? []
    for (const dep of deps) {
      // Try to resolve dependency as step ID first, then as step_index
      let sourceId = dep
      if (!stepById.has(dep) && idByIndex.has(dep)) {
        sourceId = idByIndex.get(dep)!
      }

      if (stepById.has(sourceId)) {
        edges.push({ source: sourceId, target: step.id })
      }
    }
  }

  return edges
}

interface DagNode {
  id: string
  step: StepRun
  x: number
  y: number
}

interface DagEdge {
  source: string
  target: string
  points: Array<{ x: number; y: number }>
}

export function PipelineDag({ steps, onStepClick, className, selectedStepId }: PipelineDagProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Build lookup maps
  const { stepById, idByIndex } = useMemo(() => {
    const stepById = new Map<number, StepRun>()
    const idByIndex = new Map<number, number>()
    for (const step of steps) {
      stepById.set(step.id, step)
      idByIndex.set(step.step_index, step.id)
    }
    return { stepById, idByIndex }
  }, [steps])

  // Group steps by parallel_group for swimlanes
  const parallelGroups = useMemo(() => groupByParallelGroup(steps), [steps])

  // Calculate DAG layout using d3-dag
  const { nodes, edges, swimlanes, width, height } = useMemo(() => {
    if (steps.length === 0) {
      return { nodes: [], edges: [], swimlanes: [], width: 0, height: 0 }
    }

    const nodeWidth = 200
    const nodeHeight = 80
    const horizontalGap = 80
    const verticalGap = 40

    try {
      // Build DAG data structure for d3-dag
      // Create parent-child relationships from depends_on
      const dagData: Array<{ id: string; parentIds: string[] }> = steps.map(step => {
        const deps = step.depends_on ?? []
        const parentIds = deps
          .map(dep => {
            // Try to resolve dependency as step ID first, then as step_index
            if (stepById.has(dep)) return String(dep)
            if (idByIndex.has(dep)) return String(idByIndex.get(dep))
            return null
          })
          .filter((id): id is string => id !== null)

        return {
          id: String(step.id),
          parentIds
        }
      })

      // Create the DAG using graphStratify
      const stratify = graphStratify()
      const dag = stratify(dagData)

      // Apply sugiyama layout algorithm
      const layout = sugiyama()
        .decross(decrossOpt())
        .coord(coordCenter())
        .nodeSize(() => [nodeWidth + horizontalGap, nodeHeight + verticalGap])

      const { width: layoutWidth, height: layoutHeight } = layout(dag)

      // Extract node positions
      const dagNodes: DagNode[] = []
      for (const node of dag.nodes()) {
        const step = stepById.get(parseInt(node.data.id))
        if (step) {
          dagNodes.push({
            id: node.data.id,
            step,
            x: node.x,
            y: node.y
          })
        }
      }

      // Extract edges with points
      const dagEdges: DagEdge[] = []
      for (const link of dag.links()) {
        // d3-dag returns points as [x, y] tuples
        const points = link.points.map(p => ({ x: p[0], y: p[1] }))
        dagEdges.push({
          source: link.source.data.id,
          target: link.target.data.id,
          points
        })
      }

      // Calculate swimlane backgrounds
      const swimlaneData: Array<{ group: string | null; minY: number; maxY: number; color: string }> = []
      const groupColors = ["#f0f9ff", "#f0fdf4", "#fefce8", "#fdf2f8", "#f5f3ff"]
      let colorIndex = 0

      for (const [group, groupSteps] of parallelGroups) {
        if (group === null) continue // Skip ungrouped steps

        const groupNodeIds = new Set(groupSteps.map(s => String(s.id)))
        const groupNodes = dagNodes.filter(n => groupNodeIds.has(n.id))

        if (groupNodes.length > 0) {
          const minY = Math.min(...groupNodes.map(n => n.y)) - nodeHeight / 2 - 10
          const maxY = Math.max(...groupNodes.map(n => n.y)) + nodeHeight / 2 + 10

          swimlaneData.push({
            group,
            minY,
            maxY,
            color: groupColors[colorIndex % groupColors.length]
          })
          colorIndex++
        }
      }

      return {
        nodes: dagNodes,
        edges: dagEdges,
        swimlanes: swimlaneData,
        width: layoutWidth + nodeWidth + 100,
        height: layoutHeight + nodeHeight + 100
      }
    } catch {
      // Fallback to simple layout if d3-dag fails (e.g., cyclic dependencies)
      const fallbackNodes: DagNode[] = steps.map((step, index) => ({
        id: String(step.id),
        step,
        x: 100 + (index % 3) * (nodeWidth + horizontalGap),
        y: 100 + Math.floor(index / 3) * (nodeHeight + verticalGap)
      }))

      const fallbackEdges: DagEdge[] = buildEdges(steps).map(edge => ({
        source: String(edge.source),
        target: String(edge.target),
        points: []
      }))

      return {
        nodes: fallbackNodes,
        edges: fallbackEdges,
        swimlanes: [],
        width: 100 + 3 * (nodeWidth + horizontalGap),
        height: 100 + Math.ceil(steps.length / 3) * (nodeHeight + verticalGap)
      }
    }
  }, [steps, stepById, idByIndex, parallelGroups])

  // Handle step click
  const handleStepClick = useCallback((step: StepRun) => {
    onStepClick?.(step)
  }, [onStepClick])

  // Render D3 visualization with zoom/pan support
  useEffect(() => {
    if (!svgRef.current || !containerRef.current || nodes.length === 0) return

    const svg = d3.select(svgRef.current)
    const container = containerRef.current

    // Clear previous content
    svg.selectAll("*").remove()

    // Create main group for zoom/pan
    const g = svg.append("g").attr("class", "dag-content")

    // Add zoom behavior per requirements 3.5
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform)
      })

    svg.call(zoom)

    // Initial transform to center the DAG
    const containerWidth = container.clientWidth
    const containerHeight = container.clientHeight
    const initialScale = Math.min(
      containerWidth / (width + 50),
      containerHeight / (height + 50),
      1
    )
    const initialX = (containerWidth - width * initialScale) / 2
    const initialY = 20

    svg.call(zoom.transform, d3.zoomIdentity.translate(initialX, initialY).scale(initialScale))

    // Render swimlane backgrounds per requirements 3.2
    const swimlaneGroup = g.append("g").attr("class", "swimlanes")

    swimlaneGroup.selectAll("rect.swimlane")
      .data(swimlanes)
      .enter()
      .append("rect")
      .attr("class", "swimlane")
      .attr("x", 0)
      .attr("y", d => d.minY)
      .attr("width", width)
      .attr("height", d => d.maxY - d.minY)
      .attr("fill", d => d.color)
      .attr("stroke", "#e5e7eb")
      .attr("stroke-width", 1)
      .attr("rx", 8)

    // Add swimlane labels
    swimlaneGroup.selectAll("text.swimlane-label")
      .data(swimlanes)
      .enter()
      .append("text")
      .attr("class", "swimlane-label")
      .attr("x", 10)
      .attr("y", d => d.minY + 20)
      .attr("fill", "#6b7280")
      .attr("font-size", "12px")
      .attr("font-weight", "500")
      .text(d => `Group: ${d.group}`)

    // Render edges per requirements 3.1
    const edgeGroup = g.append("g").attr("class", "edges")

    const line = d3.line<{ x: number; y: number }>()
      .x(d => d.x)
      .y(d => d.y)
      .curve(d3.curveBasis)

    edgeGroup.selectAll("path.edge")
      .data(edges)
      .enter()
      .append("path")
      .attr("class", "edge")
      .attr("d", d => {
        if (d.points.length > 0) {
          return line(d.points)
        }
        // Fallback for edges without points
        const sourceNode = nodes.find(n => n.id === d.source)
        const targetNode = nodes.find(n => n.id === d.target)
        if (sourceNode && targetNode) {
          return line([
            { x: sourceNode.x, y: sourceNode.y + 40 },
            { x: targetNode.x, y: targetNode.y - 40 }
          ])
        }
        return ""
      })
      .attr("fill", "none")
      .attr("stroke", "#94a3b8")
      .attr("stroke-width", 2)
      .attr("marker-end", "url(#arrowhead)")

    // Define arrowhead marker
    svg.append("defs")
      .append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 8)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#94a3b8")

    // Render nodes per requirements 3.3
    const nodeGroup = g.append("g").attr("class", "nodes")

    const nodeWidth = 200
    const nodeHeight = 80

    const nodeElements = nodeGroup.selectAll("g.node")
      .data(nodes)
      .enter()
      .append("g")
      .attr("class", "node")
      .attr("transform", d => `translate(${d.x - nodeWidth / 2}, ${d.y - nodeHeight / 2})`)
      .style("cursor", "pointer")
      .on("click", (_, d) => handleStepClick(d.step))

    // Node background with status color
    nodeElements.append("rect")
      .attr("width", nodeWidth)
      .attr("height", nodeHeight)
      .attr("rx", 8)
      .attr("fill", "#ffffff")
      .attr("stroke", d => getStatusColor(d.step.status))
      .attr("stroke-width", d => d.step.id === selectedStepId ? 3 : 2)
      .attr("filter", "drop-shadow(0 1px 2px rgb(0 0 0 / 0.1))")

    // Selection ring for selected node per Requirements 4.4
    nodeElements.filter(d => d.step.id === selectedStepId)
      .insert("rect", ":first-child")
      .attr("x", -4)
      .attr("y", -4)
      .attr("width", nodeWidth + 8)
      .attr("height", nodeHeight + 8)
      .attr("rx", 12)
      .attr("fill", "none")
      .attr("stroke", "#6366f1")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "4,2")

    // Status indicator circle
    nodeElements.append("circle")
      .attr("cx", 16)
      .attr("cy", 16)
      .attr("r", 6)
      .attr("fill", d => getStatusColor(d.step.status))

    // Step index badge
    nodeElements.append("text")
      .attr("x", 30)
      .attr("y", 20)
      .attr("fill", "#6b7280")
      .attr("font-size", "10px")
      .attr("font-family", "monospace")
      .text(d => `Step ${d.step.step_index}`)

    // Step name
    nodeElements.append("text")
      .attr("x", 10)
      .attr("y", 40)
      .attr("fill", "#1f2937")
      .attr("font-size", "12px")
      .attr("font-weight", "600")
      .text(d => {
        const name = d.step.step_name
        return name.length > 25 ? name.substring(0, 22) + "..." : name
      })

    // Duration display per requirements 3.6
    nodeElements.append("text")
      .attr("x", 10)
      .attr("y", 58)
      .attr("fill", "#9ca3af")
      .attr("font-size", "10px")
      .text(d => {
        // Access runtime_state for timing if available, otherwise use step fields
        const startedAt = (d.step.runtime_state as { started_at?: string } | null)?.started_at
        const finishedAt = (d.step.runtime_state as { finished_at?: string } | null)?.finished_at
        const duration = calculateDuration(startedAt, finishedAt)
        return duration ? `Duration: ${duration}` : d.step.status
      })

    // Parallel group badge
    nodeElements.filter(d => !!d.step.parallel_group)
      .append("text")
      .attr("x", nodeWidth - 10)
      .attr("y", 20)
      .attr("text-anchor", "end")
      .attr("fill", "#8b5cf6")
      .attr("font-size", "10px")
      .text(d => d.step.parallel_group ?? "")

  }, [nodes, edges, swimlanes, width, height, handleStepClick, selectedStepId])

  if (steps.length === 0) {
    return (
      <div className={cn("rounded-lg border bg-muted/20 p-6 text-sm text-muted-foreground", className)}>
        No steps to display
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className={cn("rounded-lg border bg-white overflow-hidden", className)}
      style={{ minHeight: "400px" }}
    >
      <div className="p-3 border-b bg-muted/30 text-xs text-muted-foreground flex items-center justify-between">
        <span>DAG View • Scroll to zoom, drag to pan • Click a node to view details</span>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-blue-500"></span> Running
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-green-500"></span> Completed
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-red-500"></span> Failed
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-gray-400"></span> Pending
          </span>
        </div>
      </div>
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        style={{ minHeight: "350px" }}
        className="dag-svg"
      />
    </div>
  )
}
