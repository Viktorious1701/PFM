/** Wallet Management — specs/003-wallet-management/test_cases.md, "WM: UI test cases". */
import { expect, test } from '@playwright/test';

import { createCategory, createTransaction, createWallet, newMember, uid } from './support/api';
import { alert, apiResponse, openTab, recordApi, signIn } from './support/ui';

test('TC-91 Add a VND wallet with an opening balance', async ({ page }) => {
  const me = await newMember();
  await signIn(page, me);
  await openTab(page, 'wallets', 'add-wallet');
  await page.getByTestId('add-wallet').click();
  const name = `Ví ${uid()}`;
  await page.getByTestId('wallet-name').fill(name);
  await page.getByTestId('wallet-type-Cash').click();
  await expect(page.getByRole('radio', { name: 'VND' })).toHaveAttribute('aria-checked', 'true');
  await page.getByTestId('wallet-balance').fill('2.500.000');
  const created = apiResponse(page, 'POST', /^\/wallets$/);
  await page.getByTestId('wallet-submit').click();
  const res = await created;
  expect(res.status()).toBe(201);
  expect(res.request().postDataJSON()).toMatchObject({ name, type: 'Cash', currency: 'VND', initial_balance: '2500000.00' });
  await expect(page.getByTestId(`wallet-card-${name}`)).toContainText('2.500.000 đ');
  await expect(page.getByTestId('wallets-total')).toContainText('2.500.000 đ');
});

test('TC-92 An invalid opening balance is caught before anything is sent', async ({ page }) => {
  await signIn(page, await newMember());
  await openTab(page, 'wallets', 'add-wallet');
  await page.getByTestId('add-wallet').click();
  await page.getByTestId('wallet-name').fill('Bad balance');
  await page.getByTestId('wallet-balance').fill('12.5');
  const api = recordApi(page);
  await page.getByTestId('wallet-submit').click();
  await expect(alert(page)).toContainText('whole number');
  expect(api.count('POST', /^\/wallets$/)).toBe(0);
});

test('TC-93 The Wallets tab lists every wallet, or says there are none', async ({ page }) => {
  const empty = await newMember();
  await signIn(page, empty);
  await openTab(page, 'wallets', 'add-wallet');
  await expect(page.getByText('No wallets yet.', { exact: false })).toBeVisible();
  await page.getByTestId('sign-out').click();

  const me = await newMember();
  const a = await createWallet(me.token, `Alpha ${uid()}`, '100000.00');
  const b = await createWallet(me.token, `Beta ${uid()}`, '250000.00');
  await signIn(page, me);
  const list = apiResponse(page, 'GET', /^\/wallets\?/);
  await openTab(page, 'wallets', 'wallets-total');
  expect((await list).status()).toBe(200);
  await expect(page.getByTestId(`wallet-card-${a.name}`)).toContainText('100.000 đ');
  await expect(page.getByTestId(`wallet-card-${b.name}`)).toContainText('250.000 đ');
  await expect(page.getByTestId(`wallet-card-${a.name}`)).toContainText(/Bank · VND/i);
  await expect(page.getByTestId('wallets-total')).toContainText('350.000 đ');
});

test('TC-94 Opening a wallet shows its latest activity', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const c = await createCategory(me.token, `Food ${uid()}`);
  await createTransaction(me.token, w, c, '45000.00', 'lunch');
  await signIn(page, me);
  await openTab(page, 'wallets', `wallet-card-${w.name}`);
  await page.getByTestId(`wallet-card-${w.name}`).getByRole('button').first().click();
  const card = page.getByTestId(`wallet-card-${w.name}`);
  await expect(card).toContainText('Latest activity');
  await expect(card).toContainText(c.name);
  await expect(card).toContainText('45.000 đ');
  await expect(page.getByTestId('rename-wallet')).toBeVisible();
  await expect(page.getByTestId('archive-wallet')).toBeVisible();
});

test('TC-95 Rename a wallet', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Old ${uid()}`, '500000.00');
  await signIn(page, me);
  await openTab(page, 'wallets', `wallet-card-${w.name}`);
  await page.getByTestId(`wallet-card-${w.name}`).getByRole('button').first().click();
  await page.getByTestId('rename-wallet').click();
  const renamed = `New ${uid()}`;
  await page.getByTestId('rename-field').fill(renamed);
  const updated = apiResponse(page, 'PATCH', new RegExp(`^/wallets/${w.id}$`));
  await page.getByTestId('rename-save').click();
  expect((await updated).status()).toBe(200);
  const card = page.getByTestId(`wallet-card-${renamed}`);
  await expect(card).toContainText('500.000 đ');
  await expect(card).toContainText('VND');
});

test('TC-96 Archive a wallet after confirming', async ({ page }) => {
  const me = await newMember();
  const keep = await createWallet(me.token, `Keep ${uid()}`, '100000.00');
  const gone = await createWallet(me.token, `Gone ${uid()}`, '900000.00');
  await signIn(page, me);
  await openTab(page, 'wallets', `wallet-card-${gone.name}`);
  await page.getByTestId(`wallet-card-${gone.name}`).getByRole('button').first().click();
  await page.getByTestId('archive-wallet').click();
  const archived = apiResponse(page, 'DELETE', new RegExp(`^/wallets/${gone.id}$`));
  await page.getByTestId('archive-confirm').click();
  expect((await archived).status()).toBe(200);
  await expect(page.getByTestId(`wallet-card-${gone.name}`)).toHaveCount(0);
  await expect(page.getByTestId(`wallet-card-${keep.name}`)).toBeVisible();
  await expect(page.getByTestId('wallets-total')).toContainText('100.000 đ');
});
