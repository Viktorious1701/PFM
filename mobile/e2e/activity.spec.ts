/** Transaction Management — specs/006-transaction-management/test_cases.md, "TM: UI test cases". */
import { expect, test, type Page } from '@playwright/test';

import { createCategory, createTransaction, createWallet, newMember, uid, walletBalance } from './support/api';
import { alert, apiResponse, openTab, recordApi, signIn } from './support/ui';

/** The feed row for the transaction carrying `note`. */
const rowWith = (page: Page, note: string) => page.locator('[data-testid^="txn-row-"]', { hasText: note });

test('TC-127 Record an expense', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`, '1000000.00');
  const c = await createCategory(me.token, `Food ${uid()}`);
  await signIn(page, me);
  await openTab(page, 'activity', 'add-transaction');
  await page.getByTestId('add-transaction').click();
  await expect(page.getByTestId('txn-type-Expense')).toHaveAttribute('aria-checked', 'true');
  await page.getByTestId('txn-amount').fill('50.000');
  await page.getByTestId(`txn-wallet-${w.name}`).click();
  await page.getByTestId(`txn-category-${c.name}`).click();
  const note = `phở ${uid()}`;
  await page.getByTestId('txn-note').fill(note);
  const created = apiResponse(page, 'POST', /^\/transactions$/);
  await page.getByTestId('txn-submit').click();
  const res = await created;
  expect(res.status()).toBe(201);
  expect(res.request().postDataJSON()).toMatchObject({ wallet_id: w.id, category_id: c.id, amount: '50000.00', type: 'EXPENSE', note });
  await expect(page.locator('[data-testid^="txn-row-"]').first()).toContainText(note);
  await expect(rowWith(page, note)).toContainText('−50.000 đ');
  expect(await walletBalance(me.token, w.id)).toBe('950000.00');
});

test('TC-128 Record income', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`, '100000.00');
  const c = await createCategory(me.token, `Salary ${uid()}`, 'INCOME');
  await signIn(page, me);
  await openTab(page, 'activity', 'add-transaction');
  await page.getByTestId('add-transaction').click();
  await page.getByTestId('txn-type-Income').click();
  await page.getByTestId('txn-amount').fill('200.000');
  await page.getByTestId(`txn-wallet-${w.name}`).click();
  await page.getByTestId(`txn-category-${c.name}`).click();
  const note = `bonus ${uid()}`;
  await page.getByTestId('txn-note').fill(note);
  const created = apiResponse(page, 'POST', /^\/transactions$/);
  await page.getByTestId('txn-submit').click();
  expect((await created).status()).toBe(201);
  await expect(rowWith(page, note)).toContainText('+200.000 đ');
  expect(await walletBalance(me.token, w.id)).toBe('300000.00');
});

