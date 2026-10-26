/** System Security — specs/002-system-security/test_cases.md, "SS: UI test cases". */
import { expect, test, type Page } from '@playwright/test';

import { createWallet, invite, newMember, uid } from './support/api';
import { PASSWORD } from './support/env';
import { alert, apiResponse, openTab, recordApi, signIn } from './support/ui';

test('TC-49 An ACTIVE account signs in and stays signed in across a reload', async ({ page }) => {
  const me = await newMember();
  await page.goto('/');
  await page.getByTestId('login-email').fill(me.email);
  await page.getByTestId('login-password').fill(me.password);
  const login = apiResponse(page, 'POST', /^\/auth\/login$/);
  await page.getByTestId('login-submit').click();
  expect((await login).status()).toBe(200);
  await expect(page.getByTestId('total-balance')).toBeVisible();

  await page.reload();
  await expect(page.getByTestId('total-balance')).toBeVisible();
  await expect(page.getByTestId('login-submit')).toHaveCount(0);
});

test('TC-50 A wrong password is refused with the generic message', async ({ page }) => {
  const me = await newMember();
  await page.goto('/');
  await page.getByTestId('login-email').fill(me.email);
  await page.getByTestId('login-password').fill('Wrong-Password-1!');
  const login = apiResponse(page, 'POST', /^\/auth\/login$/);
  await page.getByTestId('login-submit').click();
  expect((await login).status()).toBe(401);
  await expect(alert(page)).toHaveText('The email or password is incorrect.');
  await expect(page.getByTestId('login-submit')).toBeVisible();
});

test('TC-51 A PENDING account is told to activate first', async ({ page }) => {
  const email = `e2e-pending-${uid()}@example.com`;
  await invite(email);
  await page.goto('/');
  await page.getByTestId('login-email').fill(email);
  await page.getByTestId('login-password').fill(PASSWORD);
  const login = apiResponse(page, 'POST', /^\/auth\/login$/);
  await page.getByTestId('login-submit').click();
  expect((await login).status()).toBe(403);
  await expect(alert(page)).toContainText(/not (been )?activated/i);
  await expect(page.getByTestId('login-submit')).toBeVisible();
});

test('TC-52 Empty fields are caught before anything is sent', async ({ page }) => {
  await page.goto('/');
  const api = recordApi(page);
  await page.getByTestId('login-submit').click();
  await expect(alert(page)).toHaveText('Enter your email and password.');
  expect(api.count('POST', /^\/auth\/login$/)).toBe(0);
});

test('TC-53 Sign out ends the session on the server and on the device', async ({ page }) => {
  const me = await newMember();
  await signIn(page, me);
  const logout = page.waitForRequest((r) => r.method() === 'POST' && r.url().endsWith('/auth/logout'));
  const logoutRes = apiResponse(page, 'POST', /^\/auth\/logout$/);
  await page.getByTestId('sign-out').click();
  expect((await logout).headers().authorization).toMatch(/^Bearer \S+/);
  expect((await logoutRes).status()).toBe(200);
  await expect(page.getByTestId('login-submit')).toBeVisible();

  await page.reload();
  await expect(page.getByTestId('login-submit')).toBeVisible();
  await expect(page.getByTestId('tab-home')).toHaveCount(0);
});

test('TC-54 The sign-in panel names its server, and a changed address is used and remembered', async ({ page }) => {
  const me = await newMember();
  await page.goto('/');
  await expect(page.getByTestId('server-host')).toHaveText('localhost:8000');
  await page.getByTestId('server-change').click();
  await page.getByTestId('server-field').fill('http://127.0.0.1:8000');
  await page.getByTestId('server-save').click();
  await expect(page.getByTestId('server-host')).toHaveText('127.0.0.1:8000');

  await page.getByTestId('login-email').fill(me.email);
  await page.getByTestId('login-password').fill(me.password);
  const login = apiResponse(page, 'POST', /^\/auth\/login$/);
  await page.getByTestId('login-submit').click();
  const res = await login;
  expect(res.url()).toBe('http://127.0.0.1:8000/api/v1/auth/login');
  expect(res.status()).toBe(200);
  await expect(page.getByTestId('tab-home')).toBeVisible();

  await page.getByTestId('sign-out').click();
  await page.reload();
  await expect(page.getByTestId('server-host')).toHaveText('127.0.0.1:8000');
});

test('TC-56 An unreachable server is named as the problem', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('server-change').click();
  await page.getByTestId('server-field').fill('http://127.0.0.1:9');
  await page.getByTestId('server-save').click();
  await page.getByTestId('login-email').fill('nobody@example.com');
  await page.getByTestId('login-password').fill(PASSWORD);
  await page.getByTestId('login-submit').click();
  await expect(alert(page)).toHaveText('Could not reach the server. Check your connection and the server address.');
  await expect(page.getByTestId('login-submit')).toBeVisible();
});

test('TC-57 Something that is not a server address is refused before anything is sent', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('server-change').click();
  const api = recordApi(page);
  await page.getByTestId('server-field').fill('not a server');
  await page.getByTestId('server-save').click();
  await expect(alert(page)).toHaveText('That isn’t a server address. It looks like laptop-name.tailnet.ts.net');
  await page.getByTestId('server-cancel').click();
  await expect(page.getByTestId('server-host')).toHaveText('localhost:8000');
  expect(api.sent).toHaveLength(0);
});

// ---------------------------------------------------------------------------
// SS-US-03 — Guest trial (specs/002-system-security/test_cases.md, TC-86…TC-96)
//
// The backend these run against must allow more than 5 trial starts an hour
// from 127.0.0.1 (test_cases QF-06, plan.md A10): start it with e.g.
//   GUEST_RATE_LIMIT=1000/hour GUEST_MAX_ACTIVE=100000 uv run uvicorn app.main:app --port 8000
// A real trial end cannot be reached in a browser (QF-05), so the ended cases
// put a token the server refuses — the same 401 — or a past trial end into
// device storage instead.
// ---------------------------------------------------------------------------

type GuestSession = { access_token: string; expires_at: string };

const KEY = {
  token: 'pfm.access_token',
  savedToken: 'pfm.guest_trial.token',
  savedEnd: 'pfm.guest_trial.expires_at',
};
/** Refused by the server exactly as an ended or deleted trial is: 401. */
const REFUSED_TOKEN = 'not-a-live-guest-session';
const DAY = 24 * 60 * 60 * 1000;
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

/** The banner's date, on the same calendar as the browser's (same machine). */
function trialDate(expiresAt: string): string {
  const d = new Date(expiresAt);
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}
const bannerText = (expiresAt: string) =>
  `Guest trial — deleted on ${trialDate(expiresAt)}. Ask your family's admin for an invitation to keep using PFM.`;
/** plan.md A19: whole days left, rounded down, at least 1 (QF-08). */
function continueLabel(expiresAt: string): string {
  const n = Math.max(1, Math.floor((Date.parse(expiresAt) - Date.now()) / DAY));
  return `Continue guest trial — ${n} ${n === 1 ? 'day' : 'days'} left`;
}

/** Opens the sign-in panel and presses "Try as a guest"; resolves with the session. */
async function startGuest(page: Page): Promise<GuestSession> {
  if (!page.url().startsWith('http')) await page.goto('/');
  const started = apiResponse(page, 'POST', /^\/auth\/guest$/);
  await page.getByTestId('login-guest').click();
  const res = await started;
  expect(res.status()).toBe(201);
  await expect(page.getByTestId('tab-home')).toBeVisible();
  return (await res.json()) as GuestSession;
}

async function signOutToPanel(page: Page) {
  await page.getByTestId('sign-out').click();
  await expect(page.getByTestId('login-submit')).toBeVisible();
}

async function setStorage(page: Page, values: Record<string, string>) {
  await page.evaluate((v) => {
    for (const [k, val] of Object.entries(v)) localStorage.setItem(k, val);
  }, values);
}

test('TC-86 "Try as a guest" lands on Home with the example and the trial notice', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('login-guest')).toBeVisible();
  await expect(page.getByTestId('guest-continue')).toHaveCount(0);

  const session = await startGuest(page);

  await expect(page.getByTestId('guest-banner')).toHaveText(bannerText(session.expires_at));
  await openTab(page, 'wallets', 'wallets-total');
  await expect(page.getByTestId('wallet-card-Example wallet')).toBeVisible();
});

test('TC-87 A guest is still a guest after a reload', async ({ page }) => {
  const session = await startGuest(page);

  await page.reload();

  await expect(page.getByTestId('tab-home')).toBeVisible();
  await expect(page.getByTestId('login-submit')).toHaveCount(0);
  await expect(page.getByTestId('guest-banner')).toHaveText(bannerText(session.expires_at));
});

