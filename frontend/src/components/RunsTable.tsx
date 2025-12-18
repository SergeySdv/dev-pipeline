import { StatusPill } from '@/components/ui/StatusPill';
import { Button } from '@/components/ui/Button';
import { DataTable, ColumnDef } from '@/components/DataTable';
import { cn } from '@/lib/cn';

interface CodexRun {
  run_id: string;
  job_type: string;
  run_kind: string;
  status: string;
  project_id?: number;
  protocol_run_id?: number;
  step_run_id?: number;
  attempt: number;
  worker_id?: string;
  queue: string;
  cost_tokens?: number;
  cost_cents?: number;
  started_at?: string;
  finished_at?: string;
  created_at: string;
}

interface RunsTableProps {
  runs: CodexRun[];
  onViewLogs?: (runId: string) => void;
  onViewArtifacts?: (runId: string) => void;
  className?: string;
}

export function RunsTable({ 
  runs, 
  onViewLogs, 
  onViewArtifacts,
  className 
}: RunsTableProps) {
  const columns: ColumnDef<CodexRun>[] = [
    {
      key: 'run_id',
      header: 'Run ID',
      cell: (runId) => (
        <span className="font-mono text-xs">{runId.slice(0, 12)}...</span>
      ),
    },
    {
      key: 'job_type',
      header: 'Job Type',
      className: 'w-32',
    },
    {
      key: 'run_kind',
      header: 'Kind',
      className: 'w-20',
    },
    {
      key: 'status',
      header: 'Status',
      cell: (status) => <StatusPill status={status} variant="small" />,
      className: 'w-24',
    },
    {
      key: 'cost_tokens',
      header: 'Tokens',
      cell: (tokens) => tokens?.toLocaleString() || '-',
      className: 'w-20 text-right',
    },
    {
      key: 'created_at',
      header: 'Created',
      cell: (createdAt) => {
        const date = new Date(createdAt);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 60) {
          return `${diffMins}m ago`;
        } else if (diffMins < 1440) {
          return `${Math.floor(diffMins / 60)}h ago`;
        } else {
          return date.toLocaleDateString();
        }
      },
      className: 'w-24',
    },
    {
      key: 'actions',
      header: 'Actions',
      cell: (_, run) => (
        <div className="flex items-center gap-1">
          {onViewLogs && (
            <Button 
              onClick={() => onViewLogs(run.run_id)} 
              size="tiny" 
              variant="ghost"
            >
              Logs
            </Button>
          )}
          {onViewArtifacts && (
            <Button 
              onClick={() => onViewArtifacts(run.run_id)} 
              size="tiny" 
              variant="ghost"
            >
              Artifacts
            </Button>
          )}
        </div>
      ),
      className: 'w-32',
    },
  ];

  return (
    <DataTable
      data={runs}
      columns={columns}
      className={className}
      emptyMessage="No runs found"
    />
  );
}