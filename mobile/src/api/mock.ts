/**
 * Fixture layer.
 *
 * The backend has no routes yet, so without this the UI cannot be exercised at
 * all. Each branch below is keyed to an acceptance criterion or edge case in
 * specs/001-user-onboarding/spec.md, so driving the invite form through the
 * addresses in MOCK_INVITE_CASES walks every documented outcome.
 *
 * This is a prototype aid, NOT a test double standing in for a test. No TC in
 * test_cases.md is satisfied by anything in this file.
 */
import { sumMoney } from '../utils/money';
import { ApiError, ErrorCode } from './errors';
import type {
  ActivateResponse,
  CategoryCreate,
  CategoryRead,
  InvitationRead,
  LoginResponse,
  Page,
  SummaryReportRead,
  TransactionCreate,
  TransactionListParams,
  TransactionRead,
  UserRead,
  WalletCreate,
  WalletRead,
} from './types';

/** Perceptible latency, so pending/disabled states are actually visible. */
const LATENCY_MS = 550;

const delay = (ms = LATENCY_MS) => new Promise<void>((r) => setTimeout(r, ms));

/**
 * Mirrors the backend's max email length (spec EC-04, test_cases QF-08).
 * 320 inclusive — matches `InviteCreate.email` max_length, so 321 is rejected.
 */
const MAX_EMAIL_LENGTH = 320;

/** Deliberately permissive — the server is the source of truth (VL-01). */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/**
 * Normalisation the backend performs before any comparison: trimmed and
 * case-folded, so one mailbox maps to one account (spec FR-03 / BR-01).
 * This is what makes EC-01 work — `" Active@Example.com "` collides.
 */
export function normalizeEmail(raw: string): string {
  return raw.trim().toLowerCase();
}

/** The addresses that drive each branch. Rendered in the UI so it is discoverable. */
export const MOCK_INVITE_CASES: { email: string; outcome: string; ref: string }[] = [
  { email: 'new@example.com', outcome: 'Invitation sent', ref: 'AC-01' },
  { email: 'active@example.com', outcome: 'Already active → 409', ref: 'AC-02' },
  { email: 'Active@Example.com', outcome: 'Same address, different case → 409', ref: 'EC-01' },
  { email: 'pending@example.com', outcome: 'Re-invited, new 24h token', ref: 'EC-02' },
  { email: 'not-an-email', outcome: 'Invalid format', ref: 'AC-03' },
  { email: 'forbidden@example.com', outcome: 'Not an ADMIN → 403', ref: 'AC-04' },
  { email: 'noauth@example.com', outcome: 'Credentials rejected → 401', ref: 'AC-05' },
  { email: 'smtpdown@example.com', outcome: 'Mail delivery failed → 502', ref: 'EC-07' },
  // 321 characters — one past the inclusive 320 maximum, matching test_cases TC-09.
  {
    email: 'a'.repeat(321 - '@example.com'.length) + '@example.com',
    outcome: 'Too long → 422',
    ref: 'EC-04',
  },
];

let idCounter = 1000;
const nextId = () => `e3a89047-bf1b-4f81-8b38-${(idCounter++).toString().padStart(12, '0')}`;

/** Expiry exactly 24 hours out (spec FR-09 / AC-06). */
function expiresIn24h(): string {
  return new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
}

