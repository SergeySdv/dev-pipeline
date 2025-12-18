import type React from "react"
import { Header } from "./header"
import { Sidebar } from "./sidebar"
import { Breadcrumbs } from "./breadcrumbs"
import { CommandPalette } from "./command-palette"
import { SkipToContent } from "@/components/ui/skip-to-content"

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen">
      <SkipToContent />
      <Sidebar />
      <div className="flex min-h-screen flex-1 flex-col">
        <Header />
        <Breadcrumbs />
        <main id="main-content" className="flex-1 bg-background" tabIndex={-1}>
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  )
}
