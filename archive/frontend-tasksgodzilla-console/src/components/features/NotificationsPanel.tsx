import * as React from 'react';
import { Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Bell, Check, Trash2, Settings, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ScrollArea } from '@/components/ui/ScrollArea';
import { Separator } from '@/components/ui/Separator';
import { apiFetchJson } from '@/api/client';

interface Notification {
    id: string;
    type: 'info' | 'success' | 'warning' | 'error';
    title: string;
    message: string;
    read: boolean;
    actionUrl?: string;
    actionLabel?: string;
    createdAt: string;
}

interface NotificationsPanelProps {
    className?: string;
    onSettingsClick?: () => void;
}

// Mock data generator until real notification API exists
function useMockNotifications() {
    return useQuery({
        queryKey: ['notifications'],
        queryFn: async (): Promise<Notification[]> => {
            // This would be replaced with actual API call
            return [
                {
                    id: '1',
                    type: 'success',
                    title: 'Protocol Completed',
                    message: 'Protocol run #42 completed successfully',
                    read: false,
                    actionUrl: '/protocols/42',
                    actionLabel: 'View',
                    createdAt: new Date(Date.now() - 5 * 60000).toISOString(),
                },
                {
                    id: '2',
                    type: 'error',
                    title: 'Run Failed',
                    message: 'Run #123 failed with exit code 1',
                    read: false,
                    actionUrl: '/runs/123',
                    actionLabel: 'Debug',
                    createdAt: new Date(Date.now() - 15 * 60000).toISOString(),
                },
                {
                    id: '3',
                    type: 'info',
                    title: 'New Project Onboarded',
                    message: 'Project "my-app" has been successfully onboarded',
                    read: true,
                    actionUrl: '/projects/1',
                    actionLabel: 'Open',
                    createdAt: new Date(Date.now() - 60 * 60000).toISOString(),
                },
            ];
        },
        staleTime: 30000,
    });
}

export function NotificationsPanel({ className, onSettingsClick }: NotificationsPanelProps) {
    const { data: notifications = [], isLoading } = useMockNotifications();
    const [localRead, setLocalRead] = React.useState<Set<string>>(new Set());

    const unreadCount = notifications.filter((n) => !n.read && !localRead.has(n.id)).length;

    const markAsRead = (id: string) => {
        setLocalRead((prev) => new Set([...prev, id]));
    };

    const markAllAsRead = () => {
        setLocalRead(new Set(notifications.map((n) => n.id)));
    };

    const getTypeStyles = (type: Notification['type']) => {
        switch (type) {
            case 'success':
                return 'border-l-green-500';
            case 'error':
                return 'border-l-red-500';
            case 'warning':
                return 'border-l-yellow-500';
            default:
                return 'border-l-blue-500';
        }
    };

    const formatTime = (dateStr: string) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        return date.toLocaleDateString();
    };

    return (
        <div className={cn('w-80 bg-background border border-border rounded-lg shadow-lg', className)}>
            <div className="flex items-center justify-between p-4 border-b border-border">
                <div className="flex items-center gap-2">
                    <Bell className="h-5 w-5" />
                    <span className="font-semibold">Notifications</span>
                    {unreadCount > 0 && (
                        <Badge variant="destructive" className="text-xs px-1.5">
                            {unreadCount}
                        </Badge>
                    )}
                </div>
                <div className="flex items-center gap-1">
                    {unreadCount > 0 && (
                        <Button variant="ghost" size="sm" onClick={markAllAsRead} title="Mark all as read">
                            <Check className="h-4 w-4" />
                        </Button>
                    )}
                    {onSettingsClick && (
                        <Button variant="ghost" size="sm" onClick={onSettingsClick} title="Notification settings">
                            <Settings className="h-4 w-4" />
                        </Button>
                    )}
                </div>
            </div>

            <ScrollArea className="h-[350px]">
                {isLoading ? (
                    <div className="flex items-center justify-center h-32 text-muted-foreground">Loading...</div>
                ) : notifications.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                        <Bell className="h-8 w-8 mb-2 opacity-20" />
                        <p>No notifications</p>
                    </div>
                ) : (
                    <div>
                        {notifications.map((notification, idx) => {
                            const isRead = notification.read || localRead.has(notification.id);
                            return (
                                <React.Fragment key={notification.id}>
                                    <div
                                        className={cn(
                                            'p-4 border-l-4 transition-colors',
                                            getTypeStyles(notification.type),
                                            !isRead && 'bg-muted/30'
                                        )}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="font-medium text-sm">{notification.title}</span>
                                                    {!isRead && <div className="h-2 w-2 rounded-full bg-primary" />}
                                                </div>
                                                <p className="text-sm text-muted-foreground line-clamp-2">{notification.message}</p>
                                                <div className="mt-2 flex items-center justify-between">
                                                    <span className="text-xs text-muted-foreground">{formatTime(notification.createdAt)}</span>
                                                    {notification.actionUrl && (
                                                        <Link
                                                            to={notification.actionUrl}
                                                            className="text-xs text-primary hover:underline flex items-center gap-1"
                                                            onClick={() => markAsRead(notification.id)}
                                                        >
                                                            {notification.actionLabel || 'View'}
                                                            <ExternalLink className="h-3 w-3" />
                                                        </Link>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    {idx < notifications.length - 1 && <Separator />}
                                </React.Fragment>
                            );
                        })}
                    </div>
                )}
            </ScrollArea>

            <div className="p-3 border-t border-border">
                <Link to="/settings" search={{ tab: 'preferences' }}>
                    <Button variant="ghost" size="sm" className="w-full text-muted-foreground">
                        Manage notification preferences
                    </Button>
                </Link>
            </div>
        </div>
    );
}
