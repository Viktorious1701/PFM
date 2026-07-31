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
 * This exists because the backend has no routes yet: `backend/app/` is only
 * `core/`, `db/` and `main.py`, so `POST /api/v1/users/invite` does not exist.
 * Set EXPO_PUBLIC_API_MOCK=0 once tasks T-01…T-17 of
 * specs/001-user-onboarding/plan.md have landed.
 */
export const USE_MOCK_API = process.env.EXPO_PUBLIC_API_MOCK !== '0';

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

/** Request timeout in ms. Generous relative to NFR-01's 300 ms p95 budget. */
export const API_TIMEOUT_MS = 10_000;
