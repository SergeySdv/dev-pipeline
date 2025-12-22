"use client"

import { useMemo, useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import rehypeHighlight from "rehype-highlight"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { FileText } from "lucide-react"
import { cn } from "@/lib/utils"
import { useSpecificationContent } from "@/lib/api"

function MarkdownPanel({ content }: { content: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

export function SpecificationViewer({
  specId,
  className,
}: {
  specId: number
  className?: string
}) {
  const { data, isLoading } = useSpecificationContent(specId)
  const [tab, setTab] = useState<"spec" | "plan" | "tasks" | "checklist">("spec")

  const tabs = useMemo(() => {
    return [
      { key: "spec" as const, label: "Spec", content: data?.spec_content ?? null },
      { key: "plan" as const, label: "Plan", content: data?.plan_content ?? null },
      { key: "tasks" as const, label: "Tasks", content: data?.tasks_content ?? null },
      { key: "checklist" as const, label: "Checklist", content: data?.checklist_content ?? null },
    ]
  }, [data])

  if (isLoading) return <LoadingState message="Loading specification content..." />
  if (!data) return <EmptyState icon={FileText} title="No content" description="No spec content available." />

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Specification Content</CardTitle>
        <CardDescription className="font-mono text-xs">{data.path}</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)} className="space-y-4">
          <TabsList>
            {tabs.map((t) => (
              <TabsTrigger key={t.key} value={t.key} disabled={!t.content}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {tabs.map((t) => (
            <TabsContent key={t.key} value={t.key}>
              {t.content ? (
                <div className={cn("rounded-lg border bg-muted/10 p-4")}>
                  <MarkdownPanel content={t.content} />
                </div>
              ) : (
                <div className="text-sm text-muted-foreground py-6">
                  No {t.label.toLowerCase()} content available yet.
                </div>
              )}
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  )
}

