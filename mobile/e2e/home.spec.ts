/**
 * Home tab analysis, one block per currency — specs/007-financial-reporting/
 * test_cases.md, "FR: UI test cases" (FR-US-03, plan.md T-09). Behaviour
 * only: which blocks exist, in what order, what text and which categories
 * each holds. No colour, size, width or position is asserted (QF-12).
 */
import { expect, test, type Page } from '@playwright/test';

import { createCategory, createTransaction, createWallet, newMember, uid } from './support/api';
import { apiResponse, signIn } from './support/ui';

/** The currency blocks on screen, in document order (`report-VND`, …). */
async function blockIds(page: Page): Promise<string[]> {
  const ids = await page
    .locator('[data-testid^="report-"]')
    .evaluateAll((els) => els.map((e) => e.getAttribute('data-testid') ?? ''));
  return ids.filter((id) => /^report-[A-Z]{3}$/.test(id));
}

/** A member with a VND wallet spending 100.000 đ and a USD wallet spending $20.00. */
async function twoCurrencyMember() {
  const me = await newMember();
  const vnd = await createWallet(me.token, `Ví ${uid()}`, '1000000.00', 'VND');
  const usd = await createWallet(me.token, `Dollars ${uid()}`, '500.00', 'USD');
  const food = await createCategory(me.token, `Food ${uid()}`);
  const travel = await createCategory(me.token, `Travel ${uid()}`);
  await createTransaction(me.token, vnd, food, '100000.00');
  await createTransaction(me.token, usd, travel, '20.00');
  return { me, food, travel };
}

test('TC-50 Home shows one block per currency, in the report\'s order', async ({ page }) => {
  const { me } = await twoCurrencyMember();
  const summary = apiResponse(page, 'GET', /^\/reports\/summary$/);
  await signIn(page, me);
  expect((await summary).status()).toBe(200);

  await expect(page.getByTestId('report-USD')).toBeVisible();
  await expect(page.getByTestId('report-VND')).toBeVisible();
  expect(await blockIds(page)).toEqual(['report-USD', 'report-VND']);
  for (const cur of ['USD', 'VND']) {
    await expect(page.getByTestId(`report-${cur}-currency`)).toHaveText(cur);
    const block = page.getByTestId(`report-${cur}`);
    await expect(block.getByTestId(`report-${cur}-flow-Income`)).toBeVisible();
    await expect(block.getByTestId(`report-${cur}-flow-Expenses`)).toBeVisible();
    await expect(block.getByTestId(`report-${cur}-net-savings`)).toBeVisible();
    await expect(block.getByTestId(`report-${cur}-donut`)).toBeVisible();
  }
});

test('TC-51 Each block\'s amounts are in its own currency', async ({ page }) => {
  const { me } = await twoCurrencyMember();
  await signIn(page, me);

  const usd = page.getByTestId('report-USD');
  await expect(usd.getByTestId('report-USD-flow-Expenses')).toContainText('$20.00');
  await expect(usd).not.toContainText('đ');

  const vnd = page.getByTestId('report-VND');
  await expect(vnd.getByTestId('report-VND-flow-Expenses')).toContainText('100.000 đ');
  await expect(vnd).not.toContainText('$');
});

test('TC-52 Each block\'s breakdown lists only its own currency\'s categories', async ({ page }) => {
  const { me, food, travel } = await twoCurrencyMember();
  await signIn(page, me);

  const vndDonut = page.getByTestId('report-VND-donut');
  const usdDonut = page.getByTestId('report-USD-donut');
  await expect(vndDonut.getByTestId(`category-${food.name}`)).toBeVisible();
  await expect(usdDonut.getByTestId(`category-${travel.name}`)).toBeVisible();
  await expect(vndDonut).not.toContainText(travel.name);
  await expect(usdDonut).not.toContainText(food.name);
});

test('TC-53 A single held currency with no activity shows one zero block', async ({ page }) => {
  const me = await newMember();
  await createWallet(me.token, `Ví ${uid()}`, '0.00', 'VND');
  await signIn(page, me);

  await expect(page.getByTestId('report-VND')).toBeVisible();
  expect(await blockIds(page)).toEqual(['report-VND']);
  await expect(page.getByTestId('report-VND-currency')).toHaveText('VND');
  await expect(page.getByTestId('report-VND-flow-Income')).toHaveText(/^Income\s*0 đ$/);
  await expect(page.getByTestId('report-VND-flow-Expenses')).toHaveText(/^Expenses\s*0 đ$/);
  await expect(page.getByTestId('report-VND-donut')).toContainText('No spending recorded this month.');
});

test('TC-54 A user with nothing to report sees the empty message', async ({ page }) => {
  const me = await newMember();
  const summary = apiResponse(page, 'GET', /^\/reports\/summary$/);
  await signIn(page, me);
  expect((await summary).status()).toBe(200);

  await expect(page.getByTestId('report-empty')).toContainText('No income or expenses recorded in');
  expect(await blockIds(page)).toEqual([]);
});
