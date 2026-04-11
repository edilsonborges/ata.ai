'use client';

import { clearTokens, getAccessToken, getTokens, setTokens } from './auth';

const BASE = '';  // rewrites do next.config

type FetchOpts = RequestInit & { skipAuth?: boolean };

async function refreshAccess(): Promise<string | null> {
  const tokens = getTokens();
  if (!tokens) return null;
  const r = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  });
  if (!r.ok) { clearTokens(); return null; }
  const fresh = await r.json();
  setTokens(fresh);
  return fresh.access_token;
}

export async function api<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const doFetch = async (token: string | null) => {
    const headers = new Headers(opts.headers);
    if (token && !opts.skipAuth) headers.set('Authorization', `Bearer ${token}`);
    if (opts.body && !headers.has('Content-Type') && !(opts.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }
    return fetch(`${BASE}${path}`, { ...opts, headers });
  };

  let token = getAccessToken();
  let r = await doFetch(token);
  if (r.status === 401 && !opts.skipAuth) {
    token = await refreshAccess();
    if (token) r = await doFetch(token);
  }
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${text}`);
  }
  if (r.status === 204) return undefined as T;
  return r.json() as Promise<T>;
}

export async function apiForm<T>(path: string, form: FormData): Promise<T> {
  return api<T>(path, { method: 'POST', body: form });
}
