import React from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import { Bell, ChevronRight, ChevronDown, GitBranch, Layers, LayoutGrid, ListChecks, Settings, ShieldCheck, Home, Activity, BarChart3, Menu, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import * as Tabs from '@radix-ui/react-tabs';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

import { cn } from '@/lib/cn';
import { apiFetchJson } from '@/api/client';
import { loadWatchState, setLastSeenEventId, toggleWatchedProject, toggleWatchedProtocol } from '@/app/watch/store';
import { useSettingsSnapshot } from '@/app/settings/store';
import { useDocumentVisible } from '@/app/polling';

type EventOut = {
  id: number;
  protocol_run_id: number;
  step_run_id?: number | null;
  event_type: string;
  message: string;
  created_at: string;
  metadata?: Record<string, unknown> | null;
  protocol_name?: string | null;
  project_id?: number | null;
  project_name?: string | null;
};

type NavItem = {
  to: string;
  label: string;
  icon: React.ReactNode;
  subItems?: NavItem[];
};

const navItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: <Home className="h-4 w-4" /> },
  { to: '/projects', label: 'Projects', icon: <LayoutGrid className="h-4 w-4" /> },
  { to: '/protocols', label: 'Protocols', icon: <GitBranch className="h-4 w-4" /> },
  { to: '/steps', label: 'Steps', icon: <ListChecks className="h-4 w-4" /> },
  { to: '/runs', label: 'Runs', icon: <Activity className="h-4 w-4" /> },
  {
    to: '/ops',
    label: 'Operations',
    icon: <Layers className="h-4 w-4" />,
    subItems: [
      { to: '/ops/queues', label: 'Queues', icon: <Layers className="h-3 w-3" /> },
      { to: '/ops/events', label: 'Events', icon: <Activity className="h-3 w-3" /> },
      { to: '/ops/metrics', label: 'Metrics', icon: <BarChart3 className="h-3 w-3" /> },
    ],
  },
  { to: '/policy-packs', label: 'Policy Packs', icon: <ShieldCheck className="h-4 w-4" /> },
  { to: '/settings', label: 'Settings', icon: <Settings className="h-4 w-4" /> },
];

function computeActive(pathname: string, itemTo: string): boolean {
  if (itemTo === '/ops') {
    return pathname.startsWith('/ops/');
  }
  if (itemTo.startsWith('/ops/')) {
    return pathname === itemTo || pathname.startsWith(itemTo + '/');
  }
  return pathname === itemTo || pathname.startsWith(itemTo + '/');
}

