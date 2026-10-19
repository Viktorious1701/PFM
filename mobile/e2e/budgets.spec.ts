/** Budget Management — specs/005-budget-management/test_cases.md, "BM: UI test cases". */
import { expect, test } from '@playwright/test';

import { call, createBudget, createCategory, createTransaction, createWallet, newMember, uid } from './support/api';
import { alert, apiResponse, openTab, recordApi, signIn } from './support/ui';

test('TC-97 Add a monthly budget', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const c = await createCategory(me.token, `Groceries ${uid()}`);
  await signIn(page, me);
  await openTab(page, 'budgets', 'add-budget');
  await page.getByTestId('add-budget').click();
  await page.getByTestId(`budget-wallet-${w.name}`).click();
  await page.getByTestId(`budget-category-${c.name}`).click();
  await page.getByTestId('budget-limit').fill('3.000.000');
  const created = apiResponse(page, 'POST', /^\/budgets$/);
  await page.getByTestId('budget-submit').click();
  const res = await created;
  expect(res.status()).toBe(201);
  expect(res.request().postDataJSON()).toMatchObject({ wallet_id: w.id, category_id: c.id, amount_limit: '3000000.00' });
  const card = page.getByTestId(`budget-${c.name}`);
  await expect(card).toContainText(w.name);
  await expect(card).toContainText('On track');
  await expect(card).toContainText('0%');
  await expect(card).toContainText('3.000.000 đ');
});

test('TC-98 A second budget for the same wallet and category is refused', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const c = await createCategory(me.token, `Dining ${uid()}`);
  await createBudget(me.token, w, c, '500000.00');
  await signIn(page, me);
  await openTab(page, 'budgets', `budget-${c.name}`);
  await page.getByTestId('add-budget').click();
  await page.getByTestId(`budget-wallet-${w.name}`).click();
  await page.getByTestId(`budget-category-${c.name}`).click();
  await page.getByTestId('budget-limit').fill('600.000');
  const refused = apiResponse(page, 'POST', /^\/budgets$/);
  await page.getByTestId('budget-submit').click();
  expect((await refused).status()).toBe(409);
  await expect(alert(page)).not.toBeEmpty();
  await expect(page.getByTestId(`budget-${c.name}`)).toHaveCount(1);
});

test('TC-99 A zero limit is caught before anything is sent', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const c = await createCategory(me.token, `Fuel ${uid()}`);
  await signIn(page, me);
  await openTab(page, 'budgets', 'add-budget');
  await page.getByTestId('add-budget').click();
  await page.getByTestId(`budget-wallet-${w.name}`).click();
  await page.getByTestId(`budget-category-${c.name}`).click();
  await page.getByTestId('budget-limit').fill('0');
  const api = recordApi(page);
  await page.getByTestId('budget-submit').click();
  await expect(alert(page)).toContainText('above zero');
  expect(api.count('POST', /^\/budgets$/)).toBe(0);
});

test('TC-100 Each budget shows spending, percentage and status', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`, '10000000.00');
  const cases = [
    { spent: '50000.00', label: 'On track', pct: '50%' },
    { spent: '90000.00', label: 'Close to limit', pct: '90%' },
    { spent: '120000.00', label: 'Over limit', pct: '120%' },
  ];
  const cats = [];
  for (const k of cases) {
    const c = await createCategory(me.token, `Cat ${uid()}`);
    await createBudget(me.token, w, c, '100000.00');
    await createTransaction(me.token, w, c, k.spent);
    cats.push(c);
  }
  await signIn(page, me);
  const list = apiResponse(page, 'GET', /^\/budgets\?/);
  await openTab(page, 'budgets', `budget-${cats[0].name}`);
  expect((await list).status()).toBe(200);
  for (const [i, k] of cases.entries()) {
    const card = page.getByTestId(`budget-${cats[i].name}`);
    await expect(card).toContainText(k.label);
    await expect(card).toContainText(k.pct);
    await expect(card).toContainText('100.000 đ');
  }
});

test('TC-101 Change a budget limit', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const c = await createCategory(me.token, `Transit ${uid()}`);
  const b = await createBudget(me.token, w, c, '400000.00');
  await createTransaction(me.token, w, c, '200000.00');
  await signIn(page, me);
  await openTab(page, 'budgets', `budget-${c.name}`);
  const card = page.getByTestId(`budget-${c.name}`);
  await expect(card).toContainText('50%');
  await card.getByRole('button').first().click();
  await page.getByTestId('budget-edit').click();
  await page.getByTestId('budget-limit-edit').fill('250.000');
  const updated = apiResponse(page, 'PATCH', new RegExp(`^/budgets/${b.id}$`));
  await page.getByTestId('budget-limit-save').click();
  const res = await updated;
  expect(res.status()).toBe(200);
  expect(res.request().postDataJSON()).toEqual({ amount_limit: '250000.00' });
  await expect(card).toContainText('80%');
  await expect(card).toContainText('Close to limit');
  await expect(page.getByTestId('budget-limit-edit')).toHaveCount(0);
});

test('TC-102 Delete a budget after confirming', async ({ page }) => {
  const me = await newMember();
  const w = await createWallet(me.token, `Wallet ${uid()}`);
  const c = await createCategory(me.token, `Gifts ${uid()}`);
  const b = await createBudget(me.token, w, c, '300000.00');
  await createTransaction(me.token, w, c, '30000.00', 'gift');
  await signIn(page, me);
  await openTab(page, 'budgets', `budget-${c.name}`);
  await page.getByTestId(`budget-${c.name}`).getByRole('button').first().click();
  await page.getByTestId('budget-delete').click();
  const deleted = apiResponse(page, 'DELETE', new RegExp(`^/budgets/${b.id}$`));
  await page.getByTestId('budget-delete-confirm').click();
  expect((await deleted).status()).toBe(204);
  await expect(page.getByTestId(`budget-${c.name}`)).toHaveCount(0);
  const txns = await call<{ items: { note: string }[] }>('GET', `/transactions?wallet_id=${w.id}`, me.token);
  expect(txns.data.items.map((t) => t.note)).toContain('gift');
});