test('TC-129 An expense larger than the balance is refused', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`, '100000.00');
  const c = await createCategory(me.token, `Big ${uid()}`);
  await signIn(page, me);
  await openTab(page, 'activity', 'add-transaction');
  await page.getByTestId('add-transaction').click();
  await page.getByTestId('txn-amount').fill('500.000');
  await page.getByTestId(`txn-wallet-${w.name}`).click();
  await page.getByTestId(`txn-category-${c.name}`).click();
  const refused = apiResponse(page, 'POST', /^\/transactions$/);
  await page.getByTestId('txn-submit').click();
  expect((await refused).status()).toBe(409);
  await expect(alert(page)).not.toBeEmpty();
  await expect(page.getByText('No transactions yet.')).toBeVisible();
  expect(await walletBalance(me.token, w.id)).toBe('100000.00');
});

test('TC-130 A zero amount is caught before anything is sent', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const c = await createCategory(me.token, `Zero ${uid()}`);
  await signIn(page, me);
  await openTab(page, 'activity', 'add-transaction');
  await page.getByTestId('add-transaction').click();
  await page.getByTestId('txn-amount').fill('0');
  await page.getByTestId(`txn-wallet-${w.name}`).click();
  await page.getByTestId(`txn-category-${c.name}`).click();
  const api = recordApi(page);
  await page.getByTestId('txn-submit').click();
  await expect(alert(page)).toContainText('above zero');
  expect(api.count('POST', /^\/transactions$/)).toBe(0);
});

test('TC-131 The feed is newest first, grouped by day, and filters by wallet', async ({ page }) => {
  const me = await newMember();
  const a = await createWallet(me.token, `Alpha ${uid()}`);
  const b = await createWallet(me.token, `Beta ${uid()}`);
  const c = await createCategory(me.token, `Misc ${uid()}`);
  await createTransaction(me.token, a, c, '10000.00', 'first-in-alpha');
  await createTransaction(me.token, b, c, '20000.00', 'second-in-beta');
  await signIn(page, me);
  const list = apiResponse(page, 'GET', /^\/transactions\?/);
  await openTab(page, 'activity', 'add-transaction');
  expect((await list).status()).toBe(200);
  const rows = page.locator('[data-testid^="txn-row-"]');
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toContainText('second-in-beta');
  await expect(rows.nth(1)).toContainText('first-in-alpha');
  await expect(page.getByText('Today', { exact: true })).toBeVisible();

  const filtered = apiResponse(page, 'GET', new RegExp(`^/transactions\\?.*wallet_id=${a.id}`));
  await page.getByTestId(`filter-${a.name}`).click();
  expect((await filtered).status()).toBe(200);
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText('first-in-alpha');
});

test('TC-132 A user with no transactions sees an empty state', async ({ page }) => {
  await signIn(page, await newMember());
  await openTab(page, 'activity', 'add-transaction');
  await expect(page.getByText('No transactions yet.', { exact: false })).toBeVisible();
});

test('TC-133 Opening a transaction shows its details', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const c = await createCategory(me.token, `Coffee ${uid()}`);
  await createTransaction(me.token, w, c, '35000.00', 'flat white');
  await signIn(page, me);
  await openTab(page, 'activity', 'add-transaction');
  await rowWith(page, 'flat white').click();
  const detail = page.getByTestId('txn-detail');
  await expect(detail).toContainText('Expense');
  await expect(detail).toContainText(`${w.name} · VND`);
  await expect(detail).toContainText(/\d{2}:\d{2}/);
  await expect(detail).toContainText('flat white');
  await expect(page.getByTestId('txn-edit')).toBeVisible();
  await expect(page.getByTestId('txn-delete')).toBeVisible();
});

test('TC-134 Edit a transaction amount and note', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`, '1000000.00');
  const c = await createCategory(me.token, `Taxi ${uid()}`);
  const t = await createTransaction(me.token, w, c, '50000.00', 'ride');
  await signIn(page, me);
  await openTab(page, 'activity', 'add-transaction');
  await rowWith(page, 'ride').click();
  await page.getByTestId('txn-edit').click();
  await page.getByTestId('txn-edit-amount').fill('80.000');
  await page.getByTestId('txn-edit-note').fill('ride home');
  const updated = apiResponse(page, 'PATCH', new RegExp(`^/transactions/${t.id}$`));
  await page.getByTestId('txn-edit-save').click();
  const res = await updated;
  expect(res.status()).toBe(200);
  expect(res.request().postDataJSON()).toMatchObject({ amount: '80000.00', note: 'ride home' });
  await expect(rowWith(page, 'ride home')).toContainText('−80.000 đ');
  expect(await walletBalance(me.token, w.id)).toBe('920000.00');
});

test('TC-135 Change an expense into income', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const exp = await createCategory(me.token, `Refundable ${uid()}`);
  const inc = await createCategory(me.token, `Refunds ${uid()}`, 'INCOME');
  const t = await createTransaction(me.token, w, exp, '40000.00', 'turn me around');
  await signIn(page, me);
  await openTab(page, 'activity', 'add-transaction');
  await rowWith(page, 'turn me around').click();
  await page.getByTestId('txn-edit').click();
  await page.getByTestId('txn-edit-type-Income').click();
  await page.getByTestId(`txn-edit-category-${inc.name}`).click();
  const updated = apiResponse(page, 'PATCH', new RegExp(`^/transactions/${t.id}$`));
  await page.getByTestId('txn-edit-save').click();
  const res = await updated;
  expect(res.status()).toBe(200);
  expect(res.request().postDataJSON()).toMatchObject({ type: 'INCOME', category_id: inc.id });
  const row = rowWith(page, 'turn me around');
  await expect(row).toContainText('+40.000 đ');
  await expect(row).toContainText(inc.name);
});

test('TC-136 Delete a transaction after confirming', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`, '1000000.00');
  const c = await createCategory(me.token, `Oops ${uid()}`);
  const t = await createTransaction(me.token, w, c, '50000.00', 'delete me');
  expect(await walletBalance(me.token, w.id)).toBe('950000.00');
  await signIn(page, me);
  await openTab(page, 'activity', 'add-transaction');
  await rowWith(page, 'delete me').click();
  await page.getByTestId('txn-delete').click();
  const deleted = apiResponse(page, 'DELETE', new RegExp(`^/transactions/${t.id}$`));
  await page.getByTestId('txn-delete-confirm').click();
  expect((await deleted).status()).toBe(204);
  await expect(rowWith(page, 'delete me')).toHaveCount(0);
  expect(await walletBalance(me.token, w.id)).toBe('1000000.00');
});
