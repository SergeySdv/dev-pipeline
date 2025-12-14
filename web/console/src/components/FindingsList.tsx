import { cn } from '@/lib/cn';

interface PolicyFinding {
  code: string;
  message: string;
  severity: 'warning' | 'error';
  suggestion?: string;
  location?: string;
}

interface FindingsListProps {
  findings: PolicyFinding[];
  className?: string;
}

export function FindingsList({ findings, className }: FindingsListProps) {
  if (findings.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        No policy findings found
      </div>
    );
  }

  const getSeverityIcon = (severity: string) => {
    return severity === 'error' ? '⚠️' : '⚡';
  };

  const getSeverityColor = (severity: string) => {
    return severity === 'error' 
      ? 'text-red-600 bg-red-50 border-red-200' 
      : 'text-yellow-600 bg-yellow-50 border-yellow-200';
  };

  return (
    <div className={cn('space-y-3', className)}>
      {findings.map((finding, index) => (
        <div
          key={index}
          className={cn(
            'border rounded-lg p-4',
            getSeverityColor(finding.severity)
          )}
        >
          <div className="flex items-start gap-3">
            <span className="text-lg">{getSeverityIcon(finding.severity)}</span>
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-medium">{finding.code}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-white/50">
                  {finding.severity}
                </span>
              </div>
              
              <div className="text-sm">{finding.message}</div>
              
              {finding.location && (
                <div className="text-xs text-gray-600">
                  Location: {finding.location}
                </div>
              )}
              
              {finding.suggestion && (
                <div className="text-sm bg-white/50 p-2 rounded">
                  <span className="font-medium">Suggested fix:</span> {finding.suggestion}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}