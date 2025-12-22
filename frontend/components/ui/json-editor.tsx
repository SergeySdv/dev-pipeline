"use client"

import dynamic from "next/dynamic"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

type MonacoProps = {
  value: string
  onChange: (value: string) => void
  language?: string
  height?: number
  className?: string
  options?: Record<string, unknown>
}

const MonacoEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.default), {
  ssr: false,
  loading: () => (
    <div className="rounded-md border bg-muted/20 p-3 text-sm text-muted-foreground">
      Loading editor…
    </div>
  ),
})

export function JsonEditor({
  value,
  onChange,
  language = "json",
  height = 260,
  className,
  options,
}: MonacoProps) {
  return (
    <div className={cn("rounded-md border overflow-hidden", className)}>
      <MonacoEditor
        value={value}
        language={language}
        height={height}
        onChange={(next) => onChange(next ?? "")}
        options={{
          minimap: { enabled: false },
          fontSize: 12,
          tabSize: 2,
          insertSpaces: true,
          wordWrap: "on",
          scrollBeyondLastLine: false,
          automaticLayout: true,
          ...options,
        }}
        theme="vs-dark"
        loading={<Textarea value={value} onChange={(e) => onChange(e.target.value)} className="font-mono text-sm min-h-32" />}
      />
    </div>
  )
}