test('TC-88 A guest can add a wallet', async ({ page }) => {
  await startGuest(page);
  await openTab(page, 'wallets', 'add-wallet');
  await page.getByTestId('add-wallet').click();
  const name = `Guest ${uid()}`;
  await page.getByTestId('wallet-name').fill(name);
  await page.getByTestId('wallet-balance').fill('100.000');
  const created = apiResponse(page, 'POST', /^\/wallets$/);
  await page.getByTestId('wallet-submit').click();

  expect((await created).status()).toBe(201);
  await expect(page.getByTestId(`wallet-card-${name}`)).toBeVisible();
  await expect(page.getByTestId('wallet-card-Example wallet')).toBeVisible();
});

test('TC-89 A guest sees no Family tab', async ({ page }) => {
  await startGuest(page);

  await expect(page.getByTestId('tab-wallets')).toBeVisible();
  await expect(page.getByTestId('tab-family')).toHaveCount(0);
});

test('TC-90 A guest signs out, and continues the same trial from the sign-in screen', async ({ page }) => {
  const session = await startGuest(page);
  const added = await createWallet(session.access_token, `Kept ${uid()}`, '20000.00');
  let dialogs = 0;
  page.on('dialog', (d) => {
    dialogs += 1;
    void d.dismiss();
  });

  const logout = apiResponse(page, 'POST', /^\/auth\/logout$/);
  await signOutToPanel(page);
  expect((await logout).status()).toBe(200);
  expect(dialogs).toBe(0);
  await expect(page.getByTestId('guest-continue')).toHaveText(continueLabel(session.expires_at));
  await expect(page.getByTestId('login-guest')).toBeVisible();

  await page.reload();
  await expect(page.getByTestId('guest-continue')).toHaveText(continueLabel(session.expires_at));

  const confirms: string[] = [];
  page.on('request', (r) => {
    if (r.method() === 'GET' && /\/api\/v1\/wallets\?page=1&page_size=1$/.test(r.url())) confirms.push(r.url());
  });
  const confirm = apiResponse(page, 'GET', /^\/wallets\?page=1&page_size=1$/);
  await page.getByTestId('guest-continue').click();
  expect((await confirm).status()).toBe(200);
  await expect(page.getByTestId('tab-home')).toBeVisible();
  await expect(page.getByTestId('guest-banner')).toHaveText(bannerText(session.expires_at));
  expect(confirms).toHaveLength(1);

  await openTab(page, 'wallets', 'wallets-total');
  await expect(page.getByTestId('wallet-card-Example wallet')).toBeVisible();
  await expect(page.getByTestId(`wallet-card-${added.name}`)).toBeVisible();
});

test('TC-91 A guest\'s sign-out while the server cannot be reached still keeps the trial', async ({ page }) => {
  await startGuest(page);
  await page.route('**/api/v1/auth/logout', (route) => route.abort('internetdisconnected'));

  await signOutToPanel(page);
  await expect(page.getByTestId('guest-continue')).toBeVisible();

  await page.unroute('**/api/v1/auth/logout');
  const confirm = apiResponse(page, 'GET', /^\/wallets\?page=1&page_size=1$/);
  await page.getByTestId('guest-continue').click();
  expect((await confirm).status()).toBe(200);
  await expect(page.getByTestId('tab-home')).toBeVisible();
  await openTab(page, 'wallets', 'wallets-total');
  await expect(page.getByTestId('wallet-card-Example wallet')).toBeVisible();
});

test('TC-92 A saved trial the server refuses is dropped with a message', async ({ page }) => {
  await startGuest(page);
  await signOutToPanel(page);
  await setStorage(page, { [KEY.savedToken]: REFUSED_TOKEN });
  await page.reload();
  await expect(page.getByTestId('guest-continue')).toBeVisible();

  const confirm = apiResponse(page, 'GET', /^\/wallets\?page=1&page_size=1$/);
  await page.getByTestId('guest-continue').click();

  expect((await confirm).status()).toBe(401);
  await expect(page.getByTestId('guest-trial-ended')).toHaveText('Your guest trial has ended.');
  await expect(page.getByTestId('login-submit')).toBeVisible();
  await expect(page.getByTestId('guest-continue')).toHaveCount(0);

  await page.reload();
  await expect(page.getByTestId('login-submit')).toBeVisible();
  await expect(page.getByTestId('guest-continue')).toHaveCount(0);
  await expect(page.getByTestId('login-guest')).toBeVisible();
});

test('TC-93 A saved trial whose end has passed by the device\'s clock is not offered, and N is never 0', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('login-submit')).toBeVisible();
  const api = recordApi(page);
  const at = (ms: number) => new Date(Date.now() + ms).toISOString();

  await setStorage(page, { [KEY.savedToken]: REFUSED_TOKEN, [KEY.savedEnd]: at(-60_000) });
  await page.reload();
  await expect(page.getByTestId('login-submit')).toBeVisible();
  await expect(page.getByTestId('login-guest')).toBeVisible();
  await expect(page.getByTestId('guest-continue')).toHaveCount(0);
  await expect(page.getByTestId('guest-trial-ended')).toHaveCount(0);
  expect(api.sent).toHaveLength(0);

  await setStorage(page, { [KEY.savedToken]: REFUSED_TOKEN, [KEY.savedEnd]: at(5 * 60 * 60 * 1000) });
  await page.reload();
  await expect(page.getByTestId('guest-continue')).toHaveText('Continue guest trial — 1 day left');

  await setStorage(page, { [KEY.savedToken]: REFUSED_TOKEN, [KEY.savedEnd]: at(6 * DAY + 23 * 60 * 60 * 1000) });
  await page.reload();
  await expect(page.getByTestId('guest-continue')).toHaveText('Continue guest trial — 6 days left');
  expect(api.sent).toHaveLength(0);
});

test('TC-94 "Try as a guest" with a saved trial starts a new one and replaces it', async ({ page }) => {
  const first = await startGuest(page);
  const earlier = await createWallet(first.access_token, `Earlier ${uid()}`, '1000.00');
  await signOutToPanel(page);
  await expect(page.getByTestId('guest-continue')).toBeVisible();

  const second = await startGuest(page);
  expect(second.access_token).not.toBe(first.access_token);
  await openTab(page, 'wallets', 'wallets-total');
  await expect(page.getByTestId('wallet-card-Example wallet')).toBeVisible();
  await expect(page.getByTestId(`wallet-card-${earlier.name}`)).toHaveCount(0);

  await signOutToPanel(page);
  await expect(page.getByTestId('guest-continue')).toHaveCount(1);
  const confirm = apiResponse(page, 'GET', /^\/wallets\?page=1&page_size=1$/);
  await page.getByTestId('guest-continue').click();
  const res = await confirm;
  expect(res.status()).toBe(200);
  expect(res.request().headers().authorization).toBe(`Bearer ${second.access_token}`);
  await openTab(page, 'wallets', 'wallets-total');
  await expect(page.getByTestId('wallet-card-Example wallet')).toBeVisible();
  await expect(page.getByTestId(`wallet-card-${earlier.name}`)).toHaveCount(0);
});

test('TC-95 A member\'s sign-in leaves the saved trial for later', async ({ page }) => {
  const session = await startGuest(page);
  const kept = await createWallet(session.access_token, `Guest's ${uid()}`, '1000.00');
  await signOutToPanel(page);
  const member = await newMember();

  await page.getByTestId('login-email').fill(member.email);
  await page.getByTestId('login-password').fill(member.password);
  await page.getByTestId('login-submit').click();
  await expect(page.getByTestId('tab-home')).toBeVisible();
  await expect(page.getByTestId('guest-banner')).toHaveCount(0);
  await openTab(page, 'wallets', 'add-wallet');
  await expect(page.getByTestId('wallet-card-Example wallet')).toHaveCount(0);
  await expect(page.getByTestId(`wallet-card-${kept.name}`)).toHaveCount(0);
  await signOutToPanel(page);

  await expect(page.getByTestId('guest-continue')).toBeVisible();
  const confirm = apiResponse(page, 'GET', /^\/wallets\?page=1&page_size=1$/);
  await page.getByTestId('guest-continue').click();
  expect((await confirm).status()).toBe(200);
  await openTab(page, 'wallets', 'wallets-total');
  await expect(page.getByTestId('wallet-card-Example wallet')).toBeVisible();
  await expect(page.getByTestId(`wallet-card-${kept.name}`)).toBeVisible();
});

test('TC-96 A guest refused while using the app returns to sign-in, told the trial has ended', async ({ page }) => {
  await startGuest(page);
  await setStorage(page, { [KEY.token]: REFUSED_TOKEN, [KEY.savedToken]: REFUSED_TOKEN });

  const refused = page.waitForResponse((r) => r.url().includes('/api/v1/') && r.request().method() === 'GET');
  await page.reload();

  expect((await refused).status()).toBe(401);
  await expect(page.getByTestId('login-submit')).toBeVisible();
  await expect(page.getByTestId('guest-trial-ended')).toHaveText('Your guest trial has ended.');
  await expect(page.getByTestId('guest-continue')).toHaveCount(0);
});
