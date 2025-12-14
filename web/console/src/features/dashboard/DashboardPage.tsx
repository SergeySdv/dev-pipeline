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
  const protocolsCount = protocols?.length ?? 0;
  const runningProtocols = protocols?.filter((p) => p.status === 'running').length ?? 0;
  const completedProtocols = protocols?.filter((p) => p.status === 'completed').length ?? 0;
  const failedProtocols = protocols?.filter((p) => p.status === 'failed').length ?? 0;

  const stats = [
    {
      label: 'Projects',
      value: projectsCount,
      icon: <LayoutGrid className="h-5 w-5" />,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      to: '/projects',
    },
    {
      label: 'Protocols',
      value: protocolsCount,
      icon: <GitBranch className="h-5 w-5" />,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      to: '/protocols',
    },
    {
      label: 'Running',
      value: runningProtocols,
      icon: <Activity className="h-5 w-5" />,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      to: '/protocols',
    },
    {
      label: 'Queue Jobs',
      value: queueStats?.total_jobs ?? 0,
      icon: <Layers className="h-5 w-5" />,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      to: '/ops/queues',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">System overview and recent activity</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Link
            key={stat.label}
            to={stat.to}
            className="block rounded-lg border border-border bg-bg-panel p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-fg-muted">{stat.label}</p>
                <p className="mt-2 text-3xl font-semibold text-fg">{stat.value}</p>
              </div>
              <div className={`rounded-lg ${stat.bgColor} p-3 ${stat.color}`}>
                {stat.icon}
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-bg-panel p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-fg">Protocol Status</h2>
            <Button
              variant="ghost"
              size="small"
              onClick={() => navigate({ to: '/protocols' })}
            >
              View all
            </Button>
          </div>
          <div className="space-y-3">
            {protocolsCount === 0 ? (
              <p className="text-sm text-fg-muted">No protocols yet</p>
            ) : (
              <>
                <div className="flex items-center justify-between rounded-md bg-bg-muted p-3">
                  <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-fg">Running</span>
                  </div>
                  <span className="text-lg font-semibold text-fg">{runningProtocols}</span>
                </div>
                <div className="flex items-center justify-between rounded-md bg-bg-muted p-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-blue-600" />
                    <span className="text-sm text-fg">Completed</span>
                  </div>
                  <span className="text-lg font-semibold text-fg">{completedProtocols}</span>
                </div>
                <div className="flex items-center justify-between rounded-md bg-bg-muted p-3">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <span className="text-sm text-fg">Failed</span>
                  </div>
                  <span className="text-lg font-semibold text-fg">{failedProtocols}</span>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-bg-panel p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-fg">Recent Activity</h2>
            <Button
              variant="ghost"
              size="small"
              onClick={() => navigate({ to: '/ops/events' })}
            >
              View all
            </Button>
          </div>
          <div className="space-y-3">
            {!recentEvents || recentEvents.length === 0 ? (
              <p className="text-sm text-fg-muted">No recent activity</p>
            ) : (
              recentEvents.slice(0, 5).map((event) => (
                <div
                  key={event.id}
                  className="rounded-md border border-border bg-bg-muted p-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-fg line-clamp-2">{event.message}</p>
                      <div className="mt-1 flex items-center gap-2 text-xs text-fg-muted">
                        <Clock className="h-3 w-3" />
                        <span>{new Date(event.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                    {event.protocol_run_id && (
                      <Link
                        to="/protocols/$protocolId"
                        params={{ protocolId: String(event.protocol_run_id) }}
                        className="text-xs text-blue-600 hover:underline whitespace-nowrap"
                      >
                        #{event.protocol_run_id}
                      </Link>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-bg-panel p-6">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-fg">Quick Actions</h2>
          </div>
          <div className="grid gap-3">
            <Button
              variant="default"
              className="justify-start"
              onClick={() => navigate({ to: '/projects/new' })}
            >
              <LayoutGrid className="mr-2 h-4 w-4" />
              Create New Project
            </Button>
            <Button
              variant="default"
              className="justify-start"
              onClick={() => navigate({ to: '/protocols/new' })}
            >
              <GitBranch className="mr-2 h-4 w-4" />
              Create New Protocol
            </Button>
            <Button
              variant="default"
              className="justify-start"
              onClick={() => navigate({ to: '/ops/queues' })}
            >
              <Layers className="mr-2 h-4 w-4" />
              View Queue Status
            </Button>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-bg-panel p-6">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-fg">System Status</h2>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-fg-muted">API Status</span>
              <StatusPill status="completed" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-fg-muted">Queue Workers</span>
              <StatusPill status="running" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-fg-muted">Pending Jobs</span>
              <span className="text-sm font-medium text-fg">
                {queueStats?.total_jobs ?? 0}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
