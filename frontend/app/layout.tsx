import type React from "react"
import type { Metadata, Viewport } from "next"

import { Providers } from "@/components/providers"
import { AppShell } from "@/components/layout/app-shell"
import { TooltipProvider } from "@/components/ui/tooltip"
import "./globals.css"

export const metadata: Metadata = {
  title: "DevGodzilla Console",
  description: "AI-powered protocol-driven development control plane",
  generator: "v0.app",
}

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "white" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <Providers>
          <TooltipProvider delayDuration={200} skipDelayDuration={200}>
            <AppShell>{children}</AppShell>
          </TooltipProvider>
        </Providers>
      </body>
    </html>
  )
}
