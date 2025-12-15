import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from '@tanstack/react-router';
import { Activity, CheckCircle, Layers, LayoutGrid, GitBranch, FolderGit2, PlayCircle, AlertCircle, TrendingUp } from 'lucide-react';
import { apiFetchJson } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/cn';

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

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ['runs', 'list'],
    queryFn: () => apiFetchJson<any[]>('/runs'),
  });

  const { data: recentEvents, isLoading: eventsLoading } = useQuery({
    queryKey: ['dashboard', 'events', 'recent'],
    queryFn: () => apiFetchJson<RecentActivity[]>('/events?limit=10'),
  });

  const isLoading = projectsLoading || protocolsLoading || eventsLoading || runsLoading;

  if (isLoading) {
    return <LoadingState message="Loading dashboard..." />;
  }

  const projectsCount = projects?.length ?? 0;
  const activeProtocols = protocols?.filter((p) => p.status === 'running') ?? [];
  const totalRuns = runs?.length ?? 0;
  const failedRuns = runs?.filter((r) => r.status === 'failed').length ?? 0;
  const recentRuns = runs?.slice(0, 5) ?? [];

  const stats = [
    {
      label: 'Total Projects',
      value: projectsCount,
      icon: FolderGit2,
      color: 'text-blue-500',
      href: '/projects',
    },
    {
      label: 'Active Protocols',
      value: activeProtocols.length,
      icon: Activity,
      color: 'text-green-500',
      href: '/protocols',
    },
    {
      label: 'Total Runs',
      value: totalRuns,
      icon: PlayCircle,
      color: 'text-purple-500',
      href: '/runs',
    },
    {
      label: 'Failed Runs',
      value: failedRuns,
      icon: AlertCircle,
      color: 'text-red-500',
      href: '/runs?status=failed',
    },
  ];

  return (
    <div className="container py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your TasksGodzilla workspace</p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Link key={stat.label} to={stat.href}>
              <Card className="transition-colors hover:border-primary/50">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">{stat.label}</CardTitle>
                  <Icon className={cn('h-4 w-4', stat.color)} />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stat.value}</div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      {/* Two Column Layout */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Active Protocols */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Active Protocols
            </CardTitle>
            <CardDescription>Protocols currently running</CardDescription>
          </CardHeader>
          <CardContent>
            {activeProtocols.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4">No active protocols</p>
            ) : (
              <div className="space-y-3">
                {activeProtocols.slice(0, 5).map((protocol) => (
                  <Link key={protocol.id} to="/protocols/$protocolId" params={{ protocolId: String(protocol.id) }}>
                    <div className="flex items-center justify-between rounded-lg border p-3 hover:bg-accent">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">{protocol.name}</p>
                        <p className="text-xs text-muted-foreground">
                          Project: {projects?.find((p) => p.id === protocol.project_id)?.name ?? 'Unknown'}
                        </p>
                      </div>
                      <Badge variant="secondary">{protocol.status}</Badge>
                    </div>
                  </Link>
                ))}
                {activeProtocols.length > 5 && (
                  <Link to="/protocols">
                    <Button variant="ghost" size="sm" className="w-full">
                      View all active protocols
                    </Button>
                  </Link>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Runs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlayCircle className="h-5 w-5" />
              Recent Runs
            </CardTitle>
            <CardDescription>Latest execution runs</CardDescription>
          </CardHeader>
          <CardContent>
            {recentRuns.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4">No recent runs</p>
            ) : (
              <div className="space-y-3">
                {recentRuns.map((run) => (
                  <Link key={run.run_id} to="/runs/$runId" params={{ runId: String(run.run_id) }}>
                    <div className="flex items-center justify-between rounded-lg border p-3 hover:bg-accent">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">{run.job_type}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(run.created_at).toLocaleString()}
                        </p>
                      </div>
                      <Badge
                        variant={
                          run.status === 'completed' ? 'default' :
                            run.status === 'failed' ? 'destructive' : 'secondary'
                        }
                      >
                        {run.status}
                      </Badge>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Quick Actions
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Link to="/projects">
            <Button variant="outline">View Projects</Button>
          </Link>
          <Link to="/runs">
            <Button variant="outline">View All Runs</Button>
          </Link>
          <Link to="/ops/queues">
            <Button variant="outline">Operations Dashboard</Button>
          </Link>
          <Link to="/policy-packs">
            <Button variant="outline">Policy Packs</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
