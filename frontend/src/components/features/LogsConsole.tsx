import * as React from 'react';
import { Download, Search, Trash2, Play, Pause, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { ScrollArea } from '@/components/ui/ScrollArea';

interface LogEntry {
    timestamp: string;
    level: 'info' | 'warn' | 'error' | 'debug';
    message: string;
    source?: string;
}

interface LogsConsoleProps {
    logs: LogEntry[];
    title?: string;
    className?: string;
    onClear?: () => void;
    onDownload?: () => void;
    autoScroll?: boolean;
    maxHeight?: string;
}

export function LogsConsole({
    logs,
    title = 'Logs',
    className,
    onClear,
    onDownload,
    autoScroll = true,
    maxHeight = '500px',
}: LogsConsoleProps) {
    const [filter, setFilter] = React.useState('');
    const [levelFilter, setLevelFilter] = React.useState<LogEntry['level'] | 'all'>('all');
    const [isAutoScrollEnabled, setIsAutoScrollEnabled] = React.useState(autoScroll);
    const [isCollapsed, setIsCollapsed] = React.useState(false);
    const scrollRef = React.useRef<HTMLDivElement>(null);

    const filteredLogs = React.useMemo(() => {
        return logs.filter((log) => {
            const matchesText = filter === '' || log.message.toLowerCase().includes(filter.toLowerCase());
            const matchesLevel = levelFilter === 'all' || log.level === levelFilter;
            return matchesText && matchesLevel;
        });
    }, [logs, filter, levelFilter]);

    React.useEffect(() => {
        if (isAutoScrollEnabled && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [filteredLogs, isAutoScrollEnabled]);

    const getLevelColor = (level: LogEntry['level']) => {
        switch (level) {
            case 'error':
                return 'text-red-500';
            case 'warn':
                return 'text-yellow-500';
            case 'debug':
                return 'text-gray-400';
            default:
                return 'text-foreground';
        }
    };

    const getLevelBadgeVariant = (level: LogEntry['level']) => {
        switch (level) {
            case 'error':
                return 'destructive';
            case 'warn':
                return 'secondary';
            default:
                return 'outline';
        }
    };

    return (
        <div className={cn('border border-border rounded-lg overflow-hidden bg-background', className)}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30">
                <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">{title}</span>
                    <Badge variant="outline" className="text-xs">
                        {filteredLogs.length} entries
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setIsAutoScrollEnabled(!isAutoScrollEnabled)}
                        title={isAutoScrollEnabled ? 'Pause auto-scroll' : 'Resume auto-scroll'}
                    >
                        {isAutoScrollEnabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                    </Button>
                    {onDownload && (
                        <Button variant="ghost" size="icon" onClick={onDownload} title="Download logs">
                            <Download className="h-4 w-4" />
                        </Button>
                    )}
                    {onClear && (
                        <Button variant="ghost" size="icon" onClick={onClear} title="Clear logs">
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    )}
                    <Button variant="ghost" size="icon" onClick={() => setIsCollapsed(!isCollapsed)}>
                        {isCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
                    </Button>
                </div>
            </div>

            {!isCollapsed && (
                <>
                    {/* Filters */}
                    <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-muted/20">
                        <div className="relative flex-1 max-w-xs">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Filter logs..."
                                value={filter}
                                onChange={(e) => setFilter(e.target.value)}
                                className="pl-10 h-8 text-sm"
                            />
                        </div>
                        <div className="flex gap-1">
                            {(['all', 'info', 'warn', 'error', 'debug'] as const).map((level) => (
                                <Button
                                    key={level}
                                    variant={levelFilter === level ? 'default' : 'ghost'}
                                    size="sm"
                                    onClick={() => setLevelFilter(level)}
                                    className="text-xs h-7 px-2"
                                >
                                    {level.toUpperCase()}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* Log Content */}
                    <div
                        ref={scrollRef}
                        className="overflow-auto font-mono text-xs"
                        style={{ maxHeight }}
                    >
                        {filteredLogs.length === 0 ? (
                            <div className="flex items-center justify-center h-32 text-muted-foreground">
                                No logs to display
                            </div>
                        ) : (
                            <table className="w-full">
                                <tbody>
                                    {filteredLogs.map((log, idx) => (
                                        <tr key={idx} className="hover:bg-muted/30 border-b border-border/50 last:border-0">
                                            <td className="px-3 py-1.5 text-muted-foreground whitespace-nowrap w-36">
                                                {log.timestamp}
                                            </td>
                                            <td className="px-2 py-1.5 w-16">
                                                <Badge variant={getLevelBadgeVariant(log.level)} className="text-[10px] px-1.5 py-0">
                                                    {log.level.toUpperCase()}
                                                </Badge>
                                            </td>
                                            {log.source && (
                                                <td className="px-2 py-1.5 text-muted-foreground whitespace-nowrap w-24">
                                                    [{log.source}]
                                                </td>
                                            )}
                                            <td className={cn('px-2 py-1.5', getLevelColor(log.level))}>
                                                <pre className="whitespace-pre-wrap break-all">{log.message}</pre>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
