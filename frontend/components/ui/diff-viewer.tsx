"use client";

import { Minus,Plus } from "lucide-react";

import type { DiffHunk, DiffLine } from "@/lib/api/types";
import { cn } from "@/lib/utils";

import { Badge } from "./badge";
import { Card } from "./card";

interface DiffViewerProps {
  oldPath?: string;
  newPath?: string;
  additions: number;
  deletions: number;
  hunks: DiffHunk[];
  className?: string;
}

export function DiffViewer({
  oldPath,
  newPath,
  additions,
  deletions,
  hunks,
  className,
}: DiffViewerProps) {
  return (
    <div className={cn("space-y-4", className)}>
      {/* Diff header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          {oldPath !== newPath && oldPath && (
            <div className="text-muted-foreground text-sm line-through">{oldPath}</div>
          )}
          <div className="text-sm font-medium">{newPath || oldPath}</div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="gap-1">
            <Plus className="h-3 w-3 text-green-500" />
            <span className="text-green-500">{additions}</span>
          </Badge>
          <Badge variant="outline" className="gap-1">
            <Minus className="h-3 w-3 text-red-500" />
            <span className="text-red-500">{deletions}</span>
          </Badge>
        </div>
      </div>

      {/* Diff hunks */}
      {hunks.map((hunk, hunkIndex) => (
        <Card key={hunkIndex} className="overflow-hidden">
          {/* Hunk header */}
          <div className="bg-muted/50 text-muted-foreground border-b px-4 py-2 font-mono text-xs">
            @@ -{hunk.old_start},{hunk.old_lines} +{hunk.new_start},{hunk.new_lines} @@
          </div>

          {/* Hunk lines */}
          <div className="font-mono text-xs">
            {hunk.lines.map((line, lineIndex) => (
              <DiffLineComponent key={lineIndex} line={line} />
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}

function DiffLineComponent({ line }: { line: DiffLine }) {
  const bgColor =
    line.type === "add"
      ? "bg-green-500/10 hover:bg-green-500/20"
      : line.type === "delete"
        ? "bg-red-500/10 hover:bg-red-500/20"
        : "hover:bg-muted/50";

  const textColor =
    line.type === "add"
      ? "text-green-600 dark:text-green-400"
      : line.type === "delete"
        ? "text-red-600 dark:text-red-400"
        : "";

  const prefix = line.type === "add" ? "+" : line.type === "delete" ? "-" : " ";

  return (
    <div className={cn("flex items-start gap-4 px-4 py-1 transition-colors", bgColor, textColor)}>
      {/* Line numbers */}
      <div className="text-muted-foreground/50 flex min-w-[80px] gap-4 select-none">
        <span className="w-8 text-right">{line.old_line_number || ""}</span>
        <span className="w-8 text-right">{line.new_line_number || ""}</span>
      </div>

      {/* Line content */}
      <div className="flex-1 break-all whitespace-pre-wrap">
        <span className="mr-2 select-none">{prefix}</span>
        {line.content}
      </div>
    </div>
  );
}
