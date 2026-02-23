"use client";

import { RefreshCw, Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterConfig {
  key: string;
  label: string;
  options: FilterOption[];
  placeholder?: string;
}

interface ListToolbarProps {
  /** Search query value */
  searchValue?: string;
  /** Search change handler */
  onSearchChange?: (value: string) => void;
  /** Search placeholder text */
  searchPlaceholder?: string;
  /** Filter configurations */
  filters?: FilterConfig[];
  /** Current filter values */
  filterValues?: Record<string, string>;
  /** Filter change handler */
  onFilterChange?: (key: string, value: string) => void;
  /** Refresh handler */
  onRefresh?: () => void;
  /** Is refreshing */
  isRefreshing?: boolean;
  /** Additional actions to render on the right side */
  actions?: React.ReactNode;
  /** Show search input */
  showSearch?: boolean;
  /** Container className */
  className?: string;
}

export function ListToolbar({
  searchValue = "",
  onSearchChange,
  searchPlaceholder = "Search...",
  filters = [],
  filterValues = {},
  onFilterChange,
  onRefresh,
  isRefreshing = false,
  actions,
  showSearch = true,
  className,
}: ListToolbarProps) {
  const hasActiveFilters = Object.values(filterValues).some((v) => v && v !== "all");
  const hasSearch = searchValue.length > 0;

  const clearAllFilters = () => {
    onSearchChange?.("");
    filters.forEach((f) => onFilterChange?.(f.key, "all"));
  };

  return (
    <div className={cn("flex flex-col gap-4 py-4 sm:flex-row sm:items-center sm:justify-between", className)}>
      <div className="flex flex-1 flex-wrap items-center gap-2">
        {/* Search Input */}
        {showSearch && (
          <div className="relative min-w-[200px] flex-1 sm:max-w-xs">
            <Search className="text-muted-foreground pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2" />
            <Input
              placeholder={searchPlaceholder}
              value={searchValue}
              onChange={(e) => onSearchChange?.(e.target.value)}
              className="pl-8 pr-8"
            />
            {hasSearch && (
              <button
                onClick={() => onSearchChange?.("")}
                className="text-muted-foreground hover:text-foreground absolute right-2 top-1/2 -translate-y-1/2"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        )}

        {/* Filters */}
        {filters.map((filter) => (
          <Select
            key={filter.key}
            value={filterValues[filter.key] || "all"}
            onValueChange={(value) => onFilterChange?.(filter.key, value)}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder={filter.placeholder || filter.label} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All {filter.label}</SelectItem>
              {filter.options.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ))}

        {/* Clear Filters Button */}
        {(hasActiveFilters || hasSearch) && (
          <Button variant="ghost" size="sm" onClick={clearAllFilters}>
            <X className="mr-1 h-3 w-3" />
            Clear
          </Button>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Refresh Button */}
        {onRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={cn("mr-2 h-4 w-4", isRefreshing && "animate-spin")} />
            Refresh
          </Button>
        )}

        {/* Additional Actions */}
        {actions}
      </div>
    </div>
  );
}

/**
 * Pre-configured filter options for common entities.
 */
export const commonFilters = {
  status: {
    key: "status",
    label: "Status",
    options: [
      { value: "pending", label: "Pending" },
      { value: "running", label: "Running" },
      { value: "completed", label: "Completed" },
      { value: "failed", label: "Failed" },
      { value: "paused", label: "Paused" },
      { value: "cancelled", label: "Cancelled" },
    ],
  },
  protocolStatus: {
    key: "status",
    label: "Status",
    options: [
      { value: "pending", label: "Pending" },
      { value: "planning", label: "Planning" },
      { value: "planned", label: "Planned" },
      { value: "running", label: "Running" },
      { value: "paused", label: "Paused" },
      { value: "blocked", label: "Blocked" },
      { value: "completed", label: "Completed" },
      { value: "failed", label: "Failed" },
      { value: "cancelled", label: "Cancelled" },
    ],
  },
  runStatus: {
    key: "status",
    label: "Status",
    options: [
      { value: "queued", label: "Queued" },
      { value: "running", label: "Running" },
      { value: "succeeded", label: "Succeeded" },
      { value: "failed", label: "Failed" },
      { value: "cancelled", label: "Cancelled" },
    ],
  },
  jobType: {
    key: "job_type",
    label: "Job Type",
    placeholder: "Type",
    options: [
      { value: "codex", label: "Codex" },
      { value: "planning", label: "Planning" },
      { value: "qa", label: "QA" },
      { value: "discovery", label: "Discovery" },
    ],
  },
};
