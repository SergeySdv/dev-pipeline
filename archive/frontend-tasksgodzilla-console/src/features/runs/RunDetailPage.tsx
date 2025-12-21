import { useParams } from '@tanstack/react-router';
import React from 'react';
import { useQuery } from '@tanstack/react-query';

import { apiFetchJson } from '@/api/client';
import { loadSettings } from '@/app/settings/store';
import { type LogTailResponse } from '@/api/types';
import { useSettingsSnapshot } from '@/app/settings/store';
import { useDocumentVisible } from '@/app/polling';

export function RunDetailPage() {
  const { runId } = useParams({ from: '/runs/$runId' });
  const apiBaseFromEnv = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
  const apiBase = (loadSettings().api.apiBase || apiBaseFromEnv).replace(/\/$/, '');
  const settings = useSettingsSnapshot();
  const visible = useDocumentVisible();

  const run = useQuery({
    queryKey: ['runs', 'detail', runId],
    queryFn: async () => await apiFetchJson<Record<string, unknown>>(`/codex/runs/${runId}`),
    staleTime: 10_000,
    retry: 1,
  });

  const [follow, setFollow] = React.useState(true);
  const [streamMode, setStreamMode] = React.useState<'poll' | 'sse'>('poll');
  const followAllowed = follow && settings.polling.enabled && (!settings.polling.disableInBackground || visible);
  const [offset, setOffset] = React.useState<number>(0);
  const offsetRef = React.useRef<number>(0);
  const [buffer, setBuffer] = React.useState<string>('');
  const [filter, setFilter] = React.useState<string>('');

  React.useEffect(() => {
    offsetRef.current = offset;
  }, [offset]);

  // Initialize at end of file (best-effort) so opening a run feels like "tail -f".
  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const tail = await apiFetchJson<LogTailResponse>(`/codex/runs/${runId}/logs/tail?offset=999999999999`);
        if (cancelled) return;
        setOffset(tail.next_offset);
        offsetRef.current = tail.next_offset;
        setBuffer('');
      } catch {
        // If logs aren't ready yet, keep offset at 0 and wait for polling to pick up.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  React.useEffect(() => {
    if (!followAllowed || streamMode !== 'poll') return;
    let cancelled = false;
    const tick = async () => {
      try {
        const tail = await apiFetchJson<LogTailResponse>(`/codex/runs/${runId}/logs/tail?offset=${offsetRef.current}`);
        if (cancelled) return;
        if (tail.chunk) {
          setBuffer((prev) => {
            const next = prev + tail.chunk;
            // Keep memory bounded: retain last ~200k chars.
            return next.length > 200_000 ? next.slice(next.length - 200_000) : next;
          });
        }
        setOffset(tail.next_offset);
        offsetRef.current = tail.next_offset;
      } catch {
        // Best effort; transient failures shouldn't crash console.
      }
    };
    const id = window.setInterval(() => {
      void tick();
    }, 1000);
    void tick();
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [followAllowed, runId, streamMode]);

  React.useEffect(() => {
    if (!followAllowed || streamMode !== 'sse') return;
    let es: EventSource | null = null;
    try {
      // Note: native EventSource can't attach custom headers; this is intended for same-origin cookie auth.
      es = new EventSource(
        `${apiBase}/codex/runs/${encodeURIComponent(runId)}/logs/stream?offset=${offsetRef.current}&poll_interval_ms=1000`,
      );
      es.addEventListener('log', (ev) => {
        try {
          const data = JSON.parse((ev as MessageEvent).data) as LogTailResponse;
          if (data.chunk) {
            setBuffer((prev) => {
              const next = prev + data.chunk;
              return next.length > 200_000 ? next.slice(next.length - 200_000) : next;
            });
          }
          setOffset(data.next_offset);
          offsetRef.current = data.next_offset;
        } catch {
          // ignore
        }
      });
    } catch {
      // ignore
    }
    return () => {
      if (es) es.close();
    };
  }, [followAllowed, runId, streamMode, apiBase]);

  const displayed = React.useMemo(() => {
    if (!filter.trim()) return buffer;
    const needle = filter.trim().toLowerCase();
    return buffer
      .split('\n')
      .filter((l) => l.toLowerCase().includes(needle))
      .join('\n');
  }, [buffer, filter]);

  const runData = run.data as any;

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">
              Run: {runId}
            </h1>
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span>Job: {runData?.job_type || '...'}</span>
              <span>Kind: {runData?.run_kind || '...'}</span>
              <span className={`font-medium ${
                runData?.status === 'succeeded' ? 'text-green-600' :
                runData?.status === 'failed' ? 'text-red-600' :
                runData?.status === 'running' ? 'text-blue-600' :
                'text-gray-600'
              }`}>
                {runData?.status || '...'}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Queue:</span>
            <div className="font-medium">{runData?.queue || '...'}</div>
          </div>
          <div>
            <span className="text-gray-500">Attempt:</span>
            <div className="font-medium">{runData?.attempt || '...'}</div>
          </div>
          {runData?.worker_id && (
            <div>
              <span className="text-gray-500">Worker:</span>
              <div className="font-medium">{runData.worker_id}</div>
            </div>
          )}
          {runData?.cost_tokens && (
            <div>
              <span className="text-gray-500">Tokens:</span>
              <div className="font-medium">{runData.cost_tokens.toLocaleString()}</div>
            </div>
          )}
        </div>

        {runData?.started_at && (
          <div className="mt-4 text-sm text-gray-600">
            <span>Created: {new Date(runData.created_at).toLocaleString()}</span>
            {runData.finished_at && (
              <span className="ml-4">
                Finished: {new Date(runData.finished_at).toLocaleString()}
                {runData.started_at && (
                  <span className="ml-2">
                    ({Math.round((new Date(runData.finished_at).getTime() - new Date(runData.started_at).getTime()) / 1000 / 60)}m)
                  </span>
                )}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="rounded-md border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm font-medium">Logs console</div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} />
              <span>Follow</span>
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={streamMode === 'sse'}
                onChange={(e) => setStreamMode(e.target.checked ? 'sse' : 'poll')}
              />
              <span>Stream (SSE)</span>
            </label>
            <button
              type="button"
              className="rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm hover:bg-gray-100"
              onClick={() => setBuffer('')}
            >
              Clear
            </button>
            <button
              type="button"
              className="rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm hover:bg-gray-100"
              onClick={() => {
                setFollow(true);
                setOffset(999999999999);
                offsetRef.current = 999999999999;
              }}
            >
              Jump to end
            </button>
            <a
              className="rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm hover:bg-gray-100"
              href={`${apiBase}/codex/runs/${encodeURIComponent(runId)}/logs`}
              target="_blank"
              rel="noreferrer"
            >
              Download
            </a>
          </div>
        </div>

        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm">
            <span className="text-xs text-gray-500">Search (substring)</span>
            <input
              className="rounded-md border border-gray-300 bg-white px-3 py-2"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="error, Exception, job_id…"
            />
          </label>
          <div className="rounded-md border border-gray-300 bg-gray-50 p-3 text-xs text-gray-500">
            Offset: <span className="text-gray-900">{offset}</span> · Run status:{' '}
            <span className="text-gray-900">{runData?.status ?? '...'}</span>
          </div>
        </div>

        <pre className="mt-3 max-h-[60vh] overflow-auto rounded-md border border-gray-300 bg-gray-900 text-gray-100 p-3 text-xs font-mono">
          {displayed || 'No logs yet.'}
        </pre>
      </div>
    </div>
  );
}