function breadcrumbsFor(pathname: string): Array<{ label: string; to?: string }> {
  const parts = pathname.split('/').filter(Boolean);
  if (parts.length === 0) return [{ label: 'Home', to: '/dashboard' }];
  const crumbs: Array<{ label: string; to?: string }> = [{ label: 'Home', to: '/dashboard' }];
  let accum = '';
  for (let i = 0; i < parts.length; i += 1) {
    const p = parts[i]!;
    accum += `/${p}`;
    const label = p.replace(/-/g, ' ');
    crumbs.push({ label, to: accum });
  }
  // Avoid linking the last breadcrumb to itself (prevents unnecessary reloads)
  if (crumbs.length > 0) {
    crumbs[crumbs.length - 1] = { label: crumbs[crumbs.length - 1]!.label };
  }
  return crumbs;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const crumbs = breadcrumbsFor(location.pathname);
  const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
  const [inboxOpen, setInboxOpen] = React.useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [watchedOnly, setWatchedOnly] = React.useState(true);
  const [watchState, setWatchState] = React.useState(() => loadWatchState());
  const settings = useSettingsSnapshot();
  const visible = useDocumentVisible();
  const pollEnabled = settings.polling.enabled && (!settings.polling.disableInBackground || visible);
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

  const events = useQuery({
    queryKey: ['ops', 'events', 'recent', 'inbox'],
    enabled: inboxOpen,
    queryFn: async () => await apiFetchJson<EventOut[]>('/events?limit=50'),
    staleTime: 5_000,
    refetchInterval: pollEnabled ? settings.polling.intervalsMs.recentEvents : false,
    retry: 1,
  });

  const filteredEvents = React.useMemo(() => {
    const list = events.data ?? [];
    if (!watchedOnly) return list;
    const watchedProjects = new Set(watchState.projects);
    const watchedProtocols = new Set(watchState.protocols);
    return list.filter((e) => {
      const pid = typeof e.project_id === 'number' ? e.project_id : null;
      const pr = typeof e.protocol_run_id === 'number' ? e.protocol_run_id : null;
      return (pid !== null && watchedProjects.has(pid)) || (pr !== null && watchedProtocols.has(pr));
    });
  }, [events.data, watchedOnly, watchState.projects, watchState.protocols]);

  return (
    <div className="min-h-screen">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 flex-col border-r border-border bg-bg-panel md:flex">
          <div className="flex items-center justify-between px-4 py-4">
            <div className="text-sm font-semibold tracking-wide">TasksGodzilla</div>
            <div className="text-xs text-fg-muted">console</div>
          </div>
          <nav className="flex-1 overflow-y-auto px-2 py-2">
            {navItems.map((item) => {
              const active = computeActive(location.pathname, item.to);

              if (item.subItems) {
                return (
                  <div key={item.to} className="mb-1">
                    <div
                      className={cn(
                        'flex items-center justify-between rounded-md px-3 py-2 text-sm text-fg-muted',
                        active && 'bg-bg-muted text-fg',
                      )}
                    >
                      <div className="flex items-center gap-2">
                        {item.icon}
                        <span>{item.label}</span>
                      </div>
                      <ChevronDown className="h-3 w-3" />
                    </div>
                    {active && (
                      <div className="ml-6 mt-1 space-y-1">
                        {item.subItems.map((subItem) => {
                          const subActive = computeActive(location.pathname, subItem.to);
                          return (
                            <Link
                              key={subItem.to}
                              to={subItem.to}
                              className={cn(
                                'flex items-center gap-2 rounded-md px-3 py-1.5 text-xs text-fg-muted hover:bg-bg-muted hover:text-fg',
                                subActive && 'bg-bg-muted/50 text-fg font-medium',
                              )}
                            >
                              {subItem.icon}
                              <span>{subItem.label}</span>
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              }

              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={cn(
                    'mb-1 flex items-center gap-2 rounded-md px-3 py-2 text-sm text-fg-muted hover:bg-bg-muted hover:text-fg',
                    active && 'bg-bg-muted text-fg',
                  )}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="mt-auto px-4 py-4 text-xs text-fg-muted">
            <div className="flex items-center gap-2">
              <GitBranch className="h-3 w-3" />
              <span>env: {import.meta.env.MODE}</span>
            </div>
          </div>
        </aside>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <>
            <div
              className="fixed inset-0 z-40 bg-black/50 md:hidden"
              onClick={() => setMobileMenuOpen(false)}
            />
            <aside className="fixed inset-y-0 left-0 z-50 w-64 flex-col border-r border-border bg-bg-panel md:hidden flex">
              <div className="flex items-center justify-between px-4 py-4 border-b border-border">
                <div className="text-sm font-semibold tracking-wide">TasksGodzilla</div>
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-md p-1 text-fg-muted hover:bg-bg-muted hover:text-fg"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <nav className="flex-1 overflow-y-auto px-2 py-2">
                {navItems.map((item) => {
                  const active = computeActive(location.pathname, item.to);

                  if (item.subItems) {
                    return (
                      <div key={item.to} className="mb-1">
                        <div
                          className={cn(
                            'flex items-center justify-between rounded-md px-3 py-2 text-sm text-fg-muted',
                            active && 'bg-bg-muted text-fg',
                          )}
                        >
                          <div className="flex items-center gap-2">
                            {item.icon}
                            <span>{item.label}</span>
                          </div>
                          <ChevronDown className="h-3 w-3" />
                        </div>
                        {active && (
                          <div className="ml-6 mt-1 space-y-1">
                            {item.subItems.map((subItem) => {
                              const subActive = computeActive(location.pathname, subItem.to);
                              return (
                                <Link
                                  key={subItem.to}
                                  to={subItem.to}
                                  onClick={() => setMobileMenuOpen(false)}
                                  className={cn(
                                    'flex items-center gap-2 rounded-md px-3 py-1.5 text-xs text-fg-muted hover:bg-bg-muted hover:text-fg',
                                    subActive && 'bg-bg-muted/50 text-fg font-medium',
                                  )}
                                >
                                  {subItem.icon}
                                  <span>{subItem.label}</span>
                                </Link>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  }

                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileMenuOpen(false)}
                      className={cn(
                        'mb-1 flex items-center gap-2 rounded-md px-3 py-2 text-sm text-fg-muted hover:bg-bg-muted hover:text-fg',
                        active && 'bg-bg-muted text-fg',
                      )}
                    >
                      {item.icon}
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
              <div className="mt-auto px-4 py-4 text-xs text-fg-muted border-t border-border">
                <div className="flex items-center gap-2">
                  <GitBranch className="h-3 w-3" />
                  <span>env: {import.meta.env.MODE}</span>
                </div>
              </div>
            </aside>
          </>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between border-b border-border bg-bg-panel px-4 py-3">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden rounded-md p-2 text-fg-muted hover:bg-bg-muted hover:text-fg mr-2"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1 text-sm font-medium">
                {crumbs.map((c, idx) => (
                  <React.Fragment key={`${c.label}-${idx}`}>
                    {idx > 0 && <ChevronRight className="h-3 w-3 text-fg-muted" />}
                    {c.to ? (
                      <Link to={c.to} className="text-fg-muted hover:text-fg">
                        {c.label}
                      </Link>
                    ) : (
                      <span className="text-fg">{c.label}</span>
                    )}
                  </React.Fragment>
                ))}
              </div>
              <div className="text-xs text-fg-muted">SSO-first console · live ops</div>
            </div>
            <div className="flex items-center gap-3">
              <Dialog.Root
                open={inboxOpen}
                onOpenChange={(open) => {
                  setInboxOpen(open);
                  if (open) {
                    setWatchState(loadWatchState());
                    // Mark as seen when opening (best-effort).
                    const latest = (events.data ?? [])[0]?.id;
                    if (typeof latest === 'number') setWatchState(setLastSeenEventId(latest));
                  }
                }}
              >
                <Dialog.Trigger asChild>
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-md border border-border bg-bg-muted px-3 py-2 text-xs text-fg hover:bg-bg-panel"
                  >
                    <Bell className="h-4 w-4" />
                    <span>Inbox</span>
                  </button>
                </Dialog.Trigger>
                <Dialog.Portal>
                  <Dialog.Overlay className="fixed inset-0 bg-black/50" />
                  <Dialog.Content className="fixed right-4 top-4 h-[85vh] w-[min(720px,calc(100vw-2rem))] overflow-hidden rounded-md border border-border bg-bg-panel shadow-xl">
                    <div className="flex items-center justify-between border-b border-border px-4 py-3">
                      <div>
                        <Dialog.Title className="text-sm font-medium">Inbox</Dialog.Title>
                        <div className="text-xs text-fg-muted">Recent activity, failures, and watched updates.</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="flex items-center gap-2 text-xs text-fg-muted">
                          <input type="checkbox" checked={watchedOnly} onChange={(e) => setWatchedOnly(e.target.checked)} />
                          <span>Watched only</span>
                        </label>
                        <Dialog.Close asChild>
                          <button className="rounded-md border border-border bg-bg-muted px-3 py-2 text-xs hover:bg-bg-panel">
                            Close
                          </button>
                        </Dialog.Close>
                      </div>
                    </div>

                    <Tabs.Root defaultValue="activity" className="flex h-full flex-col">
                      <Tabs.List className="flex gap-2 border-b border-border px-4 py-2">
                        <Tabs.Trigger
                          value="activity"
                          className="rounded-md px-3 py-2 text-sm text-fg-muted data-[state=active]:bg-bg-muted data-[state=active]:text-fg"
                        >
                          Activity
                        </Tabs.Trigger>
                        <Tabs.Trigger
                          value="watch"
                          className="rounded-md px-3 py-2 text-sm text-fg-muted data-[state=active]:bg-bg-muted data-[state=active]:text-fg"
                        >
                          Watches
                        </Tabs.Trigger>
                      </Tabs.List>

                      <Tabs.Content value="activity" className="min-h-0 flex-1 overflow-auto p-4">
                        {(filteredEvents ?? []).length === 0 ? (
                          <div className="text-sm text-fg-muted">{events.isLoading ? 'Loading…' : 'No events.'}</div>
                        ) : (
                          <div className="space-y-2">
                            {filteredEvents.map((e) => {
                              const isNew = typeof watchState.lastSeenEventId === 'number' ? e.id > watchState.lastSeenEventId : false;
                              return (
                                <div
                                  key={e.id}
                                  className={cn(
                                    'rounded-md border border-border bg-bg-muted p-3',
                                    isNew && 'border-sky-400/40',
                                  )}
                                >
                                  <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div className="text-xs text-fg-muted">
                                      #{e.id} · {e.event_type} · {e.created_at}
                                    </div>
                                    <div className="flex items-center gap-2">
                                      {typeof e.project_id === 'number' ? (
                                        <Link
                                          to="/projects/$projectId"
                                          params={{ projectId: String(e.project_id) }}
                                          className="text-xs text-sky-300 hover:underline"
                                        >
                                          project:{e.project_id}
                                        </Link>
                                      ) : null}
                                      <Link
                                        to="/protocols/$protocolId"
                                        params={{ protocolId: String(e.protocol_run_id) }}
                                        className="text-xs text-sky-300 hover:underline"
                                      >
                                        protocol:{e.protocol_run_id}
                                      </Link>
                                    </div>
                                  </div>
                                  <div className="mt-1 text-sm text-fg">{e.message}</div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </Tabs.Content>

                      <Tabs.Content value="watch" className="min-h-0 flex-1 overflow-auto p-4">
                        <div className="grid gap-3 md:grid-cols-2">
                          <div className="rounded-md border border-border bg-bg-muted p-3">
                            <div className="text-sm font-medium">Watched projects</div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {watchState.projects.length === 0 ? (
                                <div className="text-sm text-fg-muted">None</div>
                              ) : (
                                watchState.projects.map((id) => (
                                  <button
                                    key={id}
                                    type="button"
                                    onClick={() => setWatchState(toggleWatchedProject(id))}
                                    className="rounded-md border border-border bg-bg-panel px-3 py-2 text-xs hover:bg-bg-muted"
                                  >
                                    {id} ×
                                  </button>
                                ))
                              )}
                            </div>
                          </div>
                          <div className="rounded-md border border-border bg-bg-muted p-3">
                            <div className="text-sm font-medium">Watched protocols</div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {watchState.protocols.length === 0 ? (
                                <div className="text-sm text-fg-muted">None</div>
                              ) : (
                                watchState.protocols.map((id) => (
                                  <button
                                    key={id}
                                    type="button"
                                    onClick={() => setWatchState(toggleWatchedProtocol(id))}
                                    className="rounded-md border border-border bg-bg-panel px-3 py-2 text-xs hover:bg-bg-muted"
                                  >
                                    {id} ×
                                  </button>
                                ))
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="mt-4 rounded-md border border-border bg-bg-muted p-3 text-xs text-fg-muted">
                          Tip: use the Watch buttons on Project/Protocol pages to subscribe.
                        </div>
                      </Tabs.Content>
                    </Tabs.Root>
                  </Dialog.Content>
                </Dialog.Portal>
              </Dialog.Root>
              {authed && me ? (
                <div className="rounded-md border border-border bg-bg-muted px-3 py-2 text-xs text-fg">
                  {me.name || me.email || me.username || 'User'}
                </div>
              ) : authMode === 'oidc' ? (
                <a
                  className="rounded-md border border-border bg-bg-muted px-3 py-2 text-xs text-fg hover:bg-bg-panel"
                  href={`${apiBase}/auth/login?next=${encodeURIComponent(
                    typeof window !== 'undefined' ? window.location.pathname + window.location.search : '/console',
                  )}`}
                >
                  Sign in
                </a>
              ) : authMode === 'jwt' ? (
                <Link
                  className="rounded-md border border-border bg-bg-muted px-3 py-2 text-xs text-fg hover:bg-bg-panel"
                  to="/login"
                  search={{ next: typeof window !== 'undefined' ? window.location.pathname + window.location.search : '/dashboard' }}
                >
                  Sign in
                </Link>
              ) : (
                <div className="rounded-md border border-border bg-bg-muted px-3 py-2 text-xs text-fg-muted">
                  Auth: disabled
                </div>
              )}
            </div>
          </header>

          <main className="min-w-0 flex-1 p-4">{children}</main>

          <footer className="border-t border-border bg-bg-panel px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-4 text-xs text-fg-muted">
              <div className="flex items-center gap-4">
                <span>&copy; {new Date().getFullYear()} TasksGodzilla</span>
                <span className="hidden sm:inline">·</span>
                <span className="hidden sm:inline">Hobby Edition Alpha 0.1</span>
              </div>
              <div className="flex items-center gap-4">
                <a
                  href="https://github.com/anthropics/claude-code"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-fg hover:underline"
                >
                  Documentation
                </a>
                <span>·</span>
                <Link to="/settings" className="hover:text-fg hover:underline">
                  Settings
                </Link>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
