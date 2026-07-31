/**
 * HTTP client.
 *
 * Per SDS §4.3.1: Axios with interceptors for JWT injection. Two interceptors:
 *   request  — attaches `Authorization: Bearer <jwt>` (SDS §6.1)
 *   response — normalises every failure into an ApiError (SDS §6.6)
 *
 * The token is supplied through a registered provider rather than imported from
 * the auth store, because the auth store needs this module — importing it back
 * would be a cycle.
 */
import axios from 'axios';

import { API_BASE_URL, API_TIMEOUT_MS } from '../config';
import { toApiError } from './errors';

type TokenProvider = () => string | null;

let getToken: TokenProvider = () => null;
let onUnauthenticated: (() => void) | null = null;

/** Called by the auth store once it has hydrated. */
export function setTokenProvider(provider: TokenProvider): void {
  getToken = provider;
}

/**
 * Registers the global 401 reaction (clear session and bounce to login).
 * Spec AC-05: an expired or invalid credential must not silently no-op.
 */
export function setUnauthenticatedHandler(handler: () => void): void {
  onUnauthenticated = handler;
}

export const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const apiError = toApiError(error);
    if (apiError.isUnauthenticated && onUnauthenticated) {
      onUnauthenticated();
    }
    return Promise.reject(apiError);
  },
);
