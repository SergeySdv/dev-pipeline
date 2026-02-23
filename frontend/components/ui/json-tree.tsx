"use client";

import { useMemo, useState } from "react";

import { ChevronRight } from "lucide-react";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

function isObject(value: JsonValue): value is Record<string, JsonValue> {
  return typeof value === "object" && value != null && !Array.isArray(value);
}

function renderScalar(value: JsonValue) {
  if (value === null) return <span className="text-muted-foreground">null</span>;
  if (typeof value === "string")
    {return <span className="text-emerald-700 dark:text-emerald-400">"{value}"</span>;}
  if (typeof value === "number")
    {return <span className="text-blue-700 dark:text-blue-400">{value}</span>;}
  if (typeof value === "boolean")
    {return <span className="text-purple-700 dark:text-purple-400">{String(value)}</span>;}
  return <span className="text-muted-foreground">…</span>;
}

function JsonNode({ name, value, depth }: { name: string; value: JsonValue; depth: number }) {
  const [open, setOpen] = useState(depth < 2);

  const isComposite = Array.isArray(value) || isObject(value);
  if (!isComposite) {
    return (
      <div className="flex items-start gap-2">
        <span className="text-muted-foreground font-mono text-xs">{name}:</span>
        <span className="font-mono text-xs">{renderScalar(value)}</span>
      </div>
    );
  }

  const entries: Array<[string, JsonValue]> = Array.isArray(value)
    ? value.map((v, i) => [String(i), v])
    : Object.entries(value);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div className="flex items-center gap-1">
        <CollapsibleTrigger className="flex items-center gap-1 text-left">
          <ChevronRight
            className={cn(
              "text-muted-foreground h-3.5 w-3.5 transition-transform",
              open && "rotate-90"
            )}
          />
          <span className="text-muted-foreground font-mono text-xs">{name}</span>
        </CollapsibleTrigger>
        <span className="text-muted-foreground text-xs">
          {Array.isArray(value) ? `[${value.length}]` : `{${entries.length}}`}
        </span>
      </div>
      <CollapsibleContent className="mt-2 space-y-2 border-l pl-4">
        {entries.length === 0 ? (
          <div className="text-muted-foreground text-xs">Empty</div>
        ) : (
          entries.map(([k, v]) => <JsonNode key={k} name={k} value={v} depth={depth + 1} />)
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}

export function JsonTree({
  value,
  className,
  rootName = "overrides",
}: {
  value: unknown;
  className?: string;
  rootName?: string;
}) {
  const normalized = useMemo<JsonValue>(() => {
    if (value === undefined) return null;
    return value as JsonValue;
  }, [value]);

  return (
    <div className={cn("bg-muted/20 rounded-lg border p-3", className)}>
      <JsonNode name={rootName} value={normalized} depth={0} />
    </div>
  );
}
