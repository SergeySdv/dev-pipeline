import React, { useState } from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import { X, Menu, GitBranch } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import * as Tabs from '@radix-ui/react-tabs';

import { cn } from '@/lib/cn';
import { apiFetchJson } from '@/api/client';
import { loadWatchState, setLastSeenEventId, toggleWatchedProject, toggleWatchedProtocol } from '@/app/watch/store';
import { useSettingsSnapshot } from '@/app/settings/store';
import { useDocumentVisible } from '@/app/polling';

import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { Breadcrumbs } from '@/components/layout/Breadcrumbs';
import { CommandPalette } from '@/components/layout/CommandPalette';

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

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [inboxOpen, setInboxOpen] = useState(false);
  const [watchedOnly, setWatchedOnly] = useState(true);
  const [watchState, setWatchState] = useState(() => loadWatchState());

  const settings = useSettingsSnapshot();
  const visible = useDocumentVisible();
  const pollEnabled = settings.polling.enabled && (!settings.polling.disableInBackground || visible);

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
    <div className="min-h-screen bg-background">
      <div className="flex min-h-screen">
        {/* Desktop Sidebar */}
        <Sidebar />

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <>
            <div
              className="fixed inset-0 z-40 bg-black/50 md:hidden"
              onClick={() => setMobileMenuOpen(false)}
            />
            <aside className="fixed inset-y-0 left-0 z-50 w-64 flex flex-col border-r border-border bg-background md:hidden">
              <div className="flex items-center justify-between px-4 py-4 border-b border-border">
                <div className="text-sm font-semibold tracking-wide">TasksGodzilla</div>
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <nav className="flex-1 overflow-y-auto p-4">
                <p className="text-sm text-muted-foreground">Mobile navigation</p>
              </nav>
              <div className="border-t border-border p-4">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <GitBranch className="h-3 w-3" />
                  <span>env: {import.meta.env.MODE}</span>
                </div>
              </div>
            </aside>
          </>
        )}

        {/* Main Content */}
        <div className="flex min-w-0 flex-1 flex-col">
          <Header
            onMobileMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)}
            mobileMenuOpen={mobileMenuOpen}
          />
          <Breadcrumbs />

          <main className="min-w-0 flex-1 p-6">{children}</main>

          <footer className="border-t border-border bg-background px-6 py-4">
            <div className="flex flex-wrap items-center justify-between gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-4">
                <span>© {new Date().getFullYear()} TasksGodzilla</span>
                <span className="hidden sm:inline">·</span>
                <span className="hidden sm:inline">Hobby Edition Alpha 0.1</span>
              </div>
              <div className="flex items-center gap-4">
                <a
                  href="https://github.com/anthropics/claude-code"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-foreground hover:underline"
                >
                  Documentation
                </a>
                <span>·</span>
                <Link to="/settings" className="hover:text-foreground hover:underline">
                  Settings
                </Link>
              </div>
            </div>
          </footer>
        </div>
      </div>

      <CommandPalette />

      {/* Inbox Dialog - Keep existing functionality */}
      <Dialog.Root
        open={inboxOpen}
        onOpenChange={(open) => {
          setInboxOpen(open);
          if (open) {
            setWatchState(loadWatchState());
            const latest = (events.data ?? [])[0]?.id;
            if (typeof latest === 'number') setWatchState(setLastSeenEventId(latest));
          }
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50" />
          <Dialog.Content className="fixed right-4 top-4 h-[85vh] w-[min(720px,calc(100vw-2rem))] overflow-hidden rounded-md border border-border bg-background shadow-xl">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div>
                <Dialog.Title className="text-sm font-medium">Inbox</Dialog.Title>
                <div className="text-xs text-muted-foreground">Recent activity, failures, and watched updates.</div>
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 text-xs text-muted-foreground">
                  <input type="checkbox" checked={watchedOnly} onChange={(e) => setWatchedOnly(e.target.checked)} />
                  <span>Watched only</span>
                </label>
                <Dialog.Close asChild>
                  <button className="rounded-md border border-border bg-muted px-3 py-2 text-xs hover:bg-accent">
                    Close
                  </button>
                </Dialog.Close>
              </div>
            </div>

            <Tabs.Root defaultValue="activity" className="flex h-full flex-col">
              <Tabs.List className="flex gap-2 border-b border-border px-4 py-2">
                <Tabs.Trigger
                  value="activity"
                  className="rounded-md px-3 py-2 text-sm text-muted-foreground data-[state=active]:bg-muted data-[state=active]:text-foreground"
                >
                  Activity
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="watch"
                  className="rounded-md px-3 py-2 text-sm text-muted-foreground data-[state=active]:bg-muted data-[state=active]:text-foreground"
                >
                  Watches
                </Tabs.Trigger>
              </Tabs.List>

              <Tabs.Content value="activity" className="min-h-0 flex-1 overflow-auto p-4">
                {(filteredEvents ?? []).length === 0 ? (
                  <div className="text-sm text-muted-foreground">{events.isLoading ? 'Loading…' : 'No events.'}</div>
                ) : (
                  <div className="space-y-2">
                    {filteredEvents.map((e) => {
                      const isNew = typeof watchState.lastSeenEventId === 'number' ? e.id > watchState.lastSeenEventId : false;
                      return (
                        <div
                          key={e.id}
                          className={cn(
                            'rounded-md border border-border bg-muted p-3',
                            isNew && 'border-sky-400/40'
                          )}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="text-xs text-muted-foreground">
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
                          <div className="mt-1 text-sm text-foreground">{e.message}</div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Tabs.Content>

              <Tabs.Content value="watch" className="min-h-0 flex-1 overflow-auto p-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-md border border-border bg-muted p-3">
                    <div className="text-sm font-medium">Watched projects</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {watchState.projects.length === 0 ? (
                        <div className="text-sm text-muted-foreground">None</div>
                      ) : (
                        watchState.projects.map((id) => (
                          <button
                            key={id}
                            type="button"
                            onClick={() => setWatchState(toggleWatchedProject(id))}
                            className="rounded-md border border-border bg-background px-3 py-2 text-xs hover:bg-muted"
                          >
                            {id} ×
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                  <div className="rounded-md border border-border bg-muted p-3">
                    <div className="text-sm font-medium">Watched protocols</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {watchState.protocols.length === 0 ? (
                        <div className="text-sm text-muted-foreground">None</div>
                      ) : (
                        watchState.protocols.map((id) => (
                          <button
                            key={id}
                            type="button"
                            onClick={() => setWatchState(toggleWatchedProtocol(id))}
                            className="rounded-md border border-border bg-background px-3 py-2 text-xs hover:bg-muted"
                          >
                            {id} ×
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-4 rounded-md border border-border bg-muted p-3 text-xs text-muted-foreground">
                  Tip: use the Watch buttons on Project/Protocol pages to subscribe.
                </div>
              </Tabs.Content>
            </Tabs.Root>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
