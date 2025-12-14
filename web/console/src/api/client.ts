import { loadSettings } from '@/app/settings/store';

function normalizeBase(base: string): string {
  const b = base.trim();
  if (!b) return '';
  return b.endsWith('/') ? b.slice(0, -1) : b;
}

function normalizeBearerToken(token: string): string {
  const t = (token || '').trim();
  if (!t) return '';
  return t.toLowerCase().startsWith('bearer ') ? t.slice('bearer '.length).trim() : t;
}

function makeRequestId(): string {
  try {
    // Some browsers (or older WebViews) may not support crypto.randomUUID().
    // Keep this best-effort and never fail the request.
    const c = (globalThis as any).crypto;
    if (c && typeof c.randomUUID === 'function') {
      return String(c.randomUUID());
    }
  } catch {
    // ignore
  }
  return `req_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function tryJwtRefresh(base: string): Promise<boolean> {
  try {
    const statusResp = await fetch(`${base}/auth/status`, { credentials: 'include' });
    if (!statusResp.ok) return false;
    const status = (await statusResp.json()) as { mode?: string; authenticated?: boolean };
    if (status.mode !== 'jwt') return false;
    // If already authenticated, no need to refresh.
    if (status.authenticated) return true;
    const refreshResp = await fetch(`${base}/auth/refresh`, { method: 'POST', credentials: 'include' });
    return refreshResp.ok;
  } catch {
    return false;
  }
}

async function apiFetchJsonInternal<T>(path: string, init?: RequestInit, attempt: number = 0): Promise<T> {
  const settings = loadSettings();
  const envBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
  const base = normalizeBase(settings.api.apiBase || envBase);

  const headers = new Headers(init?.headers);
  if (init?.body != null && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  headers.set('X-Request-ID', makeRequestId());
  const bearer = normalizeBearerToken(settings.api.bearerToken);
  if (bearer) {
    headers.set('Authorization', `Bearer ${bearer}`);
  }
  if (settings.api.projectToken) {
    headers.set('X-Project-Token', settings.api.projectToken);
  }

  const resp = await fetch(`${base}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  const contentType = resp.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const body = isJson ? await resp.json().catch(() => null) : await resp.text().catch(() => '');

  if (!resp.ok) {
    if (resp.status === 401 && attempt === 0 && !bearer) {
      const refreshed = await tryJwtRefresh(base);
      if (refreshed) {
        return await apiFetchJsonInternal<T>(path, init, attempt + 1);
      }
    }
    if (resp.status === 401 && !bearer && typeof window !== 'undefined') {
      const current = window.location.pathname + window.location.search;
      try {
        const statusResp = await fetch(`${base}/auth/status`, { credentials: 'include' });
        if (statusResp.ok) {
          const status = (await statusResp.json()) as { mode?: string; authenticated?: boolean };
          if (status.mode === 'oidc') {
            window.location.assign(`${base}/auth/login?next=${encodeURIComponent(current)}`);
          } else if (status.mode === 'jwt' && !status.authenticated) {
            const routerBase = import.meta.env.MODE === 'production' ? '/console' : '';
            window.location.assign(`${routerBase}/login?next=${encodeURIComponent(current)}`);
          } else {
            const routerBase = import.meta.env.MODE === 'production' ? '/console' : '';
            window.location.assign(`${routerBase}/settings?tab=advanced&next=${encodeURIComponent(current)}`);
          }
        }
      } catch {
        const routerBase = import.meta.env.MODE === 'production' ? '/console' : '';
        window.location.assign(`${routerBase}/settings?tab=advanced&next=${encodeURIComponent(current)}`);
      }
    }
    const detail =
      typeof body === 'object' && body && 'detail' in (body as any)
        ? String((body as any).detail)
        : typeof body === 'string' && body.trim()
          ? body.trim().slice(0, 160)
          : 'Request failed';
    const message = `${detail} (HTTP ${resp.status})`;
    throw new ApiError(message, resp.status, body);
  }

  return body as T;
}

export async function apiFetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  return await apiFetchJsonInternal<T>(path, init, 0);
}

export const apiClient = {
  fetch: apiFetchJson,
};

