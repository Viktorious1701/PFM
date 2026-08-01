import { USE_MOCK_API } from '../config';
import { client } from './client';
import { mockActivate, mockInviteUser, mockListUsers } from './mock';
import type {
  ActivateRequest,
  ActivateResponse,
  InvitationRead,
  InviteCreate,
  Page,
  TokenStateRead,
  UserRead,
} from './types';

export async function inviteUser(email: string): Promise<InvitationRead> {
  if (USE_MOCK_API) return mockInviteUser(email);

  const payload: InviteCreate = { email };
  const { data } = await client.post<InvitationRead>('/users/invite', payload);
  return data;
}

export async function listUsers(page = 1, pageSize = 25): Promise<Page<UserRead>> {
  if (USE_MOCK_API) return mockListUsers();

  const { data } = await client.get<Page<UserRead>>('/users', {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function checkTokenState(token: string): Promise<TokenStateRead> {
  if (USE_MOCK_API) {
    if (!token) return { state: 'not_usable' };
    if (token === 'expired') return { state: 'expired' };
    return { state: 'usable' };
  }

  const { data } = await client.get<TokenStateRead>('/users/activate', {
    params: { token },
  });
  return data;
}

export async function activateAccount(payload: ActivateRequest): Promise<ActivateResponse> {
  if (USE_MOCK_API) return mockActivate(payload.token);

  const { data } = await client.post<ActivateResponse>('/users/activate', payload);
  return data;
}