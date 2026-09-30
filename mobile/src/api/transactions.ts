/**
 * Transaction Management API (TM) — SDS §5.6; backend app/api/v1/transactions.py.
 */
import { USE_MOCK_API } from '../config';
import { client } from './client';
import { mockCreateTransaction, mockListTransactions } from './mock';
import type { Page, TransactionCreate, TransactionListParams, TransactionRead } from './types';

/**
 * TM-US-02 · `GET /api/v1/transactions`. `page`/`page_size` default to
 * 1/25 (API-06's default, not the Wallets screen's 100 — an unbounded
 * transaction feed needs real pagination). `wallet_id`/`category_id`/
 * `date_from`/`date_to` are merged into the query only when the caller
 * actually supplied them.
 */
export async function listTransactions(
  params: TransactionListParams = {},
): Promise<Page<TransactionRead>> {
  if (USE_MOCK_API) return mockListTransactions(params);

  const { page = 1, page_size = 25, wallet_id, category_id, date_from, date_to } = params;
  const query: Record<string, string | number> = { page, page_size };
  if (wallet_id !== undefined) query.wallet_id = wallet_id;
  if (category_id !== undefined) query.category_id = category_id;
  if (date_from !== undefined) query.date_from = date_from;
  if (date_to !== undefined) query.date_to = date_to;

  const { data } = await client.get<Page<TransactionRead>>('/transactions', { params: query });
  return data;
}

/** TM-US-01 · `POST /api/v1/transactions`. */
export async function createTransaction(payload: TransactionCreate): Promise<TransactionRead> {
  if (USE_MOCK_API) return mockCreateTransaction(payload);

  const { data } = await client.post<TransactionRead>('/transactions', payload);
  return data;
}
