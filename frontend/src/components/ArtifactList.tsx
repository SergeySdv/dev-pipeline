import { Button } from '@/components/ui/Button';
import { CodeBlock } from '@/components/ui/CodeBlock';
import { DataTable, ColumnDef } from '@/components/DataTable';
import { cn } from '@/lib/cn';

interface RunArtifact {
  id: string;
  name: string;
  kind: string;
  path: string;
  sha256: string;
  bytes: number;
  created_at: string;
  content?: string;
}

interface ArtifactListProps {
  artifacts: RunArtifact[];
  onViewContent?: (artifact: RunArtifact) => void;
  className?: string;
}

export function ArtifactList({ artifacts, onViewContent, className }: ArtifactListProps) {
  const columns: ColumnDef<RunArtifact>[] = [
    {
      key: 'name',
      header: 'Name',
    },
    {
      key: 'kind',
      header: 'Kind',
      className: 'w-24',
    },
    {
      key: 'bytes',
      header: 'Size',
      cell: (bytes) => {
        if (!bytes) return '-';
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
          size /= 1024;
          unitIndex++;
        }
        return `${size.toFixed(1)} ${units[unitIndex]}`;
      },
      className: 'w-20 text-right',
    },
    {
      key: 'sha256',
      header: 'SHA256',
      cell: (sha256) => (
        <span className="font-mono text-xs">{sha256?.slice(0, 12)}...</span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      cell: (createdAt) => new Date(createdAt).toLocaleString(),
      className: 'w-32',
    },
    {
      key: 'actions',
      header: 'Actions',
      cell: (_, artifact) => (
        <div className="flex items-center gap-1">
          {onViewContent && (
            <Button 
              onClick={() => onViewContent(artifact)} 
              size="tiny" 
              variant="ghost"
            >
              View
            </Button>
          )}
        </div>
      ),
      className: 'w-20',
    },
  ];

  if (artifacts.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        No artifacts found
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      <DataTable
        data={artifacts}
        columns={columns}
        emptyMessage="No artifacts found"
      />
    </div>
  );
}

interface ArtifactContentModalProps {
  artifact: RunArtifact | null;
  onClose: () => void;
}

export function ArtifactContentModal({ artifact, onClose }: ArtifactContentModalProps) {
  if (!artifact) return null;

  const isText = artifact.kind === 'text' || artifact.name.endsWith('.txt') || artifact.name.endsWith('.json') || artifact.name.endsWith('.yaml') || artifact.name.endsWith('.yml');
  const isBinary = artifact.bytes > 1024 * 1024; // > 1MB

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-full max-w-4xl mx-4 max-h-[80vh] bg-white rounded-lg shadow-lg">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{artifact.name}</h2>
            <p className="text-sm text-gray-500">
              {artifact.kind} • {artifact.bytes?.toLocaleString()} bytes • {artifact.sha256?.slice(0, 12)}...
            </p>
          </div>
          <Button onClick={onClose} variant="ghost" size="small">
            Close
          </Button>
        </div>
        
        <div className="px-6 py-4 overflow-auto max-h-[60vh]">
          {artifact.content ? (
            isText ? (
              <CodeBlock code={artifact.content} language={artifact.name.endsWith('.json') ? 'json' : 'text'} />
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-4">Binary content - {artifact.bytes?.toLocaleString()} bytes</p>
                <Button variant="secondary" size="small">
                  Download
                </Button>
              </div>
            )
          ) : isBinary ? (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-4">Large binary file - {artifact.bytes?.toLocaleString()} bytes</p>
              <Button variant="secondary" size="small">
                Download
              </Button>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Content not loaded
            </div>
          )}
        </div>
      </div>
    </div>
  );
}