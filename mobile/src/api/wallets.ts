/**
 * Wallet Management API (WM) — SDS §6.3 WM-API-01/02.
 */
import { client } from './client';
import type { Page, WalletCreate, WalletRead, WalletUpdate } from './types';

/** WM-US-02 · `GET /api/v1/wallets`. `pageSize` defaults to 100 — API-06's
 * own bounded maximum, not the 25 other list endpoints default to — since
 * the Wallets screen has no pagination UI of its own (a realistic wallet
 * count fits in one page). */
export async function listWallets(page = 1, pageSize = 100): Promise<Page<WalletRead>> {

  const { data } = await client.get<Page<WalletRead>>('/wallets', {
    params: { page, page_size: pageSize },
  });
  return data;
}

/** WM-US-01 · `POST /api/v1/wallets`. */
export async function createWallet(payload: WalletCreate): Promise<WalletRead> {

  const { data } = await client.post<WalletRead>('/wallets', payload);
  return data;
}

/** `PATCH /api/v1/wallets/{id}` — rename or retype. Real backend only. */
export async function updateWallet(id: string, payload: WalletUpdate): Promise<WalletRead> {
  const { data } = await client.patch<WalletRead>(`/wallets/${id}`, payload);
  return data;
}

/** `DELETE /api/v1/wallets/{id}` — archives the wallet (it leaves the list;
 * its history is kept). Real backend only. */
export async function archiveWallet(id: string): Promise<void> {
  await client.delete(`/wallets/${id}`);
}
