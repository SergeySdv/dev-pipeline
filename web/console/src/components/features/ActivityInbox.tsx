import * as React from 'react';
import { Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Bell, ExternalLink, X, Filter } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ScrollArea } from '@/components/ui/ScrollArea';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { apiFetchJson } from '@/api/client';

interface ActivityEvent {
    id: number;
    event_type: string;
    message: string;
    protocol_run_id?: number;
    project_id?: number;
    created_at: string;
}

interface ActivityInboxProps {
    maxItems?: number;
    className?: string;
    onClose?: () => void;
}

export function ActivityInbox({ maxItems = 20, className, onClose }: ActivityInboxProps) {
    const [filter, setFilter] = React.useState<'all' | 'errors' | 'protocols' | 'projects'>('all');

    const { data: events, isLoading } = useQuery({
        queryKey: ['activity', 'inbox', maxItems],
        queryFn: () => apiFetchJson<ActivityEvent[]>(`/events?limit=${maxItems}`),
        refetchInterval: 30000,
    });

    const filteredEvents = React.useMemo(() => {
        if (!events) return [];
        switch (filter) {
            case 'errors':
                return events.filter((e) => e.event_type.includes('error') || e.event_type.includes('fail'));
            case 'protocols':
                return events.filter((e) => e.protocol_run_id != null);
            case 'projects':
                return events.filter((e) => e.project_id != null);
            default:
                return events;
        }
    }, [events, filter]);

    const getEventBadgeVariant = (eventType: string) => {
        if (eventType.includes('error') || eventType.includes('fail')) return 'destructive';
        if (eventType.includes('success') || eventType.includes('complete')) return 'default';
        return 'secondary';
    };

    return (
        <Card className={cn('w-full max-w-md', className)}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle className="flex items-center gap-2 text-lg">
                    <Bell className="h-5 w-5" />
                    Activity Inbox
                </CardTitle>
                <div className="flex items-center gap-2">
                    <Button variant="ghost" size="icon" onClick={() => setFilter(filter === 'all' ? 'errors' : 'all')}>
                        <Filter className={cn('h-4 w-4', filter !== 'all' && 'text-primary')} />
                    </Button>
                    {onClose && (
                        <Button variant="ghost" size="icon" onClick={onClose}>
                            <X className="h-4 w-4" />
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent className="p-0">
                {filter !== 'all' && (
                    <div className="px-4 pb-2 flex gap-2">
                        {(['all', 'errors', 'protocols', 'projects'] as const).map((f) => (
                            <Button
                                key={f}
                                variant={filter === f ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => setFilter(f)}
                                className="text-xs"
                            >
                                {f.charAt(0).toUpperCase() + f.slice(1)}
                            </Button>
                        ))}
                    </div>
                )}
                <ScrollArea className="h-[400px]">
                    {isLoading ? (
                        <div className="flex items-center justify-center h-32 text-muted-foreground">Loading...</div>
                    ) : filteredEvents.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                            <Bell className="h-8 w-8 mb-2 opacity-20" />
                            <p>No activity yet</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-border">
                            {filteredEvents.map((event) => (
                                <div key={event.id} className="p-4 hover:bg-muted/50 transition-colors">
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <Badge variant={getEventBadgeVariant(event.event_type)} className="text-xs">
                                                    {event.event_type}
                                                </Badge>
                                                <span className="text-xs text-muted-foreground">
                                                    {new Date(event.created_at).toLocaleTimeString()}
                                                </span>
                                            </div>
                                            <p className="text-sm text-foreground line-clamp-2">{event.message}</p>
                                            <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                                                {event.project_id && (
                                                    <Link
                                                        to="/projects/$projectId"
                                                        params={{ projectId: String(event.project_id) }}
                                                        className="flex items-center gap-1 hover:text-foreground"
                                                    >
                                                        Project #{event.project_id}
                                                        <ExternalLink className="h-3 w-3" />
                                                    </Link>
                                                )}
                                                {event.protocol_run_id && (
                                                    <Link
                                                        to="/protocols/$protocolId"
                                                        params={{ protocolId: String(event.protocol_run_id) }}
                                                        className="flex items-center gap-1 hover:text-foreground"
                                                    >
                                                        Protocol #{event.protocol_run_id}
                                                        <ExternalLink className="h-3 w-3" />
                                                    </Link>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
