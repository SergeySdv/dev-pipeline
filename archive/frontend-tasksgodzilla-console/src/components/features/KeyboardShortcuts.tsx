import * as React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useNavigate } from '@tanstack/react-router';
import { Command, Search, X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { ScrollArea } from '@/components/ui/ScrollArea';

interface Shortcut {
    keys: string[];
    description: string;
    action?: () => void;
    href?: string;
}

const globalShortcuts: Shortcut[] = [
    { keys: ['⌘', 'K'], description: 'Open command palette' },
    { keys: ['⌘', '/'], description: 'Show keyboard shortcuts' },
    { keys: ['⌘', 'B'], description: 'Toggle sidebar' },
    { keys: ['Esc'], description: 'Close modal / Go back' },
];

const navigationShortcuts: Shortcut[] = [
    { keys: ['G', 'D'], description: 'Go to Dashboard', href: '/dashboard' },
    { keys: ['G', 'P'], description: 'Go to Projects', href: '/projects' },
    { keys: ['G', 'R'], description: 'Go to Runs', href: '/runs' },
    { keys: ['G', 'S'], description: 'Go to Settings', href: '/settings' },
    { keys: ['G', 'O'], description: 'Go to Operations', href: '/ops/queues' },
];

const actionShortcuts: Shortcut[] = [
    { keys: ['N', 'P'], description: 'New Project' },
    { keys: ['N', 'R'], description: 'New Protocol Run' },
    { keys: ['⌘', 'S'], description: 'Save current form' },
    { keys: ['⌘', 'Enter'], description: 'Submit / Confirm' },
];

interface KeyboardShortcutsProps {
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
}

export function KeyboardShortcuts({ open, onOpenChange }: KeyboardShortcutsProps) {
    const navigate = useNavigate();
    const [search, setSearch] = React.useState('');
    const [isOpen, setIsOpen] = React.useState(false);

    const controlledOpen = open ?? isOpen;
    const setControlledOpen = onOpenChange ?? setIsOpen;

    // Listen for keyboard shortcut to open
    React.useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === '/') {
                e.preventDefault();
                setControlledOpen(true);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [setControlledOpen]);

    const allShortcuts = [
        { title: 'Global', shortcuts: globalShortcuts },
        { title: 'Navigation', shortcuts: navigationShortcuts },
        { title: 'Actions', shortcuts: actionShortcuts },
    ];

    const filteredGroups = allShortcuts.map((group) => ({
        ...group,
        shortcuts: group.shortcuts.filter(
            (s) =>
                s.description.toLowerCase().includes(search.toLowerCase()) ||
                s.keys.join('').toLowerCase().includes(search.toLowerCase())
        ),
    })).filter((g) => g.shortcuts.length > 0);

    const handleShortcutClick = (shortcut: Shortcut) => {
        if (shortcut.href) {
            navigate({ to: shortcut.href });
            setControlledOpen(false);
        } else if (shortcut.action) {
            shortcut.action();
            setControlledOpen(false);
        }
    };

    return (
        <Dialog.Root open={controlledOpen} onOpenChange={setControlledOpen}>
            <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
                <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-background border border-border rounded-lg shadow-xl z-50">
                    <div className="flex items-center justify-between p-4 border-b border-border">
                        <Dialog.Title className="flex items-center gap-2 font-semibold">
                            <Command className="h-5 w-5" />
                            Keyboard Shortcuts
                        </Dialog.Title>
                        <Dialog.Close asChild>
                            <Button variant="ghost" size="icon">
                                <X className="h-4 w-4" />
                            </Button>
                        </Dialog.Close>
                    </div>

                    <div className="p-4 border-b border-border">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search shortcuts..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="pl-10"
                            />
                        </div>
                    </div>

                    <ScrollArea className="h-[400px]">
                        <div className="p-4 space-y-6">
                            {filteredGroups.map((group) => (
                                <div key={group.title}>
                                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                                        {group.title}
                                    </h3>
                                    <div className="space-y-2">
                                        {group.shortcuts.map((shortcut, idx) => (
                                            <button
                                                key={idx}
                                                onClick={() => handleShortcutClick(shortcut)}
                                                className={cn(
                                                    'w-full flex items-center justify-between p-2 rounded-md text-sm',
                                                    'hover:bg-muted transition-colors',
                                                    (shortcut.href || shortcut.action) && 'cursor-pointer'
                                                )}
                                            >
                                                <span className="text-foreground">{shortcut.description}</span>
                                                <div className="flex gap-1">
                                                    {shortcut.keys.map((key, keyIdx) => (
                                                        <kbd
                                                            key={keyIdx}
                                                            className="px-2 py-1 text-xs font-mono bg-muted border border-border rounded"
                                                        >
                                                            {key}
                                                        </kbd>
                                                    ))}
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ))}
                            {filteredGroups.length === 0 && (
                                <div className="text-center text-muted-foreground py-8">
                                    No shortcuts match your search
                                </div>
                            )}
                        </div>
                    </ScrollArea>
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    );
}
