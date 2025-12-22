import { Link, useParams, useSearch } from '@tanstack/react-router';
import { useMutation, useQuery } from '@tanstack/react-query';
import React from 'react';
import { toast } from 'sonner';
import { Settings, RefreshCw, Trash2, MoreVertical, Edit } from 'lucide-react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

import { apiFetchJson } from '@/api/client';
import { loadWatchState, toggleWatchedProject } from '@/app/watch/store';
import { useProject } from './hooks';

const tabs = [
  { key: 'overview', label: 'Overview' },
  { key: 'onboarding', label: 'Onboarding' },
  { key: 'protocols', label: 'Protocols' },
  { key: 'policy', label: 'Policy' },
  { key: 'clarifications', label: 'Clarifications' },
  { key: 'branches', label: 'Branches' },
] as const;

export function ProjectDetailPage() {
  const { projectId } = useParams({ from: '/projects/$projectId' });
  const search = useSearch({ from: '/projects/$projectId' });
  const activeTab = search.tab ?? 'overview';
  const pid = Number(projectId);
  const { data: project } = useProject(pid);
  const [watch, setWatch] = React.useState(() => loadWatchState());
  const isWatched = Number.isFinite(pid) && watch.projects.includes(pid);

  const branches = useQuery({
    queryKey: ['projects', pid, 'branches'],
    enabled: activeTab === 'branches' && Number.isFinite(pid),
    queryFn: async () => await apiFetchJson<{ branches: string[] }>(`/projects/${pid}/branches`),
    staleTime: 5_000,
    retry: 1,
  });

  const deleteBranch = useMutation({
    mutationFn: async (branch: string) =>
      await apiFetchJson(`/projects/${pid}/branches/${encodeURIComponent(branch)}/delete`, {
        method: 'POST',
        body: JSON.stringify({ confirm: true }),
      }),
    onSuccess: async () => {
      await branches.refetch();
      toast.success('Branch deleted');
    },
    onError: (err) => toast.error(String(err)),
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs text-fg-muted">Project</div>
          <h1 className="text-lg font-semibold">{projectId}</h1>
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button
                type="button"
                className="rounded-md border border-border bg-bg-panel px-3 py-2 text-sm hover:bg-bg-muted flex items-center gap-2"
              >
                <span>Actions</span>
                <MoreVertical className="h-4 w-4" />
              </button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className="min-w-[180px] rounded-md border border-border bg-bg-panel p-1 shadow-md z-50 animate-in fade-in-0 zoom-in-95"
                sideOffset={5}
                align="end"
              >
                <DropdownMenu.Item className="flex items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none cursor-pointer hover:bg-bg-muted focus:bg-bg-muted text-fg">
                  <Edit className="h-4 w-4 text-fg-muted" />
                  <span>Edit Configuration</span>
                </DropdownMenu.Item>
                <DropdownMenu.Item className="flex items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none cursor-pointer hover:bg-bg-muted focus:bg-bg-muted text-fg">
                  <RefreshCw className="h-4 w-4 text-fg-muted" />
                  <span>Sync Repository</span>
                </DropdownMenu.Item>
                <DropdownMenu.Separator className="my-1 h-px bg-border" />
                <DropdownMenu.Item 
                  className="flex items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none cursor-pointer hover:bg-red-50 focus:bg-red-50 text-red-600"
                  onClick={() => {
                     if (window.confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
                        toast.error('Delete functionality coming soon');
                     }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Delete Project</span>
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>

          <button
            type="button"
            className="rounded-md border border-border bg-bg-panel px-3 py-2 text-sm hover:bg-bg-muted"
            onClick={() => {
              if (!Number.isFinite(pid)) return;
              setWatch(toggleWatchedProject(pid));
            }}
          >
            {isWatched ? 'Unwatch' : 'Watch'}
          </button>
          <Link
            to="/projects"
            className="rounded-md border border-border bg-bg-panel px-3 py-2 text-sm hover:bg-bg-muted"
          >
            Back
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 rounded-md border border-border bg-bg-panel p-2">
        {tabs.map((t) => (
          <Link
            key={t.key}
            to="/projects/$projectId"
            params={{ projectId }}
            search={{ tab: t.key }}
            className={[
              'rounded-md px-3 py-2 text-sm',
              activeTab === t.key ? 'bg-bg-muted text-fg' : 'text-fg-muted hover:bg-bg-muted hover:text-fg',
            ].join(' ')}
          >
            {t.label}
          </Link>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-4">
             <div className="rounded-md border border-border bg-bg-panel p-6 shadow-sm">
                <div className="flex items-start justify-between">
                    <div>
                        <h2 className="text-xl font-semibold mb-1">{project?.name || 'Loading...'}</h2>
                        <div className="text-sm text-fg-muted flex gap-4">
                            <span>ID: {pid}</span>
                            {project?.created_at && <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>}
                        </div>
                    </div>
                </div>
                
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                         <h3 className="text-sm font-medium text-fg-muted mb-2">Repository</h3>
                         <div className="flex items-center gap-2 text-sm">
                             <span className="font-mono bg-bg-muted px-2 py-1 rounded border border-border">{project?.git_url || '-'}</span>
                             <span className="text-fg-muted">on</span>
                             <span className="font-mono">{project?.base_branch || 'main'}</span>
                         </div>
                    </div>
                     <div>
                         <h3 className="text-sm font-medium text-fg-muted mb-2">Policy</h3>
                          <div className="text-sm">
                             <span className="bg-blue-50 text-blue-700 px-2 py-1 rounded text-xs uppercase tracking-wide font-semibold">
                                {project?.policy_enforcement_mode || 'Enabled'}
                             </span>
                          </div>
                     </div>
                </div>
             </div>
        </div>
      )}
      {activeTab === 'onboarding' && (
        <div className="rounded-md border border-border bg-bg-panel p-4 text-sm text-fg-muted">
          Onboarding stages + events timeline.
        </div>
      )}
      {activeTab === 'protocols' && (
        <div className="rounded-md border border-border bg-bg-panel p-4">
          <div className="text-sm font-medium">Protocols</div>
          <div className="mt-2 flex flex-wrap gap-2">
            <Link
              to="/protocols/new"
              search={{ projectId }}
              className="rounded-md border border-border bg-bg-muted px-3 py-2 text-sm hover:bg-bg-panel"
            >
              Create protocol
            </Link>
            <Link
              to="/protocols/$protocolId"
              params={{ protocolId: '1' }}
              className="rounded-md border border-border bg-bg-muted px-3 py-2 text-sm hover:bg-bg-panel"
            >
              Open protocol #1
            </Link>
          </div>
        </div>
      )}
      {activeTab === 'policy' && (
        <div className="rounded-md border border-border bg-bg-panel p-4 text-sm text-fg-muted">
          Project policy pack selection + overrides + effective policy + findings.
        </div>
      )}
      {activeTab === 'clarifications' && (
        <div className="rounded-md border border-border bg-bg-panel p-4 text-sm text-fg-muted">
          Project clarifications Q&A.
        </div>
      )}
      {activeTab === 'branches' && (
        <div className="rounded-md border border-border bg-bg-panel p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Branches</div>
              <div className="mt-1 text-xs text-fg-muted">Remote branches (delete requires RBAC in OIDC mode).</div>
            </div>
            <button
              type="button"
              className="rounded-md border border-border bg-bg-muted px-3 py-2 text-sm hover:bg-bg-panel"
              onClick={() => branches.refetch()}
            >
              Refresh
            </button>
          </div>

          <div className="mt-4 space-y-2">
            {(branches.data?.branches ?? []).length === 0 ? (
              <div className="text-sm text-fg-muted">{branches.isLoading ? 'Loading…' : 'No branches found.'}</div>
            ) : (
              (branches.data?.branches ?? []).map((b) => (
                <div key={b} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-bg-muted p-3">
                  <div className="min-w-0 font-mono text-xs text-fg">{b}</div>
                  <button
                    type="button"
                    className="rounded-md border border-border bg-bg-panel px-3 py-2 text-xs hover:bg-bg-muted"
                    disabled={deleteBranch.isPending}
                    onClick={() => {
                      if (!window.confirm(`Delete remote branch ${b}?`)) return;
                      deleteBranch.mutate(b);
                    }}
                  >
                    Delete
                  </button>
                </div>
              ))
            )}
            {branches.error ? <div className="text-sm text-red-300">{String(branches.error)}</div> : null}
          </div>
        </div>
      )}
    </div>
  );
}
