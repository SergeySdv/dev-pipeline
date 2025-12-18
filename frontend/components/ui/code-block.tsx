"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Check, Copy } from "lucide-react"

interface CodeBlockProps {
  code: string | Record<string, unknown>
  language?: string
  title?: string
  className?: string
  maxHeight?: string
}

export function CodeBlock({ code, language = "json", title, className, maxHeight = "400px" }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const codeString = typeof code === "string" ? code : JSON.stringify(code, null, 2)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(codeString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn("rounded-lg border bg-muted/50", className)}>
      {title && (
        <div className="flex items-center justify-between border-b px-4 py-2">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <Button variant="ghost" size="sm" onClick={handleCopy}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
      )}
      <pre className={cn("overflow-auto p-4 text-sm", !title && "relative")} style={{ maxHeight }}>
        {!title && (
          <Button variant="ghost" size="sm" className="absolute right-2 top-2" onClick={handleCopy}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        )}
        <code className={`language-${language} text-foreground`}>{codeString}</code>
      </pre>
    </div>
  )
}
