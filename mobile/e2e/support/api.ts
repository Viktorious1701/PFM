/**
 * Arrange-and-check helpers that talk to the backend directly. Tests use
 * these to set up the data a screen needs and to confirm what a screen
 * changed; the behaviour under test itself is always driven through the UI.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';

import { API_URL, OUTBOX_DIR, PASSWORD } from './env';

export type Account = { email: string; password: string; token: string };
type Json = Record<string, unknown>;

let seq = 0;
/** A short unique suffix for names and emails within this run. */
export function uid(): string {
  seq += 1;
  return `${Date.now().toString(36)}${process.pid.toString(36)}${seq}`;
}

export async function call<T = Json>(method: string, route: string, token?: string, body?: unknown): Promise<{ status: number; data: T }> {
  const res = await fetch(API_URL + route, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  return { status: res.status, data: (text ? JSON.parse(text) : null) as T };
}

async function ok<T = Json>(method: string, route: string, token?: string, body?: unknown): Promise<T> {
  const r = await call<T>(method, route, token, body);
  if (r.status >= 300) throw new Error(`${method} ${route} -> ${r.status} ${JSON.stringify(r.data)}`);
  return r.data;
}

export async function login(email: string, password = PASSWORD): Promise<string> {
  return (await ok<{ access_token: string }>('POST', '/auth/login', undefined, { email, password })).access_token;
}

/** This run's ADMIN, created once in global-setup. */
export async function admin(): Promise<Account> {
  const email = process.env.E2E_ADMIN_EMAIL;
  if (!email) throw new Error('E2E_ADMIN_EMAIL missing — global-setup did not run');
  return { email, password: PASSWORD, token: await login(email) };
}

/** The activation link the backend wrote to the outbox for `email`. */
export function outboxLink(email: string): string {
  const files = readdirSync(OUTBOX_DIR)
    .filter((f) => f.endsWith(`_${email}.eml`))
    .sort((a, b) => statSync(path.join(OUTBOX_DIR, b)).mtimeMs - statSync(path.join(OUTBOX_DIR, a)).mtimeMs);
  if (!files.length) throw new Error(`No outbox message for ${email} in ${OUTBOX_DIR}`);
  const m = readFileSync(path.join(OUTBOX_DIR, files[0]), 'utf8').match(/https?:\/\/\S+\/activate\?token=\S+/);
  if (!m) throw new Error(`No activation link in the outbox message for ${email}`);
  return m[0];
}

export function tokenOf(link: string): string {
  return new URL(link).searchParams.get('token') ?? '';
}

/** Invite `email` as this run's ADMIN; returns the emailed link. */
export async function invite(email: string): Promise<string> {
  const a = await admin();
  await ok('POST', '/users/invite', a.token, { email });
  return outboxLink(email);
}

/** A brand-new ACTIVE USER, invited and activated through the API — every
 * test that needs a signed-in person gets its own, so tests never share data. */
export async function newMember(name = 'E2E Member'): Promise<Account> {
  const email = `e2e-${uid()}@example.com`;
  const link = await invite(email);
  await ok('POST', '/users/activate', undefined, { token: tokenOf(link), full_name: name, password: PASSWORD });
  return { email, password: PASSWORD, token: await login(email) };
}

export type Wallet = { id: string; name: string; currency: string; balance: string };
export type Category = { id: string; name: string; type: 'INCOME' | 'EXPENSE' };

export const createWallet = (t: string, name: string, initial = '1000000.00', currency = 'VND') =>
  ok<Wallet>('POST', '/wallets', t, { name, type: 'Bank', currency, initial_balance: initial });
export const createCategory = (t: string, name: string, type: 'INCOME' | 'EXPENSE' = 'EXPENSE') =>
  ok<Category>('POST', '/categories', t, { name, type });
export const createTransaction = (t: string, wallet: Wallet, category: Category, amount: string, note: string | null = null) =>
  ok<{ id: string }>('POST', '/transactions', t, { wallet_id: wallet.id, category_id: category.id, amount, type: category.type, note });
export const createBudget = (t: string, wallet: Wallet, category: Category, limit: string) =>
  ok<{ id: string }>('POST', '/budgets', t, { wallet_id: wallet.id, category_id: category.id, amount_limit: limit });
export async function walletBalance(t: string, id: string): Promise<string> {
  return (await ok<Wallet>('GET', `/wallets/${id}`, t)).balance;
}
