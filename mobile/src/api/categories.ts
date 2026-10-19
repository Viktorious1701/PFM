/**
 * Category Management API (CM) — SDS §2.1; backend app/api/v1/categories.py.
 *
 * `GET /api/v1/categories` (CM-US-02) is a concurrently-landing backend
 * story — this file calls it as a real, unconditional endpoint per this
 * slice's own plan; no defensive "the route might still 404" handling.
 */
import { client } from './client';
import type { CategoryCreate, CategoryRead, Page } from './types';

/** CM-US-02 · `GET /api/v1/categories`. */
export async function listCategories(page = 1, pageSize = 100): Promise<Page<CategoryRead>> {

  const { data } = await client.get<Page<CategoryRead>>('/categories', {
    params: { page, page_size: pageSize },
  });
  return data;
}

/** CM-US-01 · `POST /api/v1/categories`. */
export async function createCategory(payload: CategoryCreate): Promise<CategoryRead> {

  const { data } = await client.post<CategoryRead>('/categories', payload);
  return data;
}

/** CM-US-04 · `PATCH /api/v1/categories/{id}` — rename. Real backend only. */
export async function renameCategory(id: string, name: string): Promise<CategoryRead> {
  const { data } = await client.patch<CategoryRead>(`/categories/${id}`, { name });
  return data;
}

/** CM-US-05 · `DELETE /api/v1/categories/{id}` — archives it: it leaves the
 * list, and past transactions keep it. Real backend only. */
export async function archiveCategory(id: string): Promise<void> {
  await client.delete(`/categories/${id}`);
}
