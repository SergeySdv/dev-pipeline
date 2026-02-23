"use client";

import { useMemo } from "react";

import { AlertCircle,Bot, Cpu, Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { LoadingState } from "@/components/ui/loading-state";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { type Agent,useAgents } from "@/lib/api";
import { cn } from "@/lib/utils";

// =============================================================================
// Types
// =============================================================================

export interface AgentSelectorProps {
  projectId?: number;
  value?: string;
  onChange: (agentId: string) => void;
  className?: string;
  placeholder?: string;
  disabled?: boolean;
  filterByCapability?: string;
  showStatus?: boolean;
  showModel?: boolean;
}

export type AgentKind = "code_gen" | "planning" | "exec" | "qa" | "discovery";

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Gets the icon component for an agent kind
 */
export function getAgentKindIcon(kind: string) {
  switch (kind) {
    case "code_gen":
      return Cpu;
    case "planning":
      return Zap;
    case "exec":
      return Bot;
    case "qa":
      return AlertCircle;
    case "discovery":
      return Bot;
    default:
      return Bot;
  }
}

/**
 * Gets the display label for an agent kind
 */
export function getAgentKindLabel(kind: string): string {
  switch (kind) {
    case "code_gen":
      return "Code Generation";
    case "planning":
      return "Planning";
    case "exec":
      return "Execution";
    case "qa":
      return "Quality Assurance";
    case "discovery":
      return "Discovery";
    default:
      return kind;
  }
}

/**
 * Gets the status color for an agent
 */
export function getAgentStatusColor(status: string): string {
  switch (status) {
    case "available":
      return "bg-green-500";
    case "busy":
      return "bg-yellow-500";
    case "unavailable":
      return "bg-red-500";
    default:
      return "bg-gray-500";
  }
}

/**
 * Groups agents by their kind
 */
export function groupAgentsByKind(agents: Agent[]): Record<string, Agent[]> {
  return agents.reduce(
    (acc, agent) => {
      const kind = agent.kind || "other";
      if (!acc[kind]) {
        acc[kind] = [];
      }
      acc[kind].push(agent);
      return acc;
    },
    {} as Record<string, Agent[]>
  );
}

/**
 * Filters agents by capability
 */
export function filterAgentsByCapability(agents: Agent[], capability: string): Agent[] {
  if (!capability) return agents;
  return agents.filter((agent) => agent.capabilities?.includes(capability) || false);
}

/**
 * Sorts agents by status (available first) then by name
 */
export function sortAgentsByStatusAndName(agents: Agent[]): Agent[] {
  const statusOrder = { available: 0, busy: 1, unavailable: 2 };
  return [...agents].sort((a, b) => {
    const statusDiff =
      (statusOrder[a.status as keyof typeof statusOrder] ?? 3) -
      (statusOrder[b.status as keyof typeof statusOrder] ?? 3);
    if (statusDiff !== 0) return statusDiff;
    return a.name.localeCompare(b.name);
  });
}

// =============================================================================
// Component
// =============================================================================

export function AgentSelector({
  projectId,
  value,
  onChange,
  className,
  placeholder = "Select an agent",
  disabled = false,
  filterByCapability,
  showStatus = true,
  showModel = false,
}: AgentSelectorProps) {
  const { data: agents, isLoading, error } = useAgents(projectId);

  // Filter, sort, and group agents
  const { groupedAgents, availableCount } = useMemo(() => {
    if (!agents) return { groupedAgents: {}, availableCount: 0 };

    let filtered = filterByCapability
      ? filterAgentsByCapability(agents, filterByCapability)
      : agents;

    filtered = sortAgentsByStatusAndName(filtered);
    const grouped = groupAgentsByKind(filtered);
    const available = filtered.filter((a) => a.status === "available").length;

    return { groupedAgents: grouped, availableCount: available };
  }, [agents, filterByCapability]);

  if (isLoading) {
    return <LoadingState message="Loading agents..." />;
  }

  if (error) {
    return (
      <div className="text-destructive flex items-center gap-2 text-sm">
        <AlertCircle className="h-4 w-4" />
        Failed to load agents
      </div>
    );
  }

  const selectedAgent = agents?.find((a) => a.id === value);
  const kinds = Object.keys(groupedAgents).sort();

  return (
    <Select value={value} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger className={cn("w-full", className)}>
        <SelectValue placeholder={placeholder}>
          {selectedAgent && (
            <div className="flex items-center gap-2">
              {showStatus && (
                <span
                  className={cn("h-2 w-2 rounded-full", getAgentStatusColor(selectedAgent.status))}
                />
              )}
              <span>{selectedAgent.name}</span>
              {showModel && selectedAgent.default_model && (
                <Badge variant="outline" className="ml-auto text-xs">
                  {selectedAgent.default_model}
                </Badge>
              )}
            </div>
          )}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          <SelectLabel className="flex items-center justify-between">
            <span>Available Agents</span>
            <Badge variant="secondary" className="text-xs">
              {availableCount} available
            </Badge>
          </SelectLabel>
        </SelectGroup>
        <SelectSeparator />

        {kinds.length === 0 ? (
          <div className="text-muted-foreground p-4 text-center text-sm">No agents available</div>
        ) : (
          kinds.map((kind, index) => (
            <SelectGroup key={kind}>
              {index > 0 && <SelectSeparator />}
              <SelectLabel>{getAgentKindLabel(kind)}</SelectLabel>
              {groupedAgents[kind].map((agent) => (
                <SelectItem
                  key={agent.id}
                  value={agent.id}
                  disabled={agent.status === "unavailable"}
                >
                  <div className="flex w-full items-center gap-2">
                    {showStatus && (
                      <span
                        className={cn(
                          "h-2 w-2 shrink-0 rounded-full",
                          getAgentStatusColor(agent.status)
                        )}
                      />
                    )}
                    <span className="flex-1">{agent.name}</span>
                    {agent.capabilities && agent.capabilities.length > 0 && (
                      <Badge variant="outline" className="text-xs">
                        {agent.capabilities.length} caps
                      </Badge>
                    )}
                    {showModel && agent.default_model && (
                      <Badge variant="secondary" className="text-xs">
                        {agent.default_model}
                      </Badge>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectGroup>
          ))
        )}
      </SelectContent>
    </Select>
  );
}

// =============================================================================
// Compact Variant
// =============================================================================

export interface CompactAgentSelectorProps extends Omit<
  AgentSelectorProps,
  "showStatus" | "showModel"
> {
  /** Show inline status indicator */
  inline?: boolean;
}

/**
 * A more compact version of the agent selector for use in tight spaces
 */
export function CompactAgentSelector({
  projectId,
  value,
  onChange,
  className,
  placeholder = "Agent",
  disabled = false,
  filterByCapability,
  inline = true,
}: CompactAgentSelectorProps) {
  const { data: agents, isLoading } = useAgents(projectId);

  const filteredAgents = useMemo(() => {
    if (!agents) return [];
    const filtered = filterByCapability
      ? filterAgentsByCapability(agents, filterByCapability)
      : agents;
    return sortAgentsByStatusAndName(filtered);
  }, [agents, filterByCapability]);

  if (isLoading) {
    return (
      <Select disabled>
        <SelectTrigger className={cn("w-[180px]", className)}>
          <SelectValue placeholder="Loading..." />
        </SelectTrigger>
      </Select>
    );
  }

  const selectedAgent = agents?.find((a) => a.id === value);

  return (
    <Select value={value} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger className={cn("w-[180px]", className)} size="sm">
        <SelectValue placeholder={placeholder}>
          {selectedAgent && inline && (
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  getAgentStatusColor(selectedAgent.status)
                )}
              />
              <span className="truncate">{selectedAgent.name}</span>
            </div>
          )}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {filteredAgents.length === 0 ? (
          <div className="text-muted-foreground p-2 text-center text-sm">No agents</div>
        ) : (
          filteredAgents.map((agent) => (
            <SelectItem key={agent.id} value={agent.id} disabled={agent.status === "unavailable"}>
              <div className="flex items-center gap-2">
                <span
                  className={cn("h-1.5 w-1.5 rounded-full", getAgentStatusColor(agent.status))}
                />
                <span>{agent.name}</span>
              </div>
            </SelectItem>
          ))
        )}
      </SelectContent>
    </Select>
  );
}
