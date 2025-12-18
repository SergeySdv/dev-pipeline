"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import { FolderKanban, PlayCircle, Activity, Shield, Settings, Search } from "lucide-react"

const quickActions = [
  { icon: FolderKanban, label: "Projects", href: "/projects" },
  { icon: PlayCircle, label: "Runs", href: "/runs" },
  { icon: Activity, label: "Operations", href: "/ops" },
  { icon: Shield, label: "Policy Packs", href: "/policy-packs" },
  { icon: Settings, label: "Settings", href: "/settings" },
]

const recentProjects = [
  { id: "1", name: "E-commerce Web App", href: "/projects/1" },
  { id: "2", name: "API Gateway Service", href: "/projects/2" },
  { id: "3", name: "Mobile App Backend", href: "/projects/3" },
  { id: "4", name: "Analytics Pipeline", href: "/projects/4" },
]

export function CommandPalette() {
  const router = useRouter()
  const [open, setOpen] = useState(false)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault()
      setOpen((open) => !open)
    }
  }, [])

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [handleKeyDown])

  const runCommand = useCallback((command: () => void) => {
    setOpen(false)
    command()
  }, [])

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Quick Actions">
          {quickActions.map((action) => (
            <CommandItem key={action.href} onSelect={() => runCommand(() => router.push(action.href))}>
              <action.icon className="mr-2 h-4 w-4" />
              <span>{action.label}</span>
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Recent Projects">
          {recentProjects.map((project) => (
            <CommandItem key={project.id} onSelect={() => runCommand(() => router.push(project.href))}>
              <FolderKanban className="mr-2 h-4 w-4" />
              <span>{project.name}</span>
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Actions">
          <CommandItem onSelect={() => runCommand(() => router.push("/projects"))}>
            <Search className="mr-2 h-4 w-4" />
            <span>Search Projects...</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => router.push("/runs"))}>
            <Search className="mr-2 h-4 w-4" />
            <span>Search Runs...</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
