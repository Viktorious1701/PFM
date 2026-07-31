/**
 * User Management API (UM) — SDS §6.3 UM-API-01 / UM-API-02 / UM-API-03.
 *
 * Each function dispatches to either the real endpoint or the fixture layer,
 * chosen once at the module boundary. Screens call these and never learn which
 * one answered — so flipping EXPO_PUBLIC_API_MOCK=0 requires no screen change.
 */
import { USE_MOCK_API } from '../config';
import { client } from './client';
import { mockActivate, mockInviteUser, mockListUsers } from './mock';
import type {
  ActivateRequest,
  ActivateResponse,
  InvitationRead,
  InviteCreate,
  Page,
  UserRead,
} from './types';

/**
 * UM-US-01 · `POST /api/v1/users/invite` (SDS §6.4.1).
 *
 * Rejects are always ApiError (see client.ts response interceptor), so callers
 * can branch on `.code` without unwrapping axios internals.
 */
export async function inviteUser(email: string): Promise<InvitationRead> {
  if (USE_MOCK_API) return mockInviteUser(email);

  const payload: InviteCreate = { email };
  const { data } = await client.post<InvitationRead>('/users/invite', payload);
  return data;
}

/** UM-US-03 · `GET /api/v1/users`. Always bounded (constitution API-06, PF-04). */
export async function listUsers(page = 1, pageSize = 25): Promise<Page<UserRead>> {
  if (USE_MOCK_API) return mockListUsers();

  const { data } = await client.get<Page<UserRead>>('/users', {
    params: { page, page_size: pageSize },
  });
  return data;
}

/** UM-US-02 · `POST /api/v1/users/activate` (SDS §6.4.2). */
export async function activateAccount(payload: ActivateRequest): Promise<ActivateResponse> {
  if (USE_MOCK_API) return mockActivate(payload.token);

  const { data } = await client.post<ActivateResponse>('/users/activate', payload);
  return data;
}
