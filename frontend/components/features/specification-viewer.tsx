"use client";

import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

import { FileText } from "lucide-react";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSpecificationContent } from "@/lib/api";
import { cn } from "@/lib/utils";

// =============================================================================
// Types for Property-Based Testing
// =============================================================================

/**
 * Represents the available tab keys for the specification viewer
 */
export type SpecTabKey = "spec" | "plan" | "tasks" | "checklist";

/**
 * Represents a tab configuration for the specification viewer
 */
export interface SpecTab {
  key: SpecTabKey;
  label: string;
  content: string | null;
}

/**
 * Represents the specification content data structure
 */
export interface SpecificationContentData {
  id?: number;
  path?: string;
  title?: string;
  spec_content: string | null;
  plan_content: string | null;
  tasks_content: string | null;
  checklist_content: string | null;
}

// =============================================================================
// Helper Functions (Exported for Property-Based Testing)
// =============================================================================

/**
 * Computes the tabs configuration from specification content data.
 * For any specification with multiple files, this function SHALL return
 * a tab for each available file type (spec, plan, tasks, checklist).
 *
 * @param data - The specification content data
 * @returns Array of tab configurations
 */
export function computeSpecTabs(data: SpecificationContentData | null | undefined): SpecTab[] {
  return [
    { key: "spec" as const, label: "Spec", content: data?.spec_content ?? null },
    { key: "plan" as const, label: "Plan", content: data?.plan_content ?? null },
    { key: "tasks" as const, label: "Tasks", content: data?.tasks_content ?? null },
    { key: "checklist" as const, label: "Checklist", content: data?.checklist_content ?? null },
  ];
}

/**
 * Gets the available (non-null content) tabs from a tabs array.
 *
 * @param tabs - Array of tab configurations
 * @returns Array of tabs that have content
 */
export function getAvailableTabs(tabs: SpecTab[]): SpecTab[] {
  return tabs.filter((tab) => tab.content !== null);
}

/**
 * Validates that all expected tab types are present in the tabs array.
 *
 * @param tabs - Array of tab configurations
 * @returns Object indicating which tab types are present
 */
export function validateTabsPresence(tabs: SpecTab[]): {
  hasSpecTab: boolean;
  hasPlanTab: boolean;
  hasTasksTab: boolean;
  hasChecklistTab: boolean;
  allTabTypesPresent: boolean;
} {
  const tabKeys = new Set(tabs.map((t) => t.key));
  const hasSpecTab = tabKeys.has("spec");
  const hasPlanTab = tabKeys.has("plan");
  const hasTasksTab = tabKeys.has("tasks");
  const hasChecklistTab = tabKeys.has("checklist");

  return {
    hasSpecTab,
    hasPlanTab,
    hasTasksTab,
    hasChecklistTab,
    allTabTypesPresent: hasSpecTab && hasPlanTab && hasTasksTab && hasChecklistTab,
  };
}

/**
 * Determines if a tab should be enabled (has content).
 *
 * @param tab - The tab configuration
 * @returns True if the tab has content and should be enabled
 */
export function isTabEnabled(tab: SpecTab): boolean {
  return tab.content !== null;
}

/**
 * Gets the count of available (enabled) tabs.
 *
 * @param tabs - Array of tab configurations
 * @returns Number of tabs with content
 */
export function getAvailableTabCount(tabs: SpecTab[]): number {
  return tabs.filter(isTabEnabled).length;
}

// =============================================================================
// Component
// =============================================================================

function MarkdownPanel({ content }: { content: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

export function SpecificationViewer({ specId, className }: { specId: number; className?: string }) {
  const { data, isLoading } = useSpecificationContent(specId);
  const [tab, setTab] = useState<SpecTabKey>("spec");

  const tabs = useMemo(() => computeSpecTabs(data), [data]);

  if (isLoading) return <LoadingState message="Loading specification content..." />;
  if (!data)
    {return (
      <EmptyState icon={FileText} title="No content" description="No spec content available." />
    );}

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Specification Content</CardTitle>
        <CardDescription className="font-mono text-xs">{data.path}</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={tab} onValueChange={(v) => setTab(v as SpecTabKey)} className="space-y-4">
          <TabsList>
            {tabs.map((t) => (
              <TabsTrigger key={t.key} value={t.key} disabled={!isTabEnabled(t)}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {tabs.map((t) => (
            <TabsContent key={t.key} value={t.key}>
              {t.content ? (
                <div className={cn("bg-muted/10 rounded-lg border p-4")}>
                  <MarkdownPanel content={t.content} />
                </div>
              ) : (
                <div className="text-muted-foreground py-6 text-sm">
                  No {t.label.toLowerCase()} content available yet.
                </div>
              )}
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}
