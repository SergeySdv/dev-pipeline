import React from 'react';
import { useNavigate, useSearch } from '@tanstack/react-router';

import { Button } from '@/components/ui/Button';

export function LoginPage() {
  const navigate = useNavigate();
  const search = useSearch({ from: '/login' });
  const routerBase = import.meta.env.MODE === 'production' ? '/console' : '';
  const nextRaw = search.next || '/dashboard';
  const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';

  function normalizeNextPath(input: string): string {
    const s = (input || '').trim();
    if (!s) return '/dashboard';
    // Prevent open redirects: only allow same-origin paths.
    if (s.startsWith('http://') || s.startsWith('https://')) return '/dashboard';
    let p = s;
    // Some callers may pass the full router base (e.g. "/console/dashboard").
    if (routerBase && p.startsWith(routerBase + '/')) {
      p = p.slice(routerBase.length);
    } else if (routerBase && p === routerBase) {
      p = '/dashboard';
    }
    if (!p.startsWith('/')) p = `/${p}`;
    // Avoid loops back into login.
    if (p === '/login' || p.startsWith('/login?')) return '/dashboard';
    return p;
  }

  const next = normalizeNextPath(nextRaw);

  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${apiBase}/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!resp.ok) {
        const ct = resp.headers.get('content-type') || '';
        const body = ct.includes('application/json') ? await resp.json().catch(() => null) : await resp.text().catch(() => '');
        const msg =
          typeof body === 'object' && body && 'detail' in (body as any) ? String((body as any).detail) : `Login failed`;
        throw new Error(msg);
      }
      navigate({ to: next });
    } catch (err: any) {
      setError(err?.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto mt-20 w-full max-w-md rounded-md border border-border bg-bg-panel p-6">
      <div className="text-lg font-semibold">Sign in</div>
      <div className="mt-1 text-xs text-fg-muted">Use your username and password.</div>

      <form className="mt-6 grid gap-3" onSubmit={onSubmit}>
        <label className="grid gap-1 text-sm">
          <span className="text-xs text-fg-muted">Username</span>
          <input
            className="rounded-md border border-border bg-bg-muted px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            placeholder="admin"
          />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="text-xs text-fg-muted">Password</span>
          <input
            className="rounded-md border border-border bg-bg-muted px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            type="password"
            placeholder="••••••••"
          />
        </label>

        {error && <div className="rounded-md border border-red-500/30 bg-red-500/10 p-2 text-sm text-red-200">{error}</div>}

        <Button variant="primary" disabled={loading || !username || !password}>
          {loading ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </div>
  );
}

