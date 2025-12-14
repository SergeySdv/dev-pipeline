import { cn } from '@/lib/cn';

interface OnboardingStage {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  description?: string;
  started_at?: string;
  finished_at?: string;
  error?: string;
}

interface OnboardingStagesProps {
  stages: OnboardingStage[];
  className?: string;
}

export function OnboardingStages({ stages, className }: OnboardingStagesProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500';
      case 'running': return 'bg-blue-500';
      case 'failed': return 'bg-red-500';
      case 'skipped': return 'bg-gray-400';
      default: return 'bg-gray-300';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✓';
      case 'running': return '⟳';
      case 'failed': return '✗';
      case 'skipped': return '⊘';
      default: return '○';
    }
  };

  return (
    <div className={cn('space-y-4', className)}>
      {stages.map((stage, index) => (
        <div key={stage.name} className="flex items-start gap-3">
          <div className="flex flex-col items-center">
            <div className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium',
              getStatusColor(stage.status)
            )}>
              {getStatusIcon(stage.status)}
            </div>
            {index < stages.length - 1 && (
              <div className="w-px h-8 bg-gray-200 mt-2" />
            )}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-medium text-gray-900">{stage.name}</h4>
              <span className={cn(
                'text-xs px-2 py-0.5 rounded',
                stage.status === 'running' ? 'bg-blue-100 text-blue-700' :
                stage.status === 'completed' ? 'bg-green-100 text-green-700' :
                stage.status === 'failed' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-700'
              )}>
                {stage.status}
              </span>
            </div>
            
            {stage.description && (
              <p className="text-sm text-gray-600 mb-2">{stage.description}</p>
            )}
            
            {stage.error && (
              <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                {stage.error}
              </div>
            )}
            
            <div className="flex items-center gap-4 text-xs text-gray-500">
              {stage.started_at && (
                <span>Started: {new Date(stage.started_at).toLocaleString()}</span>
              )}
              {stage.finished_at && (
                <span>Finished: {new Date(stage.finished_at).toLocaleString()}</span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}