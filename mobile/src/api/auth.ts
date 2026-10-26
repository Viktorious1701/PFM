/**
 * System Security API (SS) — SDS §6.3 SS-API-01.
 *
 * SS-US-01 (login) is specified in a different epic and is not implemented on
 * the backend yet. This wrapper exists so the invite screen has an authenticated
 * caller to stand behind, which spec AC-04/AC-05 require.
 */
import { client } from './client';
import type { GuestSessionResponse, LoginRequest, LoginResponse, Page, WalletRead } from './types';

/** SS-US-01 · `POST /api/v1/auth/login`. Public endpoint (constitution API-08). */
export async function login(email: string, password: string): Promise<LoginResponse> {

  const payload: LoginRequest = { email, password };
  const { data } = await client.post<LoginResponse>('/auth/login', payload);
  return data;
}

/** SS-US-02 · `POST /api/v1/auth/logout`. The backend is stateless (the
 * token stays valid until it expires), so this only records the intent;
 * the client discarding its token is what actually ends the session. */
export async function logout(): Promise<void> {
  await client.post('/auth/logout');
}

/** SS-US-03 · `POST /api/v1/auth/guest`. Public, no body (constitution
 * API-08): starts a 7-day guest trial holding one example and returns its
 * session. `429` / `503` arrive as an ApiError carrying the server's message. */
export async function guestLogin(): Promise<GuestSessionResponse> {
  const { data } = await client.post<GuestSessionResponse>('/auth/guest');
  return data;
}

/** SS-US-03 plan.md A18 · asks the server whether a saved guest trial's
 * session still works, through a route Home loads anyway — the smallest
 * Wallets page. There is no active session yet, so the saved token is sent
 * explicitly. Resolves on `200`; a `401` (trial ended or deleted) rejects
 * with an ApiError whose `isUnauthenticated` is true. */
export async function confirmGuestSession(token: string): Promise<void> {
  await client.get<Page<WalletRead>>('/wallets', {
    params: { page: 1, page_size: 1 },
    headers: { Authorization: `Bearer ${token}` },
  });
}
