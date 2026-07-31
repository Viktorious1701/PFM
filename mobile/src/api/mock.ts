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
import { ApiError, ErrorCode } from './errors';
import type {
  ActivateResponse,
  InvitationRead,
  LoginResponse,
  Page,
  UserRead,
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
      ErrorCode.FORBIDDEN,
      'This account has not been activated yet. Use the link in your invitation email.',
      403,
    );
  }

  if (email === 'wrong@example.com') {
    throw new ApiError(ErrorCode.NOT_AUTHENTICATED, 'Incorrect email or password.', 401);
  }

  const isAdmin = email === MOCK_ADMIN.email || email === 'admin@example.com';
  return {
    access_token: 'mock.jwt.token',
    token_type: 'bearer',
    user: isAdmin ? MOCK_ADMIN : { ...MOCK_USERS[1], email },
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
      'INVITATION_TOKEN_EXPIRED',
      'The provided invitation link has expired. Please request a new invitation.',
      410,
    );
  }

  return { status: 'SUCCESS', message: 'Account activated successfully. You may now log in.' };
}
