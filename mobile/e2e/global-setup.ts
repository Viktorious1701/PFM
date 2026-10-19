/**
 * Runs once before the suite: checks both servers are up, warms the web
 * bundle (a cold dev build takes over a minute), and creates this run's
 * own ADMIN through the backend CLI, so tests never touch anyone's real or
 * demo data. Its credentials reach the tests through process.env.
 */
import { execFileSync } from 'node:child_process';
import path from 'node:path';

import { API_URL, APP_URL, BACKEND_DIR, PASSWORD } from './support/env';

export default async function globalSetup() {
  const health = await fetch(API_URL.replace(/\/api\/v1$/, '/health')).catch(() => null);
  if (!health?.ok) throw new Error(`Backend not reachable at ${API_URL} — start it first (CLAUDE.md §3).`);
  const app = await fetch(APP_URL).catch(() => null);
  if (!app?.ok) throw new Error(`Web app not reachable at ${APP_URL} — start it first (CLAUDE.md §3).`);
  // Warm the bundle so the first test isn't timed against a cold build.
  const bundle = `${APP_URL}/node_modules/expo-router/entry.bundle?platform=web&dev=true&hot=false&lazy=true&transform.engine=hermes&transform.routerRoot=app&unstable_transformProfile=hermes-stable`;
  await fetch(bundle).catch(() => undefined);

  const email = `e2e-admin-${Date.now()}@example.com`;
  execFileSync('uv', ['run', 'python', '-m', 'app.cli', 'create-admin', '--email', email, '--password', PASSWORD, '--full-name', 'E2E Admin'], {
    cwd: path.resolve(BACKEND_DIR),
    stdio: 'pipe',
  });
  process.env.E2E_ADMIN_EMAIL = email;
}
