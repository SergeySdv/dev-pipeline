import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from '@tanstack/react-router';
import { GitBranch, Clock, AlertCircle } from 'lucide-react';
import { apiFetchJson } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusPill } from '@/components/ui/StatusPill';
import { DataTable, ColumnDef } from '@/components/DataTable';

interface Protocol {
  id: number;
  project_id: number;
  protocol_name: string;
  status: string;
  base_branch: string;
  description?: string;
  created_at: string;
  updated_at: string;
  project_name?: string;
}

export function ProtocolsListPage() {
  const navigate = useNavigate();

  const { data: protocols, isLoading, error } = useQuery({
    queryKey: ['protocols', 'list'],
    queryFn: () => apiFetchJson<Protocol[]>('/protocols'),
  });

  const handleViewProtocol = (protocolId: number) => {
    navigate({ to: '/protocols/$protocolId', params: { protocolId: String(protocolId) } });
  };

  const handleCreateProtocol = () => {
    navigate({ to: '/protocols/new' });
  };

  if (isLoading) {
    return <LoadingState message="Loading protocols..." />;
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 mb-4">Failed to load protocols</p>
        <Button onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  const columns: ColumnDef<Protocol>[] = [
    {
      key: 'id',
      header: 'ID',
      cell: (id) => (
        <span className="font-mono text-xs text-fg-muted">#{id}</span>
      ),
      className: 'w-16',
    },
    {
      key: 'protocol_name',
      header: 'Protocol Name',
      cell: (name, row) => (
        <button
          onClick={() => handleViewProtocol(row.id)}
          className="text-left hover:underline"
        >
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-fg-muted" />
            <span className="font-medium text-fg">{name}</span>
          </div>
          {row.description && (
            <p className="mt-1 text-xs text-fg-muted line-clamp-1">{row.description}</p>
          )}
        </button>
      ),
    },
    {
      key: 'project_id',
      header: 'Project',
      cell: (projectId, row) => (
        <Link
          to="/projects/$projectId"
          params={{ projectId: String(projectId) }}
          className="text-sm text-blue-600 hover:underline"
        >
          {row.project_name || `Project #${projectId}`}
        </Link>
      ),
      className: 'w-40',
    },
    {
      key: 'status',
      header: 'Status',
      cell: (status) => <StatusPill status={status} />,
      className: 'w-32',
    },
    {
      key: 'base_branch',
      header: 'Base Branch',
      cell: (branch) => (
        <span className="font-mono text-xs text-fg-muted">{branch}</span>
      ),
      className: 'w-32',
    },
    {
      key: 'created_at',
      header: 'Created',
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
          <h1 className="text-2xl font-semibold text-gray-900">Protocols</h1>
          <p className="text-gray-600">All protocol runs across projects</p>
        </div>
        <Button onClick={handleCreateProtocol} variant="primary">
          Create Protocol
        </Button>
      </div>

      {protocols && protocols.length > 0 ? (
        <>
          <div className="flex gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-fg-muted">Total:</span>
              <span className="font-medium text-fg">{protocols.length}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-fg-muted">Running:</span>
              <span className="font-medium text-green-600">
                {protocols.filter((p) => p.status === 'running').length}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-fg-muted">Completed:</span>
              <span className="font-medium text-blue-600">
                {protocols.filter((p) => p.status === 'completed').length}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-fg-muted">Failed:</span>
              <span className="font-medium text-red-600">
                {protocols.filter((p) => p.status === 'failed').length}
              </span>
            </div>
          </div>
          <DataTable columns={columns} data={protocols} />
        </>
      ) : (
        <EmptyState
          title="No protocols yet"
          description="Create a protocol to start automating development tasks."
          action={
            <Button onClick={handleCreateProtocol} variant="primary">
              Create Protocol
            </Button>
          }
        />
      )}
    </div>
  );
}