export async function mockInviteUser(rawEmail: string): Promise<InvitationRead> {
  await delay();

  // FR-02: format is validated before any other processing.
  if (rawEmail.trim().length > MAX_EMAIL_LENGTH) {
    throw new ApiError(
      ErrorCode.VALIDATION_ERROR,
      'The submitted data failed validation.',
      422,
      { email: `Email address must be at most ${MAX_EMAIL_LENGTH} characters.` },
    );
  }

  const email = normalizeEmail(rawEmail);

  if (!EMAIL_RE.test(email)) {
    throw new ApiError(
      ErrorCode.VALIDATION_ERROR,
      'The submitted data failed validation.',
      422,
      { email: 'Please enter a valid email address' },
    );
  }

  switch (email) {
    // AC-05 — evaluated before the payload, hence checked early here too (FR-15).
    case 'noauth@example.com':
      throw new ApiError(
        ErrorCode.NOT_AUTHENTICATED,
        'Authentication credentials were not provided or are no longer valid.',
        401,
      );

    // AC-04 — authenticated, but not an ADMIN (FR-14).
    case 'forbidden@example.com':
      throw new ApiError(
        ErrorCode.FORBIDDEN,
        'Only an administrator can invite users.',
        403,
      );

    // AC-02 / EC-01 / EC-05 — an ACTIVE account already owns this address (FR-04).
    case 'active@example.com':
      throw new ApiError(
        ErrorCode.USER_EMAIL_ALREADY_ACTIVE,
        'An account with this email already exists',
        409,
        { email },
      );

    // EC-07 — no mail credentials, so a failure is surfaced rather than a false success (FR-20, SC-09).
    case 'smtpdown@example.com':
      throw new ApiError(
        ErrorCode.EMAIL_DELIVERY_FAILED,
        'The invitation could not be emailed. Please try again.',
        502,
      );

    // EC-02 / EC-03 — a PENDING account is re-invitable; the prior token stops working (FR-11, BR-03).
    case 'pending@example.com':
      return {
        id: nextId(),
        email,
        status: 'PENDING',
        message: 'A new invitation has been sent. The previous link no longer works.',
        token_expires_at: expiresIn24h(),
        created_at: new Date().toISOString(),
      };

    // AC-01 — the happy path (FR-05, FR-16).
    default:
      return {
        id: nextId(),
        email,
        status: 'PENDING',
        message: 'Invitation sent successfully',
        token_expires_at: expiresIn24h(),
        created_at: new Date().toISOString(),
      };
  }
}

const MOCK_USERS: UserRead[] = [
  {
    id: 'e3a89047-bf1b-4f81-8b38-8c114fef6f82',
    email: 'admin@example.com',
    full_name: 'An Dang',
    status: 'ACTIVE',
    role: 'ADMIN',
    created_at: '2026-07-01T09:12:00Z',
  },
  {
    id: 'a1b2c3d4-0000-4f81-8b38-8c114fef6f83',
    email: 'jane.doe@example.com',
    full_name: 'Jane Doe',
    status: 'ACTIVE',
    role: 'USER',
    created_at: '2026-07-14T14:03:00Z',
  },
  {
    id: 'a1b2c3d4-0000-4f81-8b38-8c114fef6f84',
    email: 'pending@example.com',
    full_name: null,
    status: 'PENDING',
    role: 'USER',
    created_at: '2026-07-29T18:40:00Z',
  },
  {
    id: 'a1b2c3d4-0000-4f81-8b38-8c114fef6f85',
    email: 'former.member@example.com',
    full_name: 'Alex Tran',
    status: 'DEACTIVATED',
    role: 'USER',
    created_at: '2026-05-02T11:22:00Z',
  },
];

export async function mockListUsers(): Promise<Page<UserRead>> {
  await delay(350);
  return { items: MOCK_USERS, page: 1, page_size: 25, total: MOCK_USERS.length };
}

export const MOCK_ADMIN: UserRead = MOCK_USERS[0];

/**
 * SS-US-01. `pending@example.com` demonstrates SDS §5.1.1 AC-2 — a PENDING
 * account cannot log in until activated (spec BR-06).
 */
export async function mockLogin(rawEmail: string, password: string): Promise<LoginResponse> {
  await delay();
  const email = normalizeEmail(rawEmail);

  if (!password) {
    throw new ApiError(ErrorCode.VALIDATION_ERROR, 'The submitted data failed validation.', 422, {
      password: 'Password is required.',
    });
  }

  if (email === 'pending@example.com') {
    throw new ApiError(
      ErrorCode.ACCOUNT_NOT_ACTIVATED,
      'Your account is not activated. Please check your email invitation.',
      403,
    );
  }

  if (email === 'wrong@example.com') {
    throw new ApiError(ErrorCode.INVALID_CREDENTIALS, 'The email or password is incorrect.', 401);
  }

  const isAdmin = email === MOCK_ADMIN.email || email === 'admin@example.com';
  return {
    access_token: 'mock.jwt.token',
    token_type: 'bearer',
    expires_in: 3600,
    role: isAdmin ? 'ADMIN' : 'USER',
  };
}

