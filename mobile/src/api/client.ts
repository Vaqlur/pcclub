/**
 * HTTP client for the PC Club API: base URL, bearer token, the error envelope, and
 * refresh-on-401.
 *
 * Refresh tokens rotate, and replaying a rotated one revokes every session of the user. So a
 * refresh is single-flight: all requests that hit 401 at the same time wait for one refresh.
 */

import { type Tokens, readTokens, writeTokens } from './tokenStore';
import type { components } from './schema';

type TokenPair = components['schemas']['TokenPair'];

export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(
  /\/+$/,
  '',
);

/** Every failed call. `code` is the API's stable error code; the UI localizes by it. */
export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly details: unknown = null,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

let tokens: Tokens | null = null;
let onSessionLost: (() => void) | null = null;
let refreshInFlight: Promise<boolean> | null = null;

/** Called when the server no longer accepts the session (refresh token rejected). */
export function setSessionLostHandler(handler: (() => void) | null): void {
  onSessionLost = handler;
}

export async function restoreSession(): Promise<boolean> {
  tokens = await readTokens();
  return tokens !== null;
}

export async function startSession(pair: TokenPair): Promise<void> {
  tokens = { accessToken: pair.access_token, refreshToken: pair.refresh_token };
  await writeTokens(tokens);
}

export async function endSession(): Promise<void> {
  tokens = null;
  await writeTokens(null);
}

export function currentRefreshToken(): string | null {
  return tokens?.refreshToken ?? null;
}

type Query = Record<string, string | number | null | undefined>;

export type RequestOptions = {
  body?: unknown;
  query?: Query;
  headers?: Record<string, string>;
  /** Send the bearer token and refresh on 401. Default true. */
  auth?: boolean;
};

function buildUrl(path: string, query?: Query): string {
  const params = Object.entries(query ?? {})
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  return API_URL + path + (params.length ? `?${params.join('&')}` : '');
}

async function send(
  method: string,
  path: string,
  options: RequestOptions,
  accessToken: string | null,
): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json', ...options.headers };
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  try {
    return await fetch(buildUrl(path, options.query), {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError('NETWORK_ERROR', 'The server could not be reached', 0);
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const payload = (await response.json()) as {
      error?: { code?: unknown; message?: unknown; details?: unknown };
    };
    const error = payload.error;
    if (error && typeof error.code === 'string') {
      const message = typeof error.message === 'string' ? error.message : error.code;
      return new ApiError(error.code, message, response.status, error.details ?? null);
    }
  } catch {
    // not JSON: fall through
  }
  return new ApiError('HTTP_ERROR', `HTTP ${response.status}`, response.status);
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function refreshOnce(): Promise<boolean> {
  const refreshToken = tokens?.refreshToken;
  if (!refreshToken) return false;
  const response = await send(
    'POST',
    '/v1/auth/refresh',
    { body: { refresh_token: refreshToken } },
    null,
  );
  if (response.ok) {
    await startSession((await response.json()) as TokenPair);
    return true;
  }
  if (response.status === 401 || response.status === 403) {
    await endSession();
    onSessionLost?.();
    return false;
  }
  throw await toApiError(response); // server trouble: keep the session, let the caller retry
}

function refresh(): Promise<boolean> {
  refreshInFlight ??= refreshOnce().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export async function api<T>(
  method: 'GET' | 'POST' | 'PATCH',
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const useAuth = options.auth !== false;
  const usedToken = useAuth ? (tokens?.accessToken ?? null) : null;
  const response = await send(method, path, options, usedToken);

  if (response.status === 401 && useAuth && usedToken !== null) {
    // Another request may already have refreshed while this one was in the air.
    const alreadyRefreshed = tokens !== null && tokens.accessToken !== usedToken;
    if (alreadyRefreshed || (await refresh())) {
      return parse<T>(await send(method, path, options, tokens?.accessToken ?? null));
    }
  }
  return parse<T>(response);
}
