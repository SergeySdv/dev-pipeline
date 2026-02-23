"use client";

import type React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const opsNav = [
  { href: "/ops/queues", label: "Queues" },
  { href: "/ops/events", label: "Events" },
  { href: "/ops/logs", label: "Logs" },
  { href: "/ops/metrics", label: "Metrics" },
];

export default function OpsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="container py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Operations</h1>
        <p className="text-muted-foreground">Monitor system health, queues, and events</p>
      </div>

      <div className="mb-6 flex gap-2">
        {opsNav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
              pathname === item.href
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground"
            )}
          >
            {item.label}
          </Link>
        ))}
      </div>

      {children}
    </div>
  );
}
