import { cn } from '@/lib/cn';

interface StatusPillProps {
  status: string;
  variant?: 'default' | 'small';
  className?: string;
}

const statusConfig = {
  // Protocol statuses
  pending: { color: 'bg-gray-100 text-gray-700', icon: '○' },
  planning: { color: 'bg-blue-100 text-blue-700', icon: '⟳' },
  planned: { color: 'bg-blue-100 text-blue-700', icon: '✓' },
  running: { color: 'bg-blue-100 text-blue-700', icon: '▶' },
  paused: { color: 'bg-yellow-100 text-yellow-700', icon: '⏸' },
  blocked: { color: 'bg-red-100 text-red-700', icon: '⚠' },
  failed: { color: 'bg-red-100 text-red-700', icon: '✗' },
  cancelled: { color: 'bg-gray-100 text-gray-700', icon: '⊘' },
  completed: { color: 'bg-green-100 text-green-700', icon: '✓' },
  
  // Step statuses
  needs_qa: { color: 'bg-yellow-100 text-yellow-700', icon: '📋' },
  
  // Run statuses
  queued: { color: 'bg-gray-100 text-gray-700', icon: '⏰' },
  succeeded: { color: 'bg-green-100 text-green-700', icon: '✓' },
  
  // Default
  unknown: { color: 'bg-gray-100 text-gray-700', icon: '?' },
};

export function StatusPill({ status, variant = 'default', className }: StatusPillProps) {
  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.unknown;
  
  const sizeClasses = variant === 'small' 
    ? 'px-2 py-0.5 text-xs' 
    : 'px-3 py-1 text-sm';
  
  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded-full font-medium',
      sizeClasses,
      config.color,
      className
    )}>
      <span className="text-xs">{config.icon}</span>
      {status}
    </span>
  );
}