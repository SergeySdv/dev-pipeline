"use client";

import { Command } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";

interface KeyboardShortcutsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const shortcuts = [
  {
    category: "Navigation",
    items: [
      { keys: ["⌘", "K"], description: "Open command palette" },
      { keys: ["G", "P"], description: "Go to Projects" },
      { keys: ["G", "R"], description: "Go to Runs" },
      { keys: ["G", "O"], description: "Go to Operations" },
      { keys: ["G", "S"], description: "Go to Settings" },
    ],
  },
  {
    category: "Actions",
    items: [
      { keys: ["C"], description: "Create new project" },
      { keys: ["N"], description: "Create new protocol" },
      { keys: ["/"], description: "Focus search" },
      { keys: ["?"], description: "Show keyboard shortcuts" },
    ],
  },
  {
    category: "General",
    items: [
      { keys: ["Esc"], description: "Close dialog or modal" },
      { keys: ["⌘", "Enter"], description: "Submit form" },
      { keys: ["Tab"], description: "Navigate between fields" },
    ],
  },
];

export function KeyboardShortcuts({ open, onOpenChange }: KeyboardShortcutsProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Command className="h-5 w-5" />
            Keyboard Shortcuts
          </DialogTitle>
          <DialogDescription>Quick reference for navigating DevGodzilla Console</DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {shortcuts.map((section) => (
            <div key={section.category}>
              <h3 className="mb-3 text-sm font-semibold">{section.category}</h3>
              <div className="space-y-2">
                {section.items.map((item, index) => (
                  <div key={index} className="flex items-center justify-between py-2 text-sm">
                    <span className="text-muted-foreground">{item.description}</span>
                    <div className="flex gap-1">
                      {item.keys.map((key, keyIndex) => (
                        <kbd
                          key={keyIndex}
                          className="bg-muted text-muted-foreground pointer-events-none inline-flex h-6 items-center gap-1 rounded border px-2 font-mono text-xs font-medium select-none"
                        >
                          {key}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              {section.category !== shortcuts[shortcuts.length - 1].category && (
                <Separator className="mt-4" />
              )}
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
