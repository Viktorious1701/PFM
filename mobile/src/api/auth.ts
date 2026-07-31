/**
 * System Security API (SS) — SDS §6.3 SS-API-01.
 *
 * SS-US-01 (login) is specified in a different epic and is not implemented on
 * the backend yet. This wrapper exists so the invite screen has an authenticated
 * caller to stand behind, which spec AC-04/AC-05 require.
 */
import { USE_MOCK_API } from '../config';
import { client } from './client';
import { mockLogin } from './mock';
import type { LoginRequest, LoginResponse } from './types';

/** SS-US-01 · `POST /api/v1/auth/login`. Public endpoint (constitution API-08). */
export async function login(email: string, password: string): Promise<LoginResponse> {
  if (USE_MOCK_API) return mockLogin(email, password);

  const payload: LoginRequest = { email, password };
  const { data } = await client.post<LoginResponse>('/auth/login', payload);
  return data;
}
