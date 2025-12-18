import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Command } from 'cmdk';
import { useQuery } from '@tanstack/react-query';
import {
    LayoutDashboard,
    FolderKanban,
    PlayCircle,
    Activity,
    Shield,
    Settings,
    Layers,
    ListChecks,
    Search,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { apiFetchJson } from '@/api/client';

type Project = { id: number; name: string };
type Protocol = { id: number; name: string };

export function CommandPalette() {
    const [open, setOpen] = useState(false);
    const navigate = useNavigate();

    // Fetch projects and protocols for search
    const { data: projects } = useQuery({
        queryKey: ['projects'],
        queryFn: () => apiFetchJson<Project[]>('/projects'),
        enabled: open,
    });

    const { data: protocols } = useQuery({
        queryKey: ['protocols'],
        queryFn: () => apiFetchJson<Protocol[]>('/protocols'),
        enabled: open,
    });

    // Handle keyboard shortcut
    useEffect(() => {
        const down = (e: KeyboardEvent) => {
            if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                setOpen((o) => !o);
            }
        };

        document.addEventListener('keydown', down);
        return () => document.removeEventListener('keydown', down);
    }, []);

    const runCommand = useCallback(
        (command: () => void) => {
            setOpen(false);
            command();
        },
        []
    );

    return (
        <Command.Dialog
            open={open}
            onOpenChange={setOpen}
            className="fixed inset-0 z-50 bg-black/50"
            label="Global Command Menu"
        >
            <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg">
                <div className="overflow-hidden rounded-lg border bg-popover shadow-lg">
                    <div className="flex items-center border-b px-3">
                        <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                        <Command.Input
                            placeholder="Type a command or search..."
                            className="flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                        />
                    </div>
                    <Command.List className="max-h-[300px] overflow-y-auto overflow-x-hidden p-2">
                        <Command.Empty className="py-6 text-center text-sm">No results found.</Command.Empty>

                        <Command.Group heading="Navigation" className="text-xs font-medium text-muted-foreground px-2 py-1.5">
                            <Command.Item
                                className={cn(
                                    'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
                                    'aria-selected:bg-accent aria-selected:text-accent-foreground'
                                )}
                                onSelect={() => runCommand(() => navigate({ to: '/dashboard' }))}
                            >
                                <LayoutDashboard className="mr-2 h-4 w-4" />
                                Dashboard
                            </Command.Item>
                            <Command.Item
                                className={cn(
                                    'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
                                    'aria-selected:bg-accent aria-selected:text-accent-foreground'
                                )}
                                onSelect={() => runCommand(() => navigate({ to: '/projects' }))}
                            >
                                <FolderKanban className="mr-2 h-4 w-4" />
                                Projects
                            </Command.Item>
                            <Command.Item
                                className={cn(
                                    'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
                                    'aria-selected:bg-accent aria-selected:text-accent-foreground'
                                )}
                                onSelect={() => runCommand(() => navigate({ to: '/runs' }))}
                            >
                                <PlayCircle className="mr-2 h-4 w-4" />
                                Runs
                            </Command.Item>
                            <Command.Item
                                className={cn(
                                    'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
                                    'aria-selected:bg-accent aria-selected:text-accent-foreground'
                                )}
                                onSelect={() => runCommand(() => navigate({ to: '/protocols' }))}
                            >
                                <Layers className="mr-2 h-4 w-4" />
                                Protocols
                            </Command.Item>
                            <Command.Item
                                className={cn(
                                    'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
                                    'aria-selected:bg-accent aria-selected:text-accent-foreground'
                                )}
                                onSelect={() => runCommand(() => navigate({ to: '/steps' }))}
                            >
                                <ListChecks className="mr-2 h-4 w-4" />
                                Steps
                            </Command.Item>
                            <Command.Item
                                className={cn(
                                    'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
                                    'aria-selected:bg-accent aria-selected:text-accent-foreground'
                                )}
                                onSelect={() => runCommand(() => navigate({ to: '/ops/queues' }))}
                            >
                                <Activity className="mr-2 h-4 w-4" />
                                Operations
                            </Command.Item>
                            <Command.Item
                                className={cn(
                                    'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
                                    'aria-selected:bg-accent aria-selected:text-accent-foreground'
                                )}
                                onSelect={() => runCommand(() => navigate({ to: '/policy-packs' }))}
                            >
                                <Shield className="mr-2 h-4 w-4" />
                                Policy Packs
                            </Command.Item>
                            <Command.Item
                                className={cn(
                                    'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
                                    'aria-selected:bg-accent aria-selected:text-accent-foreground'
                                )}
                                onSelect={() => runCommand(() => navigate({ to: '/settings' }))}
                            >
                                <Settings className="mr-2 h-4 w-4" />
                                Settings
                            </Command.Item>
                        </Command.Group>

                        {projects && projects.length > 0 && (
                            <Command.Group heading="Projects" className="text-xs font-medium text-muted-foreground px-2 py-1.5 mt-2">
                                {projects.slice(0, 5).map((project) => (
                                    <Command.Item
                                        key={project.id}
                                        className={cn(
                                            'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
                                            'aria-selected:bg-accent aria-selected:text-accent-foreground'
                                        )}
                                        onSelect={() =>
                                            runCommand(() => navigate({ to: '/projects/$projectId', params: { projectId: String(project.id) } }))
                                        }
                                    >
                                        <FolderKanban className="mr-2 h-4 w-4" />
                                        {project.name}
                                    </Command.Item>
                                ))}
                            </Command.Group>
                        )}

                        {protocols && protocols.length > 0 && (
                            <Command.Group heading="Protocols" className="text-xs font-medium text-muted-foreground px-2 py-1.5 mt-2">
                                {protocols.slice(0, 5).map((protocol) => (
                                    <Command.Item
                                        key={protocol.id}
                                        className={cn(
                                            'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
                                            'aria-selected:bg-accent aria-selected:text-accent-foreground'
                                        )}
                                        onSelect={() =>
                                            runCommand(() => navigate({ to: '/protocols/$protocolId', params: { protocolId: String(protocol.id) } }))
                                        }
                                    >
                                        <Layers className="mr-2 h-4 w-4" />
                                        {protocol.name}
                                    </Command.Item>
                                ))}
                            </Command.Group>
                        )}
                    </Command.List>
                </div>
            </div>
        </Command.Dialog>
    );
}
