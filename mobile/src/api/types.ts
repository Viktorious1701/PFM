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
  /** ISO-8601 instant, exactly 24 hours after creation (spec FR-09). */
  invitation_expires_at: string;
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

export type LoginResponse = {
  access_token: string;
  token_type: 'bearer';
  user: UserRead;
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
