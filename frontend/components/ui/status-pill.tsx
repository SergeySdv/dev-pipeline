import type React from "react";

import {
  AlertCircle,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  Clock,
  Loader2,
  Pause,
  Play,
  Slash,
  XCircle,
} from "lucide-react";

import { cn } from "@/lib/utils";

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
  | "skipped"
  | "queued"
  | "succeeded"
  | "active"
  | "archived"
  | "planning"
  | "open"
  | "answered";

const statusConfig: Record<StatusType, { color: string; icon: React.ElementType; label?: string }> =
  {
    // Protocol/Step statuses
    pending: { color: "bg-neutral-100 text-neutral-500 border border-neutral-200", icon: Circle },
    planning: { color: "bg-neutral-200 text-neutral-700 border border-neutral-300", icon: Loader2 },
    planned: {
      color: "bg-blue-100 text-blue-700 border border-blue-200",
      icon: CheckCircle2,
    },
    running: { color: "bg-emerald-100 text-emerald-700 border border-emerald-200", icon: Play },
    paused: { color: "bg-amber-100 text-amber-700 border border-amber-200", icon: Pause },
    blocked: {
      color: "bg-orange-100 text-orange-700 border border-orange-200",
      icon: AlertCircle,
    },
    failed: { color: "bg-red-100 text-red-700 border border-red-200", icon: XCircle },
    cancelled: { color: "bg-neutral-50 text-neutral-400 border border-neutral-200", icon: Slash },
    completed: { color: "bg-green-100 text-green-700 border border-green-200", icon: CheckCircle2 },
    // Step statuses
    needs_qa: {
      color: "bg-purple-100 text-purple-700 border border-purple-200",
      icon: ClipboardCheck,
      label: "Needs QA",
    },
    skipped: {
      color: "bg-neutral-50 text-neutral-500 border border-neutral-200",
      icon: Slash,
      label: "Skipped",
    },
    // Run statuses
    queued: { color: "bg-slate-100 text-slate-600 border border-slate-200", icon: Clock },
    succeeded: { color: "bg-green-100 text-green-700 border border-green-200", icon: CheckCircle2 },
    // Sprint statuses
    active: { color: "bg-emerald-100 text-emerald-700 border border-emerald-200", icon: Play },
    archived: { color: "bg-neutral-50 text-neutral-400 border border-neutral-200", icon: Slash },
    // Clarification statuses
    open: { color: "bg-amber-100 text-amber-700 border border-amber-200", icon: Circle },
    answered: { color: "bg-green-100 text-green-700 border border-green-200", icon: CheckCircle2 },
  };

interface StatusPillProps {
  status: string;
  size?: "sm" | "md";
  className?: string;
}

export function StatusPill({ status, size = "md", className }: StatusPillProps) {
  const config = statusConfig[status as StatusType] || statusConfig.pending;
  const Icon = config.icon;
  const isAnimated = status === "planning" || status === "running";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium capitalize",
        config.color,
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
        className
      )}
    >
      <Icon className={cn("h-3 w-3", isAnimated && "animate-spin")} />
      {config.label || status.replace(/_/g, " ")}
    </span>
  );
}
