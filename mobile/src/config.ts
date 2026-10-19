/**
 * Runtime configuration.
 *
 * Only `EXPO_PUBLIC_*` variables are inlined into the client bundle by Expo, so
 * every key here must carry that prefix. Nothing secret belongs in this file —
 * it ships to the device.
 */

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

/** Request timeout in ms. Generous relative to NFR-01's 300 ms p95 budget. */
export const API_TIMEOUT_MS = 10_000;