/** UM-US-02. `expired` demonstrates the derived-expiry rule (SDS §2.4.2, BR-04). */
export async function mockActivate(token: string): Promise<ActivateResponse> {
  await delay();

  if (!token) {
    throw new ApiError(ErrorCode.VALIDATION_ERROR, 'The submitted data failed validation.', 422, {
      token: 'This activation link is missing its token.',
    });
  }

  if (token === 'expired') {
    throw new ApiError(
      ErrorCode.INVITATION_TOKEN_EXPIRED,
      'The provided invitation link has expired. Please request a new invitation.',
      400,
    );
  }

  return { status: 'SUCCESS', message: 'Account activated successfully. You may now log in.' };
}

/** Shared pagination slicer for every list-style mock below — mirrors the
 * server's `Page<T>` envelope shape exactly. */
function paginate<T>(items: T[], page: number, pageSize: number): Page<T> {
  const start = (page - 1) * pageSize;
  return { items: items.slice(start, start + pageSize), page, page_size: pageSize, total: items.length };
}

// ---- Wallets (WM) ----------------------------------------------------------
//
// The 8-wallet dataset from the approved "Filed Folders" mockup
// (design-explore/wallets.html), reused verbatim so mock mode previews the
// real screen's folder-grouping (by `type`) and same-currency subtotals
// faithfully — including a mixed-currency pair (EUR/HKD) and two negative
// CREDIT balances.

export const MOCK_WALLETS: WalletRead[] = [
  { id: 'wallet-main-checking', user_id: MOCK_ADMIN.id, name: 'Main Checking', type: 'BANK', currency: 'USD', balance: '1250.75' },
  { id: 'wallet-petty-cash', user_id: MOCK_ADMIN.id, name: 'Petty Cash', type: 'CASH', currency: 'USD', balance: '84.00' },
  { id: 'wallet-travel-rewards', user_id: MOCK_ADMIN.id, name: 'Travel Rewards', type: 'CREDIT', currency: 'USD', balance: '-320.50' },
  { id: 'wallet-emergency-fund', user_id: MOCK_ADMIN.id, name: 'Emergency Fund', type: 'SAVINGS', currency: 'USD', balance: '5400.00' },
  { id: 'wallet-household-cash', user_id: MOCK_ADMIN.id, name: 'Household Cash', type: 'CASH', currency: 'USD', balance: '62.50' },
  { id: 'wallet-euro-travel-card', user_id: MOCK_ADMIN.id, name: 'Euro Travel Card', type: 'BANK', currency: 'EUR', balance: '430.20' },
  { id: 'wallet-store-credit-card', user_id: MOCK_ADMIN.id, name: 'Store Credit Card', type: 'CREDIT', currency: 'USD', balance: '-145.00' },
  { id: 'wallet-hk-dollar-pocket', user_id: MOCK_ADMIN.id, name: 'HK Dollar Pocket', type: 'CASH', currency: 'HKD', balance: '1200.00' },
];

export async function mockListWallets(page: number, pageSize: number): Promise<Page<WalletRead>> {
  await delay();
  return paginate(MOCK_WALLETS, page, pageSize);
}

export async function mockCreateWallet(payload: WalletCreate): Promise<WalletRead> {
  await delay();
  const wallet: WalletRead = {
    id: nextId(),
    user_id: MOCK_ADMIN.id,
    name: payload.name,
    type: payload.type,
    currency: payload.currency,
    balance: payload.initial_balance,
  };
  MOCK_WALLETS.push(wallet);
  return wallet;
}

// ---- Categories (CM) --------------------------------------------------------
//
// The 7 categories this app's demo data (this file, the Dashboard's own
// DEMO.budgets, and the mockups) names anywhere: the 6 the "Carbon-Copy
// Receipt Feed" transaction feed below actually posts against, plus "Dining
// Out" (design-explore/summary.html's deficit-scenario swatch) so the
// DiningGlyph mapping has a real category to resolve in mock mode too.

export const MOCK_CATEGORIES: CategoryRead[] = [
  { id: 'category-groceries', user_id: MOCK_ADMIN.id, name: 'Groceries', type: 'EXPENSE' },
  { id: 'category-transport', user_id: MOCK_ADMIN.id, name: 'Transport', type: 'EXPENSE' },
  { id: 'category-salary', user_id: MOCK_ADMIN.id, name: 'Salary', type: 'INCOME' },
  { id: 'category-rent', user_id: MOCK_ADMIN.id, name: 'Rent', type: 'EXPENSE' },
  { id: 'category-utilities', user_id: MOCK_ADMIN.id, name: 'Utilities', type: 'EXPENSE' },
  { id: 'category-entertainment', user_id: MOCK_ADMIN.id, name: 'Entertainment', type: 'EXPENSE' },
  { id: 'category-dining-out', user_id: MOCK_ADMIN.id, name: 'Dining Out', type: 'EXPENSE' },
];

