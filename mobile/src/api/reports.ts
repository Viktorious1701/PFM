/**
 * Financial Reporting API (FR) — SDS §5.7.1 FR-US-01.
 */
import { USE_MOCK_API } from '../config';
import { client } from './client';
import { mockGetSummaryReport } from './mock';
import type { SummaryReportRead } from './types';

/** FR-US-01 · `GET /api/v1/reports/summary`. Always the current calendar
 * month — the endpoint takes no period argument. */
export async function getSummaryReport(): Promise<SummaryReportRead> {
  if (USE_MOCK_API) return mockGetSummaryReport();

  const { data } = await client.get<SummaryReportRead>('/reports/summary');
  return data;
}
