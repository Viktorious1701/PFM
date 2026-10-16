/**
 * Budget Management API — backend app/api/v1/budgets.py. Real backend only
 * (there were never fixtures for it).
 */
import { client } from './client';
import type { BudgetCreate, BudgetProgressRead, Page } from './types';

/** `GET /api/v1/budgets` — each budget with this month's progress. */
export async function listBudgets(page = 1, pageSize = 100): Promise<Page<BudgetProgressRead>> {
  const { data } = await client.get<Page<BudgetProgressRead>>('/budgets', { params: { page, page_size: pageSize } });
  return data;
}

/** `POST /api/v1/budgets`. */
export async function createBudget(payload: BudgetCreate): Promise<void> {
  await client.post('/budgets', payload);
}

/** `PATCH /api/v1/budgets/{id}` — the limit is the only editable field. */
export async function updateBudget(id: string, amountLimit: string): Promise<void> {
  await client.patch(`/budgets/${id}`, { amount_limit: amountLimit });
}

/** `DELETE /api/v1/budgets/{id}`. */
export async function deleteBudget(id: string): Promise<void> {
  await client.delete(`/budgets/${id}`);
}