export async function mockListCategories(page: number, pageSize: number): Promise<Page<CategoryRead>> {
  await delay();
  return paginate(MOCK_CATEGORIES, page, pageSize);
}

export async function mockCreateCategory(payload: CategoryCreate): Promise<CategoryRead> {
  await delay();
  const category: CategoryRead = {
    id: nextId(),
    user_id: MOCK_ADMIN.id,
    name: payload.name,
    type: payload.type,
  };
  MOCK_CATEGORIES.push(category);
  return category;
}

// ---- Transactions (TM) -------------------------------------------------------
//
// The 14-transaction dataset from the approved "Carbon-Copy Receipt Feed"
// mockup (design-explore/transactions.html), reused verbatim — newest
// first, matching both that mockup's own order and a realistic feed's.
// Wallet/category names there resolve directly against MOCK_WALLETS/
// MOCK_CATEGORIES above (the mockups were built cross-consistently).

export const MOCK_TRANSACTIONS: TransactionRead[] = [
  { id: 'transaction-01', wallet_id: 'wallet-main-checking', category_id: 'category-groceries', amount: '50.00', type: 'EXPENSE', timestamp: '2026-09-28T09:47:00Z', note: 'Weekly groceries' },
  { id: 'transaction-02', wallet_id: 'wallet-main-checking', category_id: 'category-entertainment', amount: '18.50', type: 'EXPENSE', timestamp: '2026-09-27T19:15:00Z', note: 'Movie night' },
  { id: 'transaction-03', wallet_id: 'wallet-petty-cash', category_id: 'category-transport', amount: '12.00', type: 'EXPENSE', timestamp: '2026-09-27T08:02:00Z', note: 'Bus pass top-up' },
  { id: 'transaction-04', wallet_id: 'wallet-main-checking', category_id: 'category-utilities', amount: '220.00', type: 'EXPENSE', timestamp: '2026-09-26T14:30:00Z', note: 'Electricity bill' },
  { id: 'transaction-05', wallet_id: 'wallet-main-checking', category_id: 'category-entertainment', amount: '34.20', type: 'EXPENSE', timestamp: '2026-09-25T20:10:00Z', note: null },
  { id: 'transaction-06', wallet_id: 'wallet-petty-cash', category_id: 'category-transport', amount: '9.80', type: 'EXPENSE', timestamp: '2026-09-24T07:45:00Z', note: 'Grab ride to office' },
  { id: 'transaction-07', wallet_id: 'wallet-main-checking', category_id: 'category-groceries', amount: '65.40', type: 'EXPENSE', timestamp: '2026-09-22T18:00:00Z', note: 'Market run' },
  { id: 'transaction-08', wallet_id: 'wallet-main-checking', category_id: 'category-rent', amount: '1200.00', type: 'EXPENSE', timestamp: '2026-09-20T09:00:00Z', note: 'September rent' },
  { id: 'transaction-09', wallet_id: 'wallet-main-checking', category_id: 'category-salary', amount: '3000.00', type: 'INCOME', timestamp: '2026-09-15T08:00:00Z', note: 'Paycheck' },
  { id: 'transaction-10', wallet_id: 'wallet-petty-cash', category_id: 'category-groceries', amount: '42.75', type: 'EXPENSE', timestamp: '2026-09-14T11:20:00Z', note: 'Fresh produce' },
  { id: 'transaction-11', wallet_id: 'wallet-main-checking', category_id: 'category-entertainment', amount: '27.30', type: 'EXPENSE', timestamp: '2026-09-12T21:05:00Z', note: 'Concert tickets' },
  { id: 'transaction-12', wallet_id: 'wallet-main-checking', category_id: 'category-utilities', amount: '95.00', type: 'EXPENSE', timestamp: '2026-09-10T16:40:00Z', note: 'Water & internet' },
  { id: 'transaction-13', wallet_id: 'wallet-petty-cash', category_id: 'category-transport', amount: '15.60', type: 'EXPENSE', timestamp: '2026-09-08T13:15:00Z', note: 'Taxi' },
  { id: 'transaction-14', wallet_id: 'wallet-main-checking', category_id: 'category-salary', amount: '3000.00', type: 'INCOME', timestamp: '2026-09-01T08:00:00Z', note: 'Paycheck' },
];

