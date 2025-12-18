import type React from "react"
import { cn } from "@/lib/utils"
import {
  Circle,
  Loader2,
  CheckCircle2,
  Play,
  Pause,
  AlertCircle,
  XCircle,
  Slash,
  Clock,
  ClipboardCheck,
} from "lucide-react"

type StatusType =
  | "pending"
  | "planning"
  | "planned"
  | "running"
  | "paused"
  | "blocked"
  | "failed"
  | "cancelled"
  | "completed"
  | "needs_qa"
  | "queued"
  | "succeeded"
  | "open"
  | "answered"

const statusConfig: Record<StatusType, { color: string; icon: React.ElementType; label?: string }> = {
  // Protocol statuses
  pending: { color: "bg-neutral-100 text-neutral-500 border border-neutral-200", icon: Circle },
  planning: { color: "bg-neutral-200 text-neutral-700 border border-neutral-300", icon: Loader2 },
  planned: { color: "bg-neutral-100 text-neutral-600 border border-neutral-200", icon: CheckCircle2 },
  running: { color: "bg-neutral-800 text-white border border-neutral-900", icon: Play },
  paused: { color: "bg-neutral-100 text-neutral-600 border border-neutral-300", icon: Pause },
  blocked: { color: "bg-neutral-200 text-neutral-700 border border-neutral-400", icon: AlertCircle },
  failed: { color: "bg-neutral-100 text-neutral-600 border border-neutral-300", icon: XCircle },
  cancelled: { color: "bg-neutral-50 text-neutral-400 border border-neutral-200", icon: Slash },
  completed: { color: "bg-neutral-900 text-white border border-neutral-950", icon: CheckCircle2 },
  // Step statuses
  needs_qa: {
    color: "bg-neutral-100 text-neutral-600 border border-neutral-300",
    icon: ClipboardCheck,
    label: "Needs QA",
  },
  // Run statuses
  queued: { color: "bg-neutral-50 text-neutral-500 border border-neutral-200", icon: Clock },
  succeeded: { color: "bg-neutral-900 text-white border border-neutral-950", icon: CheckCircle2 },
  // Clarification statuses
  open: { color: "bg-neutral-100 text-neutral-600 border border-neutral-300", icon: Circle },
  answered: { color: "bg-neutral-900 text-white border border-neutral-950", icon: CheckCircle2 },
}

interface StatusPillProps {
  status: string
  size?: "sm" | "md"
  className?: string
}

export function StatusPill({ status, size = "md", className }: StatusPillProps) {
  const config = statusConfig[status as StatusType] || statusConfig.pending
  const Icon = config.icon
  const isAnimated = status === "planning" || status === "running"

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium capitalize",
        config.color,
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
        className,
      )}
    >
      <Icon className={cn("h-3 w-3", isAnimated && "animate-spin")} />
      {config.label || status.replace(/_/g, " ")}
    </span>
  )
}
