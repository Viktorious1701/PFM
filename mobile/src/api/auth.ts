/**
 * System Security API (SS) — SDS §6.3 SS-API-01.
 *
 * SS-US-01 (login) is specified in a different epic and is not implemented on
 * the backend yet. This wrapper exists so the invite screen has an authenticated
 * caller to stand behind, which spec AC-04/AC-05 require.
 */
import { client } from './client';
import type { LoginRequest, LoginResponse } from './types';

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
