import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from '@tanstack/react-router';
import { Activity, AlertCircle, CheckCircle, Clock, Layers, LayoutGrid, GitBranch } from 'lucide-react';
import { apiFetchJson } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusPill } from '@/components/ui/StatusPill';

interface DashboardStats {
  projects: {
    total: number;
    active: number;
  };
  protocols: {
    total: number;
    running: number;
    completed: number;
    failed: number;
  };
  steps: {
    total: number;
    pending: number;
    running: number;
    completed: number;
  };
  runs: {
    total: number;
    queued: number;
    running: number;
    succeeded: number;
    failed: number;
  };
}

interface RecentActivity {
  id: number;
  event_type: string;
  message: string;
  protocol_run_id?: number;
  project_id?: number;
  created_at: string;
}

export function DashboardPage() {
  const navigate = useNavigate();

  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: () => apiFetchJson<any[]>('/projects'),
  });

  const { data: protocols, isLoading: protocolsLoading } = useQuery({
    queryKey: ['protocols', 'list'],
    queryFn: () => apiFetchJson<any[]>('/protocols'),
  });

  const { data: recentEvents, isLoading: eventsLoading } = useQuery({
    queryKey: ['dashboard', 'events', 'recent'],
    queryFn: () => apiFetchJson<RecentActivity[]>('/events?limit=10'),
  });

  const { data: queueStats } = useQuery({
    queryKey: ['ops', 'queues', 'stats'],
    queryFn: () => apiFetchJson<any>('/queues'),
    refetchInterval: 5000,
  });

  const isLoading = projectsLoading || protocolsLoading || eventsLoading;

  if (isLoading) {
    return <LoadingState message="Loading dashboard..." />;
  }

  const projectsCount = projects?.length ?? 0;
  const runningProtocols = protocols?.filter((p) => p.status === 'running').length ?? 0;
  const completedProtocols = protocols?.filter((p) => p.status === 'completed').length ?? 0;
  const failedProtocols = protocols?.filter((p) => p.status === 'failed').length ?? 0;
  const totalProtocols = protocols?.length ?? 0;
  const successRate = totalProtocols > 0 ? Math.round((completedProtocols / totalProtocols) * 100) : 0;

  const stats = [
    {
      label: 'Total Projects',
      value: projectsCount,
      icon: <LayoutGrid className="h-5 w-5" />,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50/50',
      to: '/projects',
    },
    {
      label: 'Active Runs',
      value: runningProtocols,
      icon: <Activity className="h-5 w-5" />,
      color: 'text-amber-500',
      bgColor: 'bg-amber-50/50',
      to: '/protocols',
    },
    {
      label: 'Success Rate',
      value: `${successRate}%`,
      icon: <CheckCircle className="h-5 w-5" />,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50/50',
      to: '/protocols',
      subtext: `${completedProtocols} / ${totalProtocols} runs`,
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-fg">Dashboard</h1>
        <p className="text-fg-muted mt-2 text-lg">Overview of your system performance and activity.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {stats.map((stat) => (
          <Link
            key={stat.label}
            to={stat.to}
            className="group relative overflow-hidden rounded-xl border border-border bg-bg-panel p-6 shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-md hover:border-sky-400/30"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-fg-muted">{stat.label}</p>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-fg tracking-tight">{stat.value}</span>
                  {stat.subtext && <span className="text-xs text-fg-muted">{stat.subtext}</span>}
                </div>
              </div>
              <div className={`rounded-lg ${stat.bgColor} p-3 ${stat.color} transition-colors group-hover:bg-opacity-100`}>
                {stat.icon}
              </div>
            </div>
            <div className="absolute bottom-0 left-0 h-1 w-full bg-gradient-to-r from-transparent via-current to-transparent opacity-0 transition-opacity group-hover:opacity-10 text-sky-500" />
          </Link>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Activity - Spans 2 cols */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-bg-panel shadow-sm">
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <h2 className="text-lg font-semibold text-fg">Recent Activity</h2>
            <Button
              variant="ghost"
              size="small"
              onClick={() => navigate({ to: '/ops/events' })}
              className="text-xs font-medium text-fg-muted hover:text-fg"
            >
              View all
            </Button>
          </div>
          <div className="p-2">
            {!recentEvents || recentEvents.length === 0 ? (
              <div className="flex h-48 flex-col items-center justify-center text-fg-muted">
                <Activity className="mb-2 h-8 w-8 opacity-20" />
                <p>No recent activity</p>
              </div>
            ) : (
              <div className="space-y-1">
                {recentEvents.slice(0, 5).map((event) => (
                  <div
                    key={event.id}
                    className="flex items-start gap-4 rounded-lg p-3 hover:bg-bg-muted/50 transition-colors"
                  >
                    <div className="mt-1 rounded-full bg-bg-muted p-1.5 text-fg-muted">
                      <Layers className="h-3 w-3" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium text-fg break-words">{event.message}</p>
                        <span className="text-xs text-fg-muted whitespace-nowrap">
                          {new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-xs text-fg-muted">
                        {event.project_id && (
                          <span className="flex items-center gap-1">
                            <LayoutGrid className="h-3 w-3" /> Project #{event.project_id}
                          </span>
                        )}
                        {event.protocol_run_id && (
                          <span className="flex items-center gap-1">
                            <GitBranch className="h-3 w-3" /> Run #{event.protocol_run_id}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions & Status - Spans 1 col */}
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-bg-panel p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-fg mb-4">Quick Actions</h2>
            <div className="grid gap-3">
              <Button
                variant="default"
                className="w-full justify-start h-10 shadow-sm"
                onClick={() => navigate({ to: '/projects/new' })}
              >
                <LayoutGrid className="mr-2 h-4 w-4" />
                New Project
              </Button>
              <Button
                variant="secondary"
                className="w-full justify-start h-10"
                onClick={() => navigate({ to: '/ops/events' })}
              >
                <Activity className="mr-2 h-4 w-4" />
                View Events
              </Button>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-bg-panel p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-fg mb-4">System Health</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-fg-muted">API Status</span>
                <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  Operational
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-fg-muted">Pending Jobs</span>
                <span className="font-mono text-sm text-fg">{queueStats?.total_jobs ?? 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
