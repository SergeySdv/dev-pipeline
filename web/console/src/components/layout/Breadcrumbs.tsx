import { Link, useLocation } from '@tanstack/react-router';
import { ChevronRight, Home } from 'lucide-react';
import React from 'react';

function breadcrumbsFor(pathname: string): Array<{ label: string; to?: string }> {
    const parts = pathname.split('/').filter(Boolean);
    if (parts.length === 0) return [{ label: 'Home', to: '/dashboard' }];

    const crumbs: Array<{ label: string; to?: string }> = [{ label: 'Home', to: '/dashboard' }];
    let accum = '';

    for (let i = 0; i < parts.length; i += 1) {
        const p = parts[i]!;
        accum += `/${p}`;
        const label = p.charAt(0).toUpperCase() + p.slice(1).replace(/-/g, ' ');
        crumbs.push({ label, to: accum });
    }

    // Avoid linking the last breadcrumb to itself
    if (crumbs.length > 0) {
        crumbs[crumbs.length - 1] = { label: crumbs[crumbs.length - 1]!.label };
    }

    return crumbs;
}

export function Breadcrumbs() {
    const location = useLocation();
    const crumbs = breadcrumbsFor(location.pathname);

    return (
        <div className="border-b border-border bg-background px-6 py-2">
            <nav className="flex items-center gap-1 text-sm">
                {crumbs.map((c, idx) => (
                    <React.Fragment key={`${c.label}-${idx}`}>
                        {idx === 0 && <Home className="h-3.5 w-3.5 text-muted-foreground mr-1" />}
                        {idx > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                        {c.to ? (
                            <Link
                                to={c.to}
                                className="text-muted-foreground hover:text-foreground transition-colors"
                            >
                                {c.label}
                            </Link>
                        ) : (
                            <span className="text-foreground font-medium">{c.label}</span>
                        )}
                    </React.Fragment>
                ))}
            </nav>
        </div>
    );
}
