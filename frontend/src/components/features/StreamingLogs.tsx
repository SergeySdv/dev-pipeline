import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Play, Pause, Download, RefreshCw, Terminal } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { apiFetchJson } from '@/api/client';

interface StreamingLogsProps {
    runId: string | number;
    className?: string;
    autoStart?: boolean;
    pollInterval?: number;
}

interface LogTailResponse {
    chunk: string;
    next_offset: number;
}

export function StreamingLogs({
    runId,
    className,
    autoStart = true,
    pollInterval = 1000,
}: StreamingLogsProps) {
    const [buffer, setBuffer] = React.useState('');
    const [offset, setOffset] = React.useState(0);
    const [isStreaming, setIsStreaming] = React.useState(autoStart);
    const [connectionStatus, setConnectionStatus] = React.useState<'connected' | 'disconnected' | 'error'>('disconnected');
    const scrollRef = React.useRef<HTMLPreElement>(null);
    const offsetRef = React.useRef(offset);

    // Keep ref in sync
    React.useEffect(() => {
        offsetRef.current = offset;
    }, [offset]);

    // Initialize at end of log file
    React.useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const tail = await apiFetchJson<LogTailResponse>(`/codex/runs/${runId}/logs/tail?offset=999999999999`);
                if (cancelled) return;
                setOffset(tail.next_offset);
                offsetRef.current = tail.next_offset;
                setConnectionStatus('connected');
            } catch {
                setConnectionStatus('error');
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [runId]);

    // Polling loop
    React.useEffect(() => {
        if (!isStreaming) return;
        let cancelled = false;

        const tick = async () => {
            try {
                const tail = await apiFetchJson<LogTailResponse>(
                    `/codex/runs/${runId}/logs/tail?offset=${offsetRef.current}`
                );
                if (cancelled) return;
                if (tail.chunk) {
                    setBuffer((prev) => {
                        const next = prev + tail.chunk;
                        return next.length > 200_000 ? next.slice(next.length - 200_000) : next;
                    });
                }
                setOffset(tail.next_offset);
                offsetRef.current = tail.next_offset;
                setConnectionStatus('connected');
            } catch {
                setConnectionStatus('error');
            }
        };

        const id = window.setInterval(tick, pollInterval);
        void tick();

        return () => {
            cancelled = true;
            window.clearInterval(id);
        };
    }, [isStreaming, runId, pollInterval]);

    // Auto-scroll to bottom
    React.useEffect(() => {
        if (scrollRef.current && isStreaming) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [buffer, isStreaming]);

    const handleDownload = () => {
        const blob = new Blob([buffer], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `run-${runId}-logs.txt`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const handleClear = () => {
        setBuffer('');
    };

    const handleJumpToEnd = () => {
        setOffset(999999999999);
        offsetRef.current = 999999999999;
        setBuffer('');
        setIsStreaming(true);
    };

    return (
        <div className={cn('border border-border rounded-lg overflow-hidden', className)}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30">
                <div className="flex items-center gap-2">
                    <Terminal className="h-5 w-5" />
                    <span className="font-semibold text-sm">Live Logs</span>
                    <Badge
                        variant={connectionStatus === 'connected' ? 'default' : connectionStatus === 'error' ? 'destructive' : 'secondary'}
                        className="text-xs"
                    >
                        {connectionStatus}
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setIsStreaming(!isStreaming)}
                        title={isStreaming ? 'Pause streaming' : 'Resume streaming'}
                    >
                        {isStreaming ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                    </Button>
                    <Button variant="ghost" size="icon" onClick={handleJumpToEnd} title="Jump to end">
                        <RefreshCw className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={handleDownload} title="Download logs">
                        <Download className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Log Content */}
            <pre
                ref={scrollRef}
                className="bg-gray-900 text-gray-100 p-4 text-xs font-mono overflow-auto"
                style={{ maxHeight: '500px', minHeight: '200px' }}
            >
                {buffer || 'Waiting for logs...'}
            </pre>

            {/* Footer */}
            <div className="flex items-center justify-between px-4 py-2 border-t border-border bg-muted/20 text-xs text-muted-foreground">
                <span>Offset: {offset.toLocaleString()}</span>
                <span>{buffer.split('\n').length.toLocaleString()} lines</span>
            </div>
        </div>
    );
}
