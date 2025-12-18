import { StatusPill } from '@/components/ui/StatusPill';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';

interface Protocol {
  id: number;
  protocol_name: string;
  project_id: number;
  project_name: string;
  status: string;
  base_branch: string;
  spec_hash?: string;
  spec_validation_status?: string;
  policy_pack_key?: string;
  policy_pack_version?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

interface ProtocolHeaderProps {
  protocol: Protocol;
  onStart?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onCancel?: () => void;
  onRunNextStep?: () => void;
  onRetryLatest?: () => void;
  onOpenPR?: () => void;
  className?: string;
}

export function ProtocolHeader({ 
  protocol, 
  onStart,
  onPause, 
  onResume, 
  onCancel,
  onRunNextStep,
  onRetryLatest,
  onOpenPR,
  className 
}: ProtocolHeaderProps) {
  const isActive = ['running', 'paused', 'blocked'].includes(protocol.status);
  const canStart = ['pending', 'planned'].includes(protocol.status);
  const canPause = protocol.status === 'running';
  const canResume = protocol.status === 'paused';
  const canCancel = !['completed', 'cancelled'].includes(protocol.status);

  return (
    <div className={cn('border-b border-gray-200 pb-4', className)}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 mb-2">
            {protocol.protocol_name}
          </h1>
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span>Project: {protocol.project_name}</span>
            <span>Branch: {protocol.base_branch}</span>
            <StatusPill status={protocol.status} />
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {protocol.spec_hash && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
              ✓ valid ({protocol.spec_hash.slice(0, 8)})
            </span>
          )}
          {protocol.policy_pack_key && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
              {protocol.policy_pack_key}@{protocol.policy_pack_version || 'latest'}
            </span>
          )}
        </div>
      </div>
      
      {protocol.description && (
        <p className="text-gray-600 mb-4">{protocol.description}</p>
      )}
      
      <div className="flex items-center gap-2 flex-wrap">
        {canStart && onStart && (
          <Button onClick={onStart} variant="primary" size="small">
            Start
          </Button>
        )}
        {canPause && onPause && (
          <Button onClick={onPause} variant="secondary" size="small">
            Pause
          </Button>
        )}
        {canResume && onResume && (
          <Button onClick={onResume} variant="primary" size="small">
            Resume
          </Button>
        )}
        {canCancel && onCancel && (
          <Button onClick={onCancel} variant="danger" size="small">
            Cancel
          </Button>
        )}
        {isActive && onRunNextStep && (
          <Button onClick={onRunNextStep} variant="secondary" size="small">
            Run Next Step
          </Button>
        )}
        {isActive && onRetryLatest && (
          <Button onClick={onRetryLatest} variant="secondary" size="small">
            Retry Latest
          </Button>
        )}
        {protocol.status === 'completed' && onOpenPR && (
          <Button onClick={onOpenPR} variant="primary" size="small">
            Open PR
          </Button>
        )}
      </div>
    </div>
  );
}