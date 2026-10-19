/** Category Management — specs/004-category-management/test_cases.md, "CM: UI test cases". */
import { expect, test } from '@playwright/test';

import { createCategory, createTransaction, createWallet, newMember, uid } from './support/api';
import { alert, apiResponse, openTab, recordApi, signIn } from './support/ui';

test('TC-94 Create a category while recording a transaction', async ({ page }) => {
  const me = await newMember();
  await createWallet(me.token, `Wallet ${uid()}`);
  await signIn(page, me);
  await openTab(page, 'activity', 'add-transaction');
  await page.getByTestId('add-transaction').click();
  await page.getByTestId('new-category').click();
  const name = `Snacks ${uid()}`;
  await page.getByTestId('new-category-name').fill(name);
  const created = apiResponse(page, 'POST', /^\/categories$/);
  await page.getByTestId('new-category-add').click();
  const res = await created;
  expect(res.status()).toBe(201);
  expect(res.request().postDataJSON()).toMatchObject({ name, type: 'EXPENSE' });
  await expect(page.getByTestId(`txn-category-${name}`)).toHaveAttribute('aria-checked', 'true');
});

test('TC-95 The Categories panel lists income and expense categories', async ({ page }) => {
  const me = await newMember();
  const inc = await createCategory(me.token, `Salary ${uid()}`, 'INCOME');
  const exp = await createCategory(me.token, `Rent ${uid()}`, 'EXPENSE');
  await signIn(page, me);
  await openTab(page, 'activity', 'manage-categories');
  await page.getByTestId('manage-categories').click();
  const panel = page.getByTestId('categories-panel');
  await expect(panel).toBeVisible();
  // headings render uppercase, so compare case-insensitively
  const text = (await panel.innerText()).replace(/\s+/g, ' ').toLowerCase();
  const at = (t: string) => text.indexOf(t.toLowerCase());
  expect(at('Income')).toBeGreaterThanOrEqual(0);
  expect(at(inc.name)).toBeGreaterThan(at('Income'));
  expect(at(inc.name)).toBeLessThan(at('Expense'));
  expect(at(exp.name)).toBeGreaterThan(at('Expense'));
});

test('TC-96 Rename a category', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const c = await createCategory(me.token, `Old ${uid()}`);
  await createTransaction(me.token, w, c, '10000.00', 'in old category');
  await signIn(page, me);
  await openTab(page, 'activity', 'manage-categories');
  await page.getByTestId('manage-categories').click();
  await page.getByTestId(`category-row-${c.name}`).getByRole('button').first().click();
  await page.getByTestId('category-rename').click();
  const renamed = `New ${uid()}`;
  await page.getByTestId('category-rename-field').fill(renamed);
  const updated = apiResponse(page, 'PATCH', new RegExp(`^/categories/${c.id}$`));
  await page.getByTestId('category-rename-save').click();
  expect((await updated).status()).toBe(200);
  await expect(page.getByTestId(`category-row-${renamed}`)).toBeVisible();
  await page.getByTestId('categories-done').click();
  await expect(page.getByText('in old category').locator('..')).toContainText(renamed);
});

test('TC-97 A blank category name is caught before anything is sent', async ({ page }) => {
  const me = await newMember();
  const c = await createCategory(me.token, `Keep ${uid()}`);
  await signIn(page, me);
  await openTab(page, 'activity', 'manage-categories');
  await page.getByTestId('manage-categories').click();
  await page.getByTestId(`category-row-${c.name}`).getByRole('button').first().click();
  await page.getByTestId('category-rename').click();
  await page.getByTestId('category-rename-field').fill('   ');
  const api = recordApi(page);
  await page.getByTestId('category-rename-save').click();
  await expect(alert(page)).toHaveText('A category needs a name.');
  expect(api.count('PATCH', /^\/categories\//)).toBe(0);
});

test('TC-98 Archive a category after confirming', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const c = await createCategory(me.token, `Gone ${uid()}`);
  await createTransaction(me.token, w, c, '20000.00', 'archived-cat txn');
  await signIn(page, me);
  await openTab(page, 'activity', 'manage-categories');
  await page.getByTestId('manage-categories').click();
  await page.getByTestId(`category-row-${c.name}`).getByRole('button').first().click();
  await page.getByTestId('category-archive').click();
  const archived = apiResponse(page, 'DELETE', new RegExp(`^/categories/${c.id}$`));
  await page.getByTestId('category-archive-confirm').click();
  expect((await archived).status()).toBe(200);
  await expect(page.getByTestId(`category-row-${c.name}`)).toHaveCount(0);
  await page.getByTestId('categories-done').click();

  await expect(page.getByText('archived-cat txn').locator('..')).toContainText('Archived category');
  await page.getByTestId('add-transaction').click();
  await expect(page.getByTestId(`txn-category-${c.name}`)).toHaveCount(0);
});
