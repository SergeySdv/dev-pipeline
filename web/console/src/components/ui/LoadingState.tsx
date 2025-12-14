import { cn } from '@/lib/cn';

interface LoadingStateProps {
  className?: string;
  message?: string;
}

export function LoadingState({ className, message = 'Loading...' }: LoadingStateProps) {
  return (
    <div className={cn('flex items-center justify-center py-8', className)}>
      <div className="flex items-center gap-2 text-gray-500">
        <span className="animate-spin text-lg">⟳</span>
        <span className="text-sm">{message}</span>
      </div>
    </div>
  );
}

interface SkeletonProps {
  className?: string;
  lines?: number;
}

export function Skeleton({ className, lines = 1 }: SkeletonProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 w-full animate-pulse rounded bg-gray-200"
          style={{ width: i === lines - 1 ? '75%' : '100%' }}
        />
      ))}
    </div>
  );
}