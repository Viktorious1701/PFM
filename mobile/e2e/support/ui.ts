/**
 * Screen actions shared by every spec: signing in, moving between tabs,
 * and watching which API requests a button sends.
 */
import { expect, type Page, type Request, type Response } from '@playwright/test';

import type { Account } from './api';

const API = '/api/v1';

/** Opens the app and signs in through the sign-in panel. */
export async function signIn(page: Page, who: Pick<Account, 'email' | 'password'>) {
  await page.goto('/');
  await page.getByTestId('login-email').fill(who.email);
  await page.getByTestId('login-password').fill(who.password);
  await page.getByTestId('login-submit').click();
  await expect(page.getByTestId('tab-home')).toBeVisible();
}

/** Switches tab and waits until the new page has replaced the old one. */
export async function openTab(page: Page, key: 'home' | 'wallets' | 'activity' | 'budgets' | 'family', ready: string) {
  await page.getByTestId(`tab-${key}`).click();
  await expect(page.getByTestId(ready)).toBeVisible();
}

/** Resolves with the response to the next `method` request whose path
 * (after /api/v1) matches `route`. */
export function apiResponse(page: Page, method: string, route: RegExp): Promise<Response> {
  return page.waitForResponse((r) => r.request().method() === method && matches(r.request(), route));
}

function matches(req: Request, route: RegExp) {
  const u = new URL(req.url());
  return u.pathname.startsWith(API) && route.test(u.pathname.slice(API.length) + u.search);
}

/** Records every API request (method + path) the page sends from now on. */
export function recordApi(page: Page) {
  const sent: string[] = [];
  page.on('request', (r) => {
    const u = new URL(r.url());
    if (u.pathname.startsWith(API) && r.method() !== 'OPTIONS') sent.push(`${r.method()} ${u.pathname.slice(API.length)}`);
  });
  return {
    sent,
    /** Requests matching `method` + `route` sent so far. */
    count: (method: string, route: RegExp) => sent.filter((s) => s.startsWith(`${method} `) && route.test(s.slice(method.length + 1))).length,
  };
}

/** The inline error/alert text currently shown. */
export const alert = (page: Page) => page.getByRole('alert').first();
