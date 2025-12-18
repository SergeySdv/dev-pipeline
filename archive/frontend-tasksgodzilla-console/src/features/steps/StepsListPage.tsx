import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from '@tanstack/react-router';
import { ListChecks, Clock, GitBranch } from 'lucide-react';
import { apiFetchJson } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusPill } from '@/components/ui/StatusPill';
import { DataTable, ColumnDef } from '@/components/DataTable';

interface Step {
  id: number;
  protocol_run_id: number;
  step_index: number;
  step_name: string;
  step_type: string;
  status: string;
  retries: number;
  model?: string;
  engine_id?: string;
  summary?: string;
  created_at: string;
  updated_at: string;
  protocol_name?: string;
  project_id?: number;
}

export function StepsListPage() {
  const navigate = useNavigate();

  const { data: steps, isLoading, error } = useQuery({
    queryKey: ['steps', 'list'],
    queryFn: () => apiFetchJson<Step[]>('/steps'),
  });

  const handleViewStep = (stepId: number) => {
    navigate({ to: '/steps/$stepId', params: { stepId: String(stepId) } });
  };

  if (isLoading) {
    return <LoadingState message="Loading steps..." />;
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 mb-4">Failed to load steps</p>
        <Button onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  const columns: ColumnDef<Step>[] = [
    {
      key: 'id',
      header: 'ID',
      cell: (id) => (
        <span className="font-mono text-xs text-fg-muted">#{id}</span>
      ),
      className: 'w-16',
    },
    {
      key: 'step_name',
      header: 'Step Name',
      cell: (name, row) => (
        <button
          onClick={() => handleViewStep(row.id)}
          className="text-left hover:underline"
        >
          <div className="flex items-center gap-2">
            <ListChecks className="h-4 w-4 text-fg-muted" />
            <div>
              <div className="font-medium text-fg">
                {row.step_index + 1}. {name}
              </div>
              {row.summary && (
                <p className="mt-1 text-xs text-fg-muted line-clamp-1">{row.summary}</p>
              )}
            </div>
          </div>
        </button>
      ),
    },
    {
      key: 'protocol_run_id',
      header: 'Protocol',
      cell: (protocolId, row) => (
        <Link
          to="/protocols/$protocolId"
          params={{ protocolId: String(protocolId) }}
          className="flex items-center gap-1 text-sm text-blue-600 hover:underline"
        >
          <GitBranch className="h-3 w-3" />
          <span>{row.protocol_name || `#${protocolId}`}</span>
        </Link>
      ),
      className: 'w-48',
    },
    {
      key: 'status',
      header: 'Status',
      cell: (status) => <StatusPill status={status} />,
      className: 'w-32',
    },
    {
      key: 'step_type',
      header: 'Type',
      cell: (type) => (
        <span className="rounded bg-bg-muted px-2 py-1 text-xs font-medium text-fg-muted">
          {type}
        </span>
      ),
      className: 'w-24',
    },
    {
      key: 'retries',
      header: 'Retries',
      cell: (retries) => (
        <span className={`text-sm font-medium ${retries > 0 ? 'text-orange-600' : 'text-fg-muted'}`}>
          {retries}
        </span>
      ),
      className: 'w-20',
    },
    {
      key: 'engine_id',
      header: 'Engine',
      cell: (engine) => (
        <span className="font-mono text-xs text-fg-muted">{engine || 'N/A'}</span>
      ),
      className: 'w-24',
    },
    {
      key: 'updated_at',
      header: 'Updated',
      cell: (date) => (
        <div className="flex items-center gap-1 text-xs text-fg-muted">
          <Clock className="h-3 w-3" />
          <span>{new Date(date).toLocaleDateString()}</span>
        </div>
      ),
      className: 'w-32',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Steps</h1>
          <p className="text-gray-600">All step runs across protocols</p>
        </div>
      </div>

      {steps && steps.length > 0 ? (
        <>
          <div className="flex gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-fg-muted">Total:</span>
              <span className="font-medium text-fg">{steps.length}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-fg-muted">Pending:</span>
              <span className="font-medium text-gray-600">
                {steps.filter((s) => s.status === 'pending').length}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-fg-muted">Running:</span>
              <span className="font-medium text-green-600">
                {steps.filter((s) => s.status === 'running').length}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-fg-muted">Completed:</span>
              <span className="font-medium text-blue-600">
                {steps.filter((s) => s.status === 'completed').length}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-fg-muted">Failed:</span>
              <span className="font-medium text-red-600">
                {steps.filter((s) => s.status === 'failed').length}
              </span>
            </div>
          </div>
          <DataTable columns={columns} data={steps} />
        </>
      ) : (
        <EmptyState
          title="No steps yet"
          description="Steps will appear here when protocols start executing."
        />
      )}
    </div>
  );
}
