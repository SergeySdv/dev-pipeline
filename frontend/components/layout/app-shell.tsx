import type React from "react";

import { SkipToContent } from "@/components/ui/skip-to-content";

import { Breadcrumbs } from "./breadcrumbs";
import { CommandPalette } from "./command-palette";
import { Header } from "./header";
import { Sidebar } from "./sidebar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen">
      <SkipToContent />
      <Sidebar />
      <div className="flex min-h-screen flex-1 flex-col">
        <Header />
        <Breadcrumbs />
        <main id="main-content" className="bg-background flex-1" tabIndex={-1}>
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
