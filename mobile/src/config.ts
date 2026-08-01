/**
 * Runtime configuration.
 *
 * Only `EXPO_PUBLIC_*` variables are inlined into the client bundle by Expo, so
 * every key here must carry that prefix. Nothing secret belongs in this file —
 * it ships to the device.
 */

/**
 * When true, all API calls are served from local fixtures instead of HTTP.
 *
 * Login (SS-US-01), invite (UM-US-01) and activate (UM-US-02) are real,
 * verified backend routes — `.env.example` defaults this to `0`. Set it to
 * `1` to explore screens with no backend yet: UM-US-03 (list users) and
 * Features 03-11 (wallets, budgets, transactions, ...) are still
 * fixture-only.
 */
export const USE_MOCK_API = process.env.EXPO_PUBLIC_API_MOCK === '1';

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

/** Request timeout in ms. Generous relative to NFR-01's 300 ms p95 budget. */
export const API_TIMEOUT_MS = 10_000;

/**
 * Shows dev-only chrome — currently the Family > Invites "copy activation
 * link" action, which reads `GET /api/v1/dev/outbox` (UM-US-01 A14).
 * Never a substitute for the real invitation flow; strictly for this
 * environment, where no convenient mailbox exists to check.
 */
export const SHOW_DEV_TOOLS = process.env.EXPO_PUBLIC_DEV_TOOLS === '1';
