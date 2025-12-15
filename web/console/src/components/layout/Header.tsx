import { Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Bell, HelpCircle, Search, Menu, User } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu';
import { cn } from '@/lib/cn';

interface HeaderProps {
    onMobileMenuToggle?: () => void;
    mobileMenuOpen?: boolean;
}

export function Header({ onMobileMenuToggle, mobileMenuOpen }: HeaderProps) {
    const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';

    const { data: health, isError } = useQuery({
        queryKey: ['health'],
        queryFn: async () => {
            const resp = await fetch(`${apiBase}/health`);
            if (!resp.ok) throw new Error('Health check failed');
            return (await resp.json()) as { status: string };
        },
        staleTime: 10_000,
        retry: 1,
    });

    const { data: authStatus } = useQuery({
        queryKey: ['auth', 'status'],
        queryFn: async () => {
            const resp = await fetch(`${apiBase}/auth/status`, { credentials: 'include' });
            if (!resp.ok) return { mode: 'open', authenticated: false, user: null } as const;
            return (await resp.json()) as { mode: string; authenticated: boolean; user: any };
        },
        staleTime: 10_000,
        retry: 0,
    });

    const authMode = authStatus?.mode ?? 'open';
    const authed = Boolean(authStatus?.authenticated);
    const me = (authStatus?.user ?? null) as { name?: string; email?: string; username?: string } | null;

    const handleCommandPalette = () => {
        const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
        document.dispatchEvent(event);
    };

    return (
        <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex h-14 items-center justify-between px-4 md:px-6">
                <div className="flex items-center gap-4">
                    {/* Mobile menu button */}
                    <Button
                        variant="ghost"
                        size="sm"
                        className="md:hidden"
                        onClick={onMobileMenuToggle}
                    >
                        <Menu className="h-5 w-5" />
                    </Button>

                    {/* Status indicator */}
                    <div className="hidden sm:flex items-center gap-2 rounded-md border border-border bg-muted/50 px-2 py-1">
                        <div
                            className={cn(
                                'h-2 w-2 rounded-full',
                                health?.status === 'ok'
                                    ? 'bg-green-500 animate-pulse'
                                    : isError
                                        ? 'bg-red-500'
                                        : 'bg-yellow-500'
                            )}
                        />
                        <span className="text-xs text-muted-foreground">
                            {health?.status === 'ok' ? 'Connected' : isError ? 'Offline' : 'Connecting...'}
                        </span>
                    </div>

                    <Badge variant="outline" className="text-xs hidden sm:inline-flex">
                        {import.meta.env.MODE === 'production' ? 'Production' : 'Development'}
                    </Badge>
                </div>

                <div className="flex items-center gap-2">
                    {/* Search button */}
                    <Button
                        variant="outline"
                        className="h-8 gap-2 px-3 text-xs text-muted-foreground bg-transparent hidden md:flex"
                        onClick={handleCommandPalette}
                    >
                        <Search className="h-3 w-3" />
                        <span>Search</span>
                        <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
                            <span className="text-xs">⌘</span>K
                        </kbd>
                    </Button>

                    {/* Notifications */}
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 relative">
                                <Bell className="h-4 w-4" />
                                <span className="sr-only">Notifications</span>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-80">
                            <DropdownMenuLabel>Notifications</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem>
                                <div className="flex flex-col gap-1">
                                    <p className="text-sm font-medium">No new notifications</p>
                                    <p className="text-xs text-muted-foreground">Check back later for updates</p>
                                </div>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>

                    {/* Help */}
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                                <HelpCircle className="h-4 w-4" />
                                <span className="sr-only">Help</span>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Help & Resources</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem>Documentation</DropdownMenuItem>
                            <DropdownMenuItem>API Reference</DropdownMenuItem>
                            <DropdownMenuItem>Keyboard Shortcuts</DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem>Contact Support</DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>

                    <div className="h-6 w-px bg-border hidden md:block" />

                    {/* User menu */}
                    {authed && me ? (
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" className="h-8 gap-2 px-2">
                                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                                        {(me.name || me.email || me.username || 'U').charAt(0).toUpperCase()}
                                    </div>
                                    <span className="text-sm hidden md:inline">{me.name || me.email || me.username || 'User'}</span>
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuLabel>
                                    <div className="flex flex-col gap-1">
                                        <p className="text-sm font-medium">{me.name || 'User'}</p>
                                        <p className="text-xs text-muted-foreground">{me.email}</p>
                                    </div>
                                </DropdownMenuLabel>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem asChild>
                                    <Link to="/settings">Settings</Link>
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem className="text-destructive">Sign out</DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    ) : authMode === 'oidc' ? (
                        <a
                            className="rounded-md border border-border bg-muted px-3 py-2 text-xs text-foreground hover:bg-accent"
                            href={`${apiBase}/auth/login?next=${encodeURIComponent(
                                typeof window !== 'undefined' ? window.location.pathname + window.location.search : '/console'
                            )}`}
                        >
                            Sign in
                        </a>
                    ) : authMode === 'jwt' ? (
                        <Link
                            className="rounded-md border border-border bg-muted px-3 py-2 text-xs text-foreground hover:bg-accent"
                            to="/login"
                            search={{ next: typeof window !== 'undefined' ? window.location.pathname + window.location.search : '/dashboard' }}
                        >
                            Sign in
                        </Link>
                    ) : (
                        <div className="rounded-md border border-border bg-muted px-3 py-2 text-xs text-muted-foreground">
                            <User className="h-4 w-4" />
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}
