/**
 * Category Management API (CM) — SDS §2.1; backend app/api/v1/categories.py.
 *
 * `GET /api/v1/categories` (CM-US-02) is a concurrently-landing backend
 * story — this file calls it as a real, unconditional endpoint per this
 * slice's own plan; no defensive "the route might still 404" handling.
 */
import { USE_MOCK_API } from '../config';
import { client } from './client';
import { mockCreateCategory, mockListCategories } from './mock';
import type { CategoryCreate, CategoryRead, Page } from './types';

/** CM-US-02 · `GET /api/v1/categories`. */
export async function listCategories(page = 1, pageSize = 100): Promise<Page<CategoryRead>> {
  if (USE_MOCK_API) return mockListCategories(page, pageSize);

  const { data } = await client.get<Page<CategoryRead>>('/categories', {
    params: { page, page_size: pageSize },
  });
  return data;
}

/** CM-US-01 · `POST /api/v1/categories`. */
export async function createCategory(payload: CategoryCreate): Promise<CategoryRead> {
  if (USE_MOCK_API) return mockCreateCategory(payload);

  const { data } = await client.post<CategoryRead>('/categories', payload);
  return data;
}
