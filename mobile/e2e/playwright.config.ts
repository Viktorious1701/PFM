/**
 * Functional UI tests (CLAUDE.md §1.1 rule 0): behaviour, never visual
 * design. They drive the Expo web app on :8081 against the real backend on
 * :8000 — both must already be running (CLAUDE.md §3).
 */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  globalSetup: './global-setup.ts',
  // The dev bundle and the camera pans are slow on purpose; tests wait for
  // real outcomes, not fixed sleeps, but give them room.
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  workers: 2,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_APP_URL ?? 'http://localhost:8081',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 860 } } },
    { name: 'phone', use: { ...devices['Pixel 7'] } },
  ],
});
