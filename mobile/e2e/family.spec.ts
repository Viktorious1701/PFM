/** User Onboarding (invite, members) — specs/001-user-onboarding/test_cases.md, "UM: UI test cases". */
import { expect, test } from '@playwright/test';

import { admin, invite, newMember, uid } from './support/api';
import { alert, apiResponse, openTab, recordApi, signIn } from './support/ui';

test('TC-73 ADMIN invites a family member from the Family tab', async ({ page }) => {
  const a = await admin();
  await signIn(page, a);
  await openTab(page, 'family', 'invite-form');
  const email = `e2e-invitee-${uid()}@example.com`;
  await page.getByTestId('invite-email').fill(email);
  const sent = apiResponse(page, 'POST', /^\/users\/invite$/);
  await page.getByTestId('invite-submit').click();
  expect((await sent).status()).toBe(201);
  await expect(page.getByText(new RegExp(`invitation.*sent|${email.replace(/[.+]/g, '\\$&')}`, 'i')).first()).toBeVisible();
  await expect(page.getByTestId(`member-${email}`)).toContainText('Invited');
});

test('TC-74 A malformed email is caught before anything is sent', async ({ page }) => {
  await signIn(page, await admin());
  await openTab(page, 'family', 'invite-form');
  const api = recordApi(page);
  await page.getByTestId('invite-email').fill('not-an-email');
  await page.getByTestId('invite-submit').click();
  await expect(alert(page)).toContainText('name@example.com');
  expect(api.count('POST', /^\/users\/invite$/)).toBe(0);
});

test('TC-75 Inviting an address that is already ACTIVE shows the server refusal', async ({ page }) => {
  const existing = await newMember();
  await signIn(page, await admin());
  await openTab(page, 'family', 'invite-form');
  await page.getByTestId('invite-email').fill(existing.email);
  const sent = apiResponse(page, 'POST', /^\/users\/invite$/);
  await page.getByTestId('invite-submit').click();
  expect((await sent).status()).toBe(409);
  await expect(alert(page)).not.toBeEmpty();
});

test('TC-76 A non-ADMIN has no Family tab', async ({ page }) => {
  await signIn(page, await newMember());
  await expect(page.getByRole('tab')).toHaveText(['Home', 'Wallets', 'Activity', 'Budgets']);
  await expect(page.getByTestId('tab-family')).toHaveCount(0);
});

test('TC-80 The Family tab lists members of every status', async ({ page }) => {
  const active = await newMember();
  const pending = `e2e-pending-${uid()}@example.com`;
  await invite(pending);
  await signIn(page, await admin());
  const list = apiResponse(page, 'GET', /^\/users\?/);
  await openTab(page, 'family', 'invite-form');
  expect((await list).status()).toBe(200);
  await expect(page.getByTestId(`member-${active.email}`)).toContainText('Active');
  await expect(page.getByTestId(`member-${pending}`)).toContainText('Invited');
  await expect(page.getByText(/\d+ members?/i)).toBeVisible();
});
