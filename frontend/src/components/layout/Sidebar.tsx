import { useState } from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import {
    LayoutDashboard,
    FolderKanban,
    PlayCircle,
    Activity,
    Shield,
    Settings,
    ChevronDown,
    ChevronRight,
    Layers,
    ListChecks,
    BarChart3,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { Button } from '@/components/ui/Button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/Collapsible';
import { ScrollArea } from '@/components/ui/ScrollArea';
import { Separator } from '@/components/ui/Separator';

type NavItem = {
    name: string;
    href: string;
    icon: React.ComponentType<{ className?: string }>;
    children?: { name: string; href: string }[];
};

const navigation: NavItem[] = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Projects', href: '/projects', icon: FolderKanban },
    { name: 'Runs', href: '/runs', icon: PlayCircle },
    {
        name: 'Operations',
        href: '/ops',
        icon: Activity,
        children: [
            { name: 'Queues', href: '/ops/queues' },
            { name: 'Events', href: '/ops/events' },
            { name: 'Metrics', href: '/ops/metrics' },
        ],
    },
    { name: 'Protocols', href: '/protocols', icon: Layers },
    { name: 'Steps', href: '/steps', icon: ListChecks },
    { name: 'Policy Packs', href: '/policy-packs', icon: Shield },
    { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
    const location = useLocation();
    const pathname = location.pathname;
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [expandedSections, setExpandedSections] = useState<string[]>(['Operations']);

    const toggleSection = (name: string) => {
        setExpandedSections((prev) =>
            prev.includes(name) ? prev.filter((s) => s !== name) : [...prev, name]
        );
    };

    const isActive = (href: string) => {
        if (href === '/ops') return pathname.startsWith('/ops/');
        return pathname === href || pathname.startsWith(href + '/');
    };

    return (
        <aside
            className={cn(
                'sticky top-0 h-screen border-r border-sidebar-border bg-sidebar transition-all duration-300 hidden md:flex flex-col',
                isCollapsed ? 'w-16' : 'w-64'
            )}
        >
            {/* Logo */}
            <div className="flex h-16 items-center border-b border-sidebar-border px-4">
                <Link to="/dashboard" className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sidebar-primary">
                        <Layers className="h-5 w-5 text-sidebar-primary-foreground" />
                    </div>
                    {!isCollapsed && (
                        <span className="font-semibold text-sidebar-foreground">TasksGodzilla</span>
                    )}
                </Link>
            </div>

            <ScrollArea className="flex-1 px-3 py-4">
                <nav className="space-y-1">
                    {navigation.map((item) => {
                        const active = isActive(item.href);
                        const hasChildren = item.children && item.children.length > 0;
                        const isExpanded = expandedSections.includes(item.name);
                        const Icon = item.icon;

                        if (hasChildren) {
                            return (
                                <Collapsible
                                    key={item.name}
                                    open={isExpanded}
                                    onOpenChange={() => toggleSection(item.name)}
                                >
                                    <CollapsibleTrigger asChild>
                                        <Button
                                            variant="ghost"
                                            className={cn(
                                                'w-full justify-start gap-3 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                                                active && 'bg-sidebar-accent text-sidebar-accent-foreground'
                                            )}
                                        >
                                            <Icon className="h-5 w-5 shrink-0" />
                                            {!isCollapsed && (
                                                <>
                                                    <span className="flex-1 text-left">{item.name}</span>
                                                    {isExpanded ? (
                                                        <ChevronDown className="h-4 w-4" />
                                                    ) : (
                                                        <ChevronRight className="h-4 w-4" />
                                                    )}
                                                </>
                                            )}
                                        </Button>
                                    </CollapsibleTrigger>
                                    {!isCollapsed && (
                                        <CollapsibleContent className="ml-8 mt-1 space-y-1">
                                            {item.children!.map((child) => {
                                                const childActive = isActive(child.href);
                                                return (
                                                    <Link key={child.href} to={child.href}>
                                                        <Button
                                                            variant="ghost"
                                                            className={cn(
                                                                'w-full justify-start text-sm text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                                                                childActive && 'bg-sidebar-accent text-sidebar-accent-foreground'
                                                            )}
                                                        >
                                                            {child.name}
                                                        </Button>
                                                    </Link>
                                                );
                                            })}
                                        </CollapsibleContent>
                                    )}
                                </Collapsible>
                            );
                        }

                        return (
                            <Link key={item.name} to={item.href}>
                                <Button
                                    variant="ghost"
                                    className={cn(
                                        'w-full justify-start gap-3 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                                        active && 'bg-sidebar-accent text-sidebar-accent-foreground'
                                    )}
                                >
                                    <Icon className="h-5 w-5 shrink-0" />
                                    {!isCollapsed && <span>{item.name}</span>}
                                </Button>
                            </Link>
                        );
                    })}
                </nav>
            </ScrollArea>

            {/* Collapse Toggle */}
            <Separator />
            <div className="p-3">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="w-full justify-center"
                >
                    {isCollapsed ? (
                        <ChevronRight className="h-4 w-4" />
                    ) : (
                        <ChevronRight className="h-4 w-4 rotate-180" />
                    )}
                </Button>
            </div>
        </aside>
    );
}
