import path from 'node:path';

export const APP_URL = process.env.E2E_APP_URL ?? 'http://localhost:8081';
export const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000/api/v1';
export const BACKEND_DIR = process.env.E2E_BACKEND_DIR ?? path.resolve(__dirname, '../../../backend');
/** Where the dev backend writes invitation emails (EMAIL_TRANSPORT=outbox). */
export const OUTBOX_DIR = process.env.E2E_OUTBOX_DIR ?? path.join(BACKEND_DIR, 'var/outbox');
/** Satisfies the password policy (VL-04). Every account the suite makes uses it. */
export const PASSWORD = 'E2e-Moonlit-2026!';
