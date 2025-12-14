import React from 'react';
import { CodeBlock } from '@/components/ui/CodeBlock';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';

interface LogViewerProps {
  logs: string;
  className?: string;
  maxHeight?: string;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export function LogViewer({ 
  logs, 
  className, 
  maxHeight = '400px',
  onRefresh,
  isRefreshing = false
}: LogViewerProps) {
  const [autoScroll, setAutoScroll] = React.useState(true);
  const logContainerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleScroll = () => {
    if (logContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = logContainerRef.current;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
      setAutoScroll(isAtBottom);
    }
  };

  return (
    <div className={cn('border border-gray-200 rounded-lg overflow-hidden', className)}>
      <div className="flex items-center justify-between bg-gray-50 px-4 py-2 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Logs</span>
          {autoScroll && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
              auto-scroll
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setAutoScroll(!autoScroll)}
            size="tiny"
            variant="ghost"
          >
            {autoScroll ? 'Stop Scroll' : 'Auto Scroll'}
          </Button>
          {onRefresh && (
            <Button
              onClick={onRefresh}
              size="tiny"
              variant="ghost"
              loading={isRefreshing}
            >
              Refresh
            </Button>
          )}
        </div>
      </div>
      
      <div
        ref={logContainerRef}
        className="overflow-auto bg-gray-900 text-gray-100 p-4 font-mono text-sm"
        style={{ maxHeight }}
        onScroll={handleScroll}
      >
        <pre className="whitespace-pre-wrap">{logs || 'No logs available'}</pre>
      </div>
    </div>
  );
}