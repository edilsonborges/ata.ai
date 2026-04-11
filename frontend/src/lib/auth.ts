'use client';

type Tokens = { access_token: string; refresh_token: string };

const STORAGE_KEY = 'ata_tokens';

export function setTokens(t: Tokens): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
  }
}

export function getTokens(): Tokens | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? (JSON.parse(raw) as Tokens) : null;
}

export function clearTokens(): void {
  if (typeof window !== 'undefined') localStorage.removeItem(STORAGE_KEY);
}

export function getAccessToken(): string | null {
  return getTokens()?.access_token ?? null;
}
