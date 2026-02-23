"use client";

import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RefreshButtonProps {
  /** Refresh handler */
  onRefresh: () => void;
  /** Is currently refreshing */
  isRefreshing?: boolean;
  /** Button variant */
  variant?: "default" | "outline" | "ghost" | "link";
  /** Button size */
  size?: "default" | "sm" | "lg" | "icon";
  /** Show text label */
  showLabel?: boolean;
  /** Custom label */
  label?: string;
  /** Additional className */
  className?: string;
  /** Auto-refresh interval in ms (0 = disabled) */
  autoRefreshInterval?: number;
}

export function RefreshButton({
  onRefresh,
  isRefreshing = false,
  variant = "outline",
  size = "sm",
  showLabel = true,
  label = "Refresh",
  className,
  autoRefreshInterval = 0,
}: RefreshButtonProps) {
  return (
    <Button
      variant={variant}
      size={size}
      onClick={onRefresh}
      disabled={isRefreshing}
      className={className}
      title={showLabel ? undefined : label}
    >
      <RefreshCw className={cn("h-4 w-4", showLabel && "mr-2", isRefreshing && "animate-spin")} />
      {showLabel && label}
    </Button>
  );
}

/**
 * Auto-refresh toggle button with interval display.
 */
interface AutoRefreshToggleProps {
  /** Is auto-refresh enabled */
  enabled: boolean;
  /** Toggle handler */
  onToggle: () => void;
  /** Current interval in seconds */
  intervalSeconds?: number;
  /** Available intervals */
  intervals?: number[];
  /** Interval change handler */
  onIntervalChange?: (seconds: number) => void;
  /** Is currently refreshing */
  isRefreshing?: boolean;
  /** Manual refresh handler */
  onRefresh?: () => void;
}

export function AutoRefreshToggle({
  enabled,
  onToggle,
  intervalSeconds = 10,
  intervals = [5, 10, 30, 60],
  onIntervalChange,
  isRefreshing = false,
  onRefresh,
}: AutoRefreshToggleProps) {
  return (
    <div className="flex items-center gap-2">
      <Button
        variant={enabled ? "default" : "outline"}
        size="sm"
        onClick={onToggle}
        className="gap-2"
      >
        <RefreshCw className={cn("h-4 w-4", enabled && isRefreshing && "animate-spin")} />
        {enabled ? `${intervalSeconds}s` : "Auto"}
      </Button>
      
      {enabled && onIntervalChange && (
        <div className="flex items-center gap-1">
          {intervals.map((interval) => (
            <Button
              key={interval}
              variant={interval === intervalSeconds ? "secondary" : "ghost"}
              size="sm"
              onClick={() => onIntervalChange(interval)}
              className="h-7 px-2 text-xs"
            >
              {interval}s
            </Button>
          ))}
        </div>
      )}
      
      {onRefresh && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh now"
        >
          <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
        </Button>
      )}
    </div>
  );
}
