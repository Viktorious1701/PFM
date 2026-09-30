/**
 * Wire DTOs, typed to the documented contract in SDS §6.2.1 / §6.4.
 *
 * Enum values are the literal UPPER_SNAKE_CASE strings the backend serialises
 * (constitution NC-05); human-friendly labels are a client concern and live in
 * the components, not here.
 */

/** SDS §2.4.1. `PENDING` — SRS wins over the SDS's old `PENDING_INVITATION`. */
export type UserStatus = 'PENDING' | 'ACTIVE' | 'DEACTIVATED';

/** SDS §5.2.1 / §5.2.3. Invited accounts always get `USER` (spec FR-06). */
export type UserRole = 'ADMIN' | 'USER';

/** SDS §6.2.1 `InviteCreate`. */
export type InviteCreate = {
  email: string;
};

/**
 * Response of `POST /api/v1/users/invite` (SDS §6.4.1) plus the invitation
 * expiry that spec AC-01 / FR-16 require the caller to receive.
 *
 * There is deliberately NO token field. Spec AC-08 / BR-07 / SC-06: the raw
 * token reaches exactly one party — the invited mailbox. Adding a token here
 * would be the client-side half of that leak, so the type forbids it.
 */
export type InvitationRead = {
  id: string;
  email: string;
  status: UserStatus;
  message: string;
  /**
   * ISO-8601 instant, exactly 24 hours after creation (spec FR-09).
   * Always carries a UTC offset — the backend passes it through
   * `clock.ensure_aware()` because SQLite drops tzinfo on read-back.
   */
  token_expires_at: string;
  created_at: string;
};

/** Row of `GET /api/v1/users` (SDS §6.3 UM-API-03) — UM-US-03. */
export type UserRead = {
  id: string;
  email: string;
  full_name: string | null;
  status: UserStatus;
  role: UserRole;
  created_at: string;
};

/** Paginated envelope — constitution API-06, PF-04 (always bounded). */
export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

/** `POST /api/v1/auth/login` (SDS §6.3 SS-API-01) — SS-US-01. */
export type LoginRequest = {
  email: string;
  password: string;
};

/**
 * Matches `TokenResponse` (`backend/app/schemas/auth.py`) exactly — SS-US-01's
 * spec requires only the token, its expiry, and the caller's role, so that is
 * all the server returns. There is deliberately no `user` field: a full
 * profile is UM-US-04's concern (SDS-only, out of MVP scope), not this
 * story's, and inventing one here would be a client contract the backend
 * does not honour.
 */
export type LoginResponse = {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  role: UserRole;
};

/** SDS §6.2.1 `UserActivate` — UM-US-02. */
export type ActivateRequest = {
  token: string;
  full_name: string;
  password: string;
};

export type ActivateResponse = {
  status: 'SUCCESS';
  message: string;
};
/** Token state for UM-US-02 pre-check (GET /api/v1/users/activate) */
export type TokenState = 'usable' | 'expired' | 'not_usable';

export type TokenStateRead = {
  state: TokenState;
};

/**
 * `GET /api/v1/dev/outbox` (UM-US-01 A13/A14) — dev-only, ADMIN, never present
 * in production. Reads what `FileOutboxSender` wrote when
 * `EMAIL_TRANSPORT=outbox`, so an activation link can be read without a real
 * mailbox. Not a documented SDS DTO — this route belongs to no SRS/SDS story.
 */
export type OutboxMessage = {
  to: string;
  sent_at: string;
  activation_url: string | null;
};

export type OutboxList = {
  messages: OutboxMessage[];
};

// ---------------------------------------------------------------------------
// Wallet Management (WM) — SDS §2.2, §6.2.1; backend app/schemas/wallet.py.
// ---------------------------------------------------------------------------

/** `POST /api/v1/wallets` request (SDS §6.2.1 `WalletCreate`) — WM-US-01. */
export type WalletCreate = {
  name: string;
  /** Free text, no enum (WM-US-01 plan.md A1) — e.g. `"Piggy Bank"` is valid. */
  type: string;
  /** ISO-4217 shape only, no case-folding — server pattern `^[A-Z]{3}$`. */
  currency: string;
  /** Decimal-as-string (constitution VL-07) — never `number`. May be negative. */
  initial_balance: string;
};

/**
 * Row of `GET /api/v1/wallets` / response of `POST /api/v1/wallets` (SDS
 * §2.2, §6.2.1) — WM-US-01/02. Exactly six fields — no `created_at`
 * (WM-US-01 plan.md A5).
 */
