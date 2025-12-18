import { cn } from '@/lib/cn';

interface QueueStats {
  queue: string;
  queued: number;
  started: number;
  failed: number;
  total: number;
  healthy_percentage: number;
}

interface QueueStatsCardProps {
  stats: QueueStats[];
  className?: string;
}

export function QueueStatsCard({ stats, className }: QueueStatsCardProps) {
  const getHealthColor = (percentage: number) => {
    if (percentage >= 80) return 'bg-green-500';
    if (percentage >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getHealthText = (percentage: number) => {
    if (percentage >= 80) return 'healthy';
    if (percentage >= 60) return 'degraded';
    return 'unhealthy';
  };

  return (
    <div className={cn('space-y-4', className)}>
      {stats.map((stat) => (
        <div key={stat.queue} className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-gray-900">{stat.queue}</h3>
            <div className="flex items-center gap-2">
              <span className={cn(
                'text-xs px-2 py-1 rounded',
                stat.healthy_percentage >= 80 ? 'bg-green-100 text-green-700' :
                stat.healthy_percentage >= 60 ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              )}>
                {getHealthText(stat.healthy_percentage)}
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-4 gap-4 text-sm mb-3">
            <div>
              <span className="text-gray-500">Queued</span>
              <div className="font-medium text-gray-900">{stat.queued}</div>
            </div>
            <div>
              <span className="text-gray-500">Started</span>
              <div className="font-medium text-blue-600">{stat.started}</div>
            </div>
            <div>
              <span className="text-gray-500">Failed</span>
              <div className="font-medium text-red-600">{stat.failed}</div>
            </div>
            <div>
              <span className="text-gray-500">Total</span>
              <div className="font-medium text-gray-900">{stat.total}</div>
            </div>
          </div>
          
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Health</span>
              <span>{stat.healthy_percentage}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={cn('h-2 rounded-full transition-all', getHealthColor(stat.healthy_percentage))}
                style={{ width: `${stat.healthy_percentage}%` }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}