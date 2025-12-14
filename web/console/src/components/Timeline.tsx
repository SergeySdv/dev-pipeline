import { cn } from '@/lib/cn';

interface TimelineProps {
  events: TimelineEvent[];
  className?: string;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  type: string;
  title: string;
  description?: string;
  metadata?: Record<string, any>;
}

export function Timeline({ events, className }: TimelineProps) {
  return (
    <div className={cn('space-y-4', className)}>
      {events.map((event, index) => (
        <div key={event.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="w-2 h-2 bg-blue-500 rounded-full" />
            {index < events.length - 1 && (
              <div className="w-px h-full bg-gray-200 mt-1" />
            )}
          </div>
          <div className="flex-1 pb-4">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span>{new Date(event.timestamp).toLocaleTimeString()}</span>
              <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{event.type}</span>
            </div>
            <h4 className="font-medium text-gray-900 mt-1">{event.title}</h4>
            {event.description && (
              <p className="text-sm text-gray-600 mt-1">{event.description}</p>
            )}
            {event.metadata && Object.keys(event.metadata).length > 0 && (
              <details className="mt-2">
                <summary className="text-xs text-gray-500 cursor-pointer">Details</summary>
                <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-auto">
                  {JSON.stringify(event.metadata, null, 2)}
                </pre>
              </details>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}