/**
 * Wallet Management API (WM) — SDS §6.3 WM-API-01/02.
 */
import { USE_MOCK_API } from '../config';
import { client } from './client';
import { mockCreateWallet, mockListWallets } from './mock';
import type { Page, WalletCreate, WalletRead } from './types';

/** WM-US-02 · `GET /api/v1/wallets`. `pageSize` defaults to 100 — API-06's
 * own bounded maximum, not the 25 other list endpoints default to — since
 * the Wallets screen has no pagination UI of its own (a realistic wallet
 * count fits in one page). */
export async function listWallets(page = 1, pageSize = 100): Promise<Page<WalletRead>> {
  if (USE_MOCK_API) return mockListWallets(page, pageSize);

  const { data } = await client.get<Page<WalletRead>>('/wallets', {
    params: { page, page_size: pageSize },
  });
  return data;
}

/** WM-US-01 · `POST /api/v1/wallets`. */
export async function createWallet(payload: WalletCreate): Promise<WalletRead> {
  if (USE_MOCK_API) return mockCreateWallet(payload);

  const { data } = await client.post<WalletRead>('/wallets', payload);
  return data;
}
