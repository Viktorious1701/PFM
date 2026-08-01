/**
 * Dev-only tooling API (UM-US-01 A13/A14).
 *
 * Not a documented SDS story — `GET /api/v1/dev/outbox` is operational
 * tooling for this environment, recorded in specs/001-user-onboarding/plan.md
 * A14, not a DTO in the API contract. 404s outside development on the server
 * regardless of what this client does; `SHOW_DEV_TOOLS` (config.ts) only
 * controls whether the screen that calls it renders.
 */
import { client } from './client';
import type { OutboxList } from './types';

export async function getOutbox(): Promise<OutboxList> {
  const { data } = await client.get<OutboxList>('/dev/outbox');
  return data;
}