export type WalletRead = {
  id: string;
  user_id: string;
  name: string;
  type: string;
  currency: string;
  /** Decimal-as-string — never `number`. */
  balance: string;
};

// ---------------------------------------------------------------------------
// Category Management (CM) — SDS §2.2; backend app/schemas/category.py.
// ---------------------------------------------------------------------------

/**
 * SRS FR-04: a closed, two-value vocabulary (`app/models/category.py`).
 * Reused below as `TransactionCreate.type` / `TransactionRead.type` too —
 * the backend deliberately declares `TransactionType` as its own enum class
 * with matching literals rather than importing `CategoryType` (one-enum-
 * per-owning-model convention), but the two never disagree in value (spec
 * BR-03), so this client-side reuse is a convenience, not a contract mirror.
 */
export type CategoryType = 'INCOME' | 'EXPENSE';

/** `POST /api/v1/categories` request — CM-US-01. */
export type CategoryCreate = {
  name: string;
  type: CategoryType;
};

/**
 * Row of `GET /api/v1/categories` (CM-US-02) / response of `POST
 * /api/v1/categories` (CM-US-01). Exactly four fields — no `icon` (CM-US-01
 * plan.md A4; deferred to CM-US-04, which is also why category glyph
 * matching in this client is name-string-based rather than id-based).
 */
export type CategoryRead = {
  id: string;
  user_id: string;
  name: string;
  type: CategoryType;
};

// ---------------------------------------------------------------------------
// Transaction Management (TM) — SDS §2.2; backend app/schemas/transaction.py.
// ---------------------------------------------------------------------------

/**
 * `POST /api/v1/transactions` request — TM-US-01. No `timestamp` field — the
 * server always sets it to the moment of creation (plan.md A5).
 */
export type TransactionCreate = {
  wallet_id: string;
  category_id: string;
  /** Decimal-as-string, strictly positive — a magnitude; `type` carries
   * direction (spec BR-04). */
  amount: string;
  type: CategoryType;
  /** Optional free text, max 500 chars server-side. Omit or pass `null` —
   * both mean "no note", matching the server's `str | None = None`. */
  note?: string | null;
};

/**
 * Row of `GET /api/v1/transactions` / response of `POST /api/v1/transactions`
 * (TM-US-01/02). Exactly seven fields — no owner field of any kind (plan.md
 * A11), no echoed wallet balance, no message (plan.md A14).
 */
export type TransactionRead = {
  id: string;
  wallet_id: string;
  category_id: string;
  /** Decimal-as-string — never `number`. */
  amount: string;
  type: CategoryType;
  /** ISO-8601 instant. */
  timestamp: string;
  note: string | null;
};

/**
 * Query params for `GET /api/v1/transactions` (TM-US-02). `page`/`page_size`
 * default to 1/25 inside `listTransactions` itself, not here, so every key
 * on this type stays optional and is merged into the request only when
 * present.
 */
export type TransactionListParams = {
  page?: number;
  page_size?: number;
  wallet_id?: string;
  category_id?: string;
  /** ISO-8601 instant — the server parses this as a `datetime`, not a bare date. */
  date_from?: string;
  date_to?: string;
};

// ---------------------------------------------------------------------------
// Financial Reporting (FR) — SDS §5.7.1; backend app/schemas/report.py.
// ---------------------------------------------------------------------------

/**
 * One ranked entry in `SummaryReportRead.top_categories` (backend
 * `CategorySpendingRead`). `category_name` is a projected field, not a
 * nested `CategoryRead` — no `GET /categories` endpoint existed anywhere in
 * this codebase when that response shape was designed (plan.md A6), so the
 * backend resolves the display name itself.
 */
export type TopCategory = {
  category_id: string;
  category_name: string;
  /** Decimal-as-string. */
  total_amount: string;
};

/**
 * `GET /api/v1/reports/summary` response — FR-US-01. Always the current
 * calendar month; the endpoint takes no period argument. No currency field
 * at all — the aggregation is currency-naive, summing Decimal amounts across
 * whatever wallets/currencies the caller has (a gap flagged at the Reports
 * screen's own call site, not silently absorbed here).
 */
export type SummaryReportRead = {
  /** ISO-8601 date, e.g. `"2026-09-01"` — the first of the reported month. */
  period: string;
  total_income: string;
  total_expenses: string;
  /** May be negative (spec AC-09, BR-04) — no positivity bound. */
  net_savings: string;
  top_categories: TopCategory[];
};