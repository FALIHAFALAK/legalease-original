function resolveApiUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (typeof window !== 'undefined') {
    const currentHost = window.location.hostname;
    if (!configured) return `${window.location.protocol}//${currentHost}:8000`;
    try {
      const parsed = new URL(configured);
      if (['localhost', '127.0.0.1', '[::1]'].includes(parsed.hostname)) {
        return `${window.location.protocol}//${currentHost}:${parsed.port || '8000'}`;
      }
    } catch {
      return `${window.location.protocol}//${currentHost}:8000`;
    }
  }
  return configured || 'http://localhost:8000';
}

export const API_URL = resolveApiUrl().replace(/\/$/, '');
const CSRF_COOKIE_NAME = process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME || 'le_csrf';

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = 'request_failed') {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const prefix = `${name}=`;
  const item = document.cookie.split('; ').find((part) => part.startsWith(prefix));
  return item ? decodeURIComponent(item.slice(prefix.length)) : null;
}

export async function csrfToken(): Promise<string> {
  const existing = getCookie(CSRF_COOKIE_NAME);
  if (existing) return existing;
  const response = await fetch(`${API_URL}/api/auth/csrf`, { credentials: 'include' });
  if (!response.ok) throw new ApiError('Could not initialize request protection.', response.status);
  return (await response.json()).csrf_token;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  let body = options.body;
  if (body && !(body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (options.method && !['GET', 'HEAD', 'OPTIONS'].includes(options.method.toUpperCase())) {
    headers.set('X-CSRF-Token', await csrfToken());
  }
  const response = await fetch(`${API_URL}${path}`, { ...options, headers, body, credentials: 'include' });
  if (response.status === 204 || response.status === 205) return '' as T;
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof data === 'object' && data !== null && 'detail' in data ? data.detail : null;
    const message = typeof detail === 'object' && detail !== null && 'message' in detail ? String(detail.message) : typeof detail === 'string' ? detail : 'The request could not be completed.';
    const code = typeof detail === 'object' && detail !== null && 'code' in detail ? String(detail.code) : 'request_failed';
    throw new ApiError(message, response.status, code);
  }
  return data as T;
}

export function jsonBody(value: unknown): RequestInit {
  return { method: 'POST', body: JSON.stringify(value) };
}
