import React from 'react';
import { useNavigate } from '@tanstack/react-router';
import { apiFetchJson } from '@/api/client';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusPill } from '@/components/ui/StatusPill';
import { DataTable, Column } from '@/components/ui/DataTable';
import { Activity, Clock, Terminal, Box } from 'lucide-react';

interface Run {
  run_id: number;
  project_id?: number;
  protocol_id?: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

function useRuns() {
  return useQuery({
    queryKey: ['runs', 'list'],
    queryFn: () => apiFetchJson<Run[]>('/runs'),
  });
}

export function RunsListPage() {
  const navigate = useNavigate();
  const { data: runs, isLoading } = useRuns();

  const handleViewLogs = (runId: number) => {
    navigate({
        to: '/runs/$runId',
        params: { runId: String(runId) }
    });
  };

  const handleViewArtifacts = (runId: number) => {
      // TODO: Implement specific artifacts view
      navigate({
          to: '/runs/$runId',
          params: { runId: String(runId) }
      });
  };

  const columns: Column<Run>[] = [
    {
      header: 'Run ID',
      accessorKey: 'run_id',
      cell: (run: Run) => (
        <span className="font-mono text-xs text-fg">#{run.run_id}</span>
      ),
      className: 'w-24',
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (run: Run) => <StatusPill status={run.status} />,
      className: 'w-32',
    },
    {
      header: 'Timing',
      cell: (run: Run) => (
         <div className="flex flex-col text-xs text-fg-muted">
             <span className="flex items-center gap-1">
                 <Clock className="h-3 w-3" />
                 {new Date(run.created_at).toLocaleString()}
             </span>
             {run.completed_at && (
                 <span className="opacity-70 mt-0.5">
                    Duration: {Math.round((new Date(run.completed_at).getTime() - new Date(run.created_at).getTime()) / 1000)}s
                 </span>
             )}
         </div>
      ),
    },
    {
      header: 'Context',
      cell: (run: Run) => (
        <div className="text-xs text-fg-muted space-y-0.5">
            {run.project_id && <div>Project: <span className="text-fg font-medium">#{run.project_id}</span></div>}
            {run.protocol_id && <div>Protocol: <span className="text-fg font-medium">#{run.protocol_id}</span></div>}
        </div>
      )
    },
    {
      header: 'Actions',
      cell: (run: Run) => (
        <div className="flex items-center gap-2 justify-end">
          <Button 
            onClick={() => handleViewLogs(run.run_id)} 
            size="tiny" 
            variant="ghost"
            className="text-fg-muted hover:text-fg"
          >
            <Terminal className="h-3 w-3 mr-1.5" />
            Logs
          </Button>
          <Button 
            onClick={() => handleViewArtifacts(run.run_id)} 
            size="tiny" 
            variant="ghost"
            className="text-fg-muted hover:text-fg"
          >
            <Box className="h-3 w-3 mr-1.5" />
            Artifacts
          </Button>
        </div>
      ),
      className: 'w-48 text-right',
    },
  ];

  if (isLoading) {
    return <LoadingState message="Loading runs..." />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-fg">Run History</h1>
        <p className="text-fg-muted mt-2 text-lg">Monitor execution progress, debug logs, and inspect artifacts.</p>
      </div>

      {runs && runs.length > 0 ? (
        <div className="rounded-xl border border-border bg-bg-panel shadow-sm overflow-hidden">
             <DataTable
              data={runs}
              columns={columns}
              emptyMessage="No runs recorded yet"
            />
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border bg-bg-muted/30 p-12 text-center">
            <EmptyState
              title="No runs found"
              description="Start a protocol execution to see it appear here."
              icon={<Activity className="h-12 w-12 text-fg-muted opacity-20" />}
            />
        </div>
      )}
    </div>
  );
}
