"use client"

import { useProtocol, useProtocolSteps, useProjectProtocols } from "@/lib/api"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { PipelineVisualizer } from "@/components/workflow/pipeline-visualizer"
import { Workflow } from "lucide-react"
import { toast } from "sonner"
import { useRouter } from "next/navigation"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { useEffect, useRef, useState } from "react"
import type { StepRun } from "@/lib/api/types"
import { useEventStream } from "@/lib/api"
import { useVisibility } from "@/lib/hooks/use-visibility"
import { useQueryClient } from "@tanstack/react-query"
import { queryKeys } from "@/lib/api/query-keys"

interface WorkflowTabProps {
  projectId: number
}

export function WorkflowTab({ projectId }: WorkflowTabProps) {
  const { data: protocols, isLoading: protocolsLoading } = useProjectProtocols(projectId)
  const [selectedProtocolId, setSelectedProtocolId] = useState<number | null>(null)
  const queryClient = useQueryClient()
  const isVisible = useVisibility()
  const invalidateTimeoutRef = useRef<number | null>(null)

  const protocolId = selectedProtocolId || protocols?.[0]?.id || null
  const { data: protocol, isLoading: protocolLoading } = useProtocol(protocolId!)
  const { data: steps, isLoading: stepsLoading } = useProtocolSteps(protocolId!)
  const router = useRouter()

  useEventStream(
    protocolId
      ? {
          protocol_id: protocolId,
        }
      : null,
    {
      enabled: Boolean(protocolId) && isVisible,
      onEvent: () => {
        if (!protocolId) return
        if (invalidateTimeoutRef.current != null) return
        invalidateTimeoutRef.current = window.setTimeout(() => {
          queryClient.invalidateQueries({ queryKey: queryKeys.protocols.detail(protocolId) })
          queryClient.invalidateQueries({ queryKey: queryKeys.protocols.steps(protocolId) })
          queryClient.invalidateQueries({ queryKey: queryKeys.protocols.events(protocolId) })
          queryClient.invalidateQueries({ queryKey: queryKeys.projects.protocols(projectId) })
          invalidateTimeoutRef.current = null
        }, 250)
      },
    },
  )

  useEffect(() => {
    return () => {
      if (invalidateTimeoutRef.current != null) {
        window.clearTimeout(invalidateTimeoutRef.current)
        invalidateTimeoutRef.current = null
      }
    }
  }, [])

  const handleStepClick = (step: StepRun) => {
    router.push(`/steps/${step.id}`)
  }

  const handleAssignAgent = (stepId: number, agentId: string) => {
    toast.success(`Agent ${agentId} assigned to step ${stepId}`)
  }

  if (protocolsLoading) return <LoadingState message="Loading workflows..." />

  if (!protocols || protocols.length === 0) {
    return (
      <EmptyState
        icon={Workflow}
        title="No workflows yet"
        description="Create a protocol to visualize its workflow pipeline"
      />
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <div className="flex-1 space-y-2">
          <Label htmlFor="protocol-select">Select Protocol Workflow</Label>
          <Select value={protocolId?.toString() || ""} onValueChange={(value) => setSelectedProtocolId(Number(value))}>
            <SelectTrigger id="protocol-select" className="w-full">
              <SelectValue placeholder="Select a protocol" />
            </SelectTrigger>
            <SelectContent>
              {protocols.map((p) => (
                <SelectItem key={p.id} value={p.id.toString()}>
                  {p.protocol_name} - {p.status}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {protocolLoading || stepsLoading ? (
        <LoadingState message="Loading pipeline..." />
      ) : protocol && steps ? (
        <PipelineVisualizer
          protocol={protocol}
          steps={steps}
          onStepClick={handleStepClick}
          onAssignAgent={handleAssignAgent}
        />
      ) : (
        <EmptyState icon={Workflow} title="No pipeline data" description="Unable to load pipeline visualization" />
      )}
    </div>
  )
}