export async function mockListTransactions(params: TransactionListParams): Promise<Page<TransactionRead>> {
  await delay();
  const { page = 1, page_size = 25, wallet_id, category_id, date_from, date_to } = params;

  let items = MOCK_TRANSACTIONS;
  if (wallet_id) items = items.filter((t) => t.wallet_id === wallet_id);
  if (category_id) items = items.filter((t) => t.category_id === category_id);
  // ISO-8601 UTC strings compare correctly lexicographically — every
  // timestamp here shares the same fixed zero-padded format.
  if (date_from) items = items.filter((t) => t.timestamp >= date_from);
  if (date_to) items = items.filter((t) => t.timestamp <= date_to);

  return paginate(items, page, page_size);
}

/**
 * Mirrors `transaction_service.create_transaction`'s own fixed check order
 * exactly (backend `app/services/transaction_service.py`): wallet
 * ownership/existence, then category, then category-type agreement (BR-03),
 * then — EXPENSE only — balance sufficiency (BR-05). Real relational rules
 * against the mock arrays, not a magic-string branch, because these two
 * errors are about a relationship between submitted data and existing
 * records, not a fixed input.
 */
export async function mockCreateTransaction(payload: TransactionCreate): Promise<TransactionRead> {
  await delay();

  const wallet = MOCK_WALLETS.find((w) => w.id === payload.wallet_id);
  if (!wallet) {
    throw new ApiError(
      ErrorCode.TRANSACTION_WALLET_NOT_FOUND,
      'The referenced wallet was not found.',
      404,
    );
  }

  const category = MOCK_CATEGORIES.find((c) => c.id === payload.category_id);
  if (!category) {
    throw new ApiError(
      ErrorCode.TRANSACTION_CATEGORY_NOT_FOUND,
      'The referenced category was not found.',
      404,
    );
  }

  if (category.type !== payload.type) {
    throw new ApiError(
      ErrorCode.TRANSACTION_CATEGORY_TYPE_MISMATCH,
      "The transaction type does not match the referenced category's type.",
      409,
    );
  }

  if (payload.type === 'EXPENSE') {
    // The sufficiency check IS this arithmetic, mirroring the server's own
    // `WHERE balance >= amount` conditional UPDATE (wallet_repo.py): the
    // decrement is insufficient exactly when it would take the balance
    // negative, i.e. `balance < amount`.
    const nextBalance = sumMoney([wallet.balance, `-${payload.amount}`]);
    if (nextBalance.startsWith('-')) {
      throw new ApiError(ErrorCode.TRANSACTION_INSUFFICIENT_BALANCE, 'Insufficient balance.', 409);
    }
    wallet.balance = nextBalance;
  } else {
    wallet.balance = sumMoney([wallet.balance, payload.amount]);
  }

  const transaction: TransactionRead = {
    id: nextId(),
    wallet_id: wallet.id,
    category_id: category.id,
    amount: payload.amount,
    type: payload.type,
    timestamp: new Date().toISOString(),
    note: payload.note ?? null,
  };
  MOCK_TRANSACTIONS.unshift(transaction);
  return transaction;
}

// ---- Financial Reporting (FR) ------------------------------------------------
//
// September 2026's figures from the selected "Balance Scale + Category
// Stamps" concept (design-explore/summary.html `#c6`), reused verbatim.
// `category_id`s resolve against MOCK_CATEGORIES above.

export async function mockGetSummaryReport(): Promise<SummaryReportRead> {
  await delay();
  return {
    period: '2026-09-01',
    total_income: '3500.00',
    total_expenses: '2350.00',
    net_savings: '1150.00',
    top_categories: [
      { category_id: 'category-rent', category_name: 'Rent', total_amount: '1200.00' },
      { category_id: 'category-groceries', category_name: 'Groceries', total_amount: '450.00' },
      { category_id: 'category-transport', category_name: 'Transport', total_amount: '300.00' },
      { category_id: 'category-utilities', category_name: 'Utilities', total_amount: '200.00' },
      { category_id: 'category-entertainment', category_name: 'Entertainment', total_amount: '150.00' },
    ],
  };
}
