/** System Security — specs/002-system-security/test_cases.md, "SS: UI test cases". */
import { expect, test } from '@playwright/test';

import { invite, newMember, uid } from './support/api';
import { PASSWORD } from './support/env';
import { alert, apiResponse, recordApi, signIn } from './support/ui';

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
