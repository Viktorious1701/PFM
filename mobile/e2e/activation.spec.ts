/** User Onboarding (activation) — specs/001-user-onboarding/test_cases.md, "UM: UI test cases". */
import { expect, test } from '@playwright/test';

import { call, invite, tokenOf, uid } from './support/api';
import { PASSWORD } from './support/env';
import { alert, apiResponse } from './support/ui';

/** The emailed link points at the dev web app; keep only path + query so
 * it opens against whatever baseURL the suite runs on. */
const local = (link: string) => {
  const u = new URL(link);
  return u.pathname + u.search;
};

test('TC-77 An invited member activates from the emailed link and can then sign in', async ({ page }) => {
  const email = `e2e-activate-${uid()}@example.com`;
  const link = await invite(email);

  const state = apiResponse(page, 'GET', /^\/users\/activate\?token=/);
  await page.goto(local(link));
  expect((await state).status()).toBe(200);
  await page.getByTestId('activate-name').fill('Linh Nguyen');
  await page.getByTestId('activate-password').fill(PASSWORD);
  const activated = apiResponse(page, 'POST', /^\/users\/activate$/);
  await page.getByTestId('activate-submit').click();
  expect((await activated).status()).toBe(200);
  await expect(page.getByTestId('activate-done')).toBeVisible();

  await page.getByTestId('activate-signin').click();
  await expect(page.getByTestId('login-submit')).toBeVisible();
  expect(new URL(page.url()).pathname).toBe('/');
  await page.getByTestId('login-email').fill(email);
  await page.getByTestId('login-password').fill(PASSWORD);
  await page.getByTestId('login-submit').click();
  await expect(page.getByTestId('total-balance')).toBeVisible();
});

test('TC-78 A password that breaks the policy is refused with the specific rule', async ({ page }) => {
  const email = `e2e-weakpw-${uid()}@example.com`;
  const link = await invite(email);
  await page.goto(local(link));
  await page.getByTestId('activate-name').fill('Weak Password');
  await page.getByTestId('activate-password').fill('weakpass');
  const refused = apiResponse(page, 'POST', /^\/users\/activate$/);
  await page.getByTestId('activate-submit').click();
  expect((await refused).status()).toBe(422);
  await expect(alert(page)).toHaveText(/Password must/);
  await expect(alert(page)).not.toHaveText('Request payload is invalid.');
  await expect(page.getByTestId('activate-name')).toBeVisible();

  // the link is still good: a valid password now activates it
  await page.getByTestId('activate-password').fill(PASSWORD);
  await page.getByTestId('activate-submit').click();
  await expect(page.getByTestId('activate-done')).toBeVisible();
});

test('TC-79 An already-used or unknown link says so before any typing', async ({ page }) => {
  const email = `e2e-used-${uid()}@example.com`;
  const link = await invite(email);
  const used = await call('POST', '/users/activate', undefined, { token: tokenOf(link), full_name: 'Used Link', password: PASSWORD });
  expect(used.status).toBe(200);

  for (const target of [local(link), '/activate?token=not-a-real-token']) {
    await page.goto(target);
    await expect(page.getByTestId('activate-unusable')).toBeVisible();
    await expect(page.getByTestId('activate-name')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Go to sign in' })).toBeVisible();
  }
});

test('TC-81 An invitation link that carries a server address uses that server', async ({ page }) => {
  const server = 'http://127.0.0.1:8000/api/v1';
  const state = apiResponse(page, 'GET', /^\/users\/activate\?token=/);
  await page.goto(`/activate?token=unknown-${uid()}&server=${encodeURIComponent(server)}`);
  const res = await state;
  expect(res.url().startsWith(`${server}/users/activate?token=`)).toBe(true);
  await expect(page.getByTestId('server-host')).toHaveText('127.0.0.1:8000');
  await expect(page.getByTestId('activate-unusable')).toBeVisible();
});
