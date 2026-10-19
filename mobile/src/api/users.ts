import { client } from './client';
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

  const payload: InviteCreate = { email };
  const { data } = await client.post<InvitationRead>('/users/invite', payload);
  return data;
}

export async function listUsers(page = 1, pageSize = 25): Promise<Page<UserRead>> {

  const { data } = await client.get<Page<UserRead>>('/users', {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function checkTokenState(token: string): Promise<TokenStateRead> {

  const { data } = await client.get<TokenStateRead>('/users/activate', {
    params: { token },
  });
  return data;
}

export async function activateAccount(payload: ActivateRequest): Promise<ActivateResponse> {

  const { data } = await client.post<ActivateResponse>('/users/activate', payload);
  return data;
}