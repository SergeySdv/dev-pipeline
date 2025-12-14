import { cn } from '@/lib/cn';

interface EventRow {
  id: string;
  timestamp: string;
  event_type: string;
  message: string;
  metadata?: Record<string, any>;
  project_name?: string;
  protocol_name?: string;
}

interface EventRowProps {
  event: EventRow;
  className?: string;
}

export function EventRow({ event, className }: EventRowProps) {
  const getEventTypeColor = (eventType: string) => {
    if (eventType.includes('error') || eventType.includes('failed')) return 'text-red-600 bg-red-50';
    if (eventType.includes('completed') || eventType.includes('success')) return 'text-green-600 bg-green-50';
    if (eventType.includes('started') || eventType.includes('enqueued')) return 'text-blue-600 bg-blue-50';
    return 'text-gray-600 bg-gray-50';
  };

  return (
    <div className={cn('border-b border-gray-100 py-3', className)}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-16 text-xs text-gray-500">
          {new Date(event.timestamp).toLocaleTimeString()}
        </div>
        
        <div className="flex-shrink-0">
          <span className={cn(
            'text-xs px-2 py-1 rounded font-medium',
            getEventTypeColor(event.event_type)
          )}>
            {event.event_type}
          </span>
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="text-sm text-gray-900 mb-1">{event.message}</div>
          
          <div className="flex items-center gap-4 text-xs text-gray-500">
            {event.project_name && (
              <span>Project: {event.project_name}</span>
            )}
            {event.protocol_name && (
              <span>Protocol: {event.protocol_name}</span>
            )}
          </div>
          
          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                Details
              </summary>
              <div className="mt-1">
                <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-32">
                  {JSON.stringify(event.metadata, null, 2)}
                </pre>
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}

interface EventTimelineProps {
  events: EventRow[];
  className?: string;
}

export function EventTimeline({ events, className }: EventTimelineProps) {
  if (events.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        No events found
      </div>
    );
  }

  return (
    <div className={cn('divide-y divide-gray-100', className)}>
      {events.map((event) => (
        <EventRow key={event.id} event={event} />
      ))}
    </div>
  );
}