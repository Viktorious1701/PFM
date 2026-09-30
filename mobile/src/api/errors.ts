/**
 * Error envelope handling.
 *
 * The backend returns ONE flat shape for every failure, validation included
 * (SDS §6.6, constitution API-02):
 *
 *     { "error_code": "USER_EMAIL_ALREADY_ACTIVE", "message": "…", "details": {} }
 *
 * It is NOT nested under an "error" key. Parsing anything else here would put a
 * bug in the client the day the backend lands, so this module is written to the
 * documented contract rather than to whatever a mock happens to emit.
 */

/** Error codes this client knows how to react to. */
export const ErrorCode = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  USER_EMAIL_ALREADY_ACTIVE: 'USER_EMAIL_ALREADY_ACTIVE',
  USER_EMAIL_DEACTIVATED: 'USER_EMAIL_DEACTIVATED',
  NOT_AUTHENTICATED: 'NOT_AUTHENTICATED',
  FORBIDDEN: 'FORBIDDEN',
  EMAIL_DELIVERY_FAILED: 'EMAIL_DELIVERY_FAILED',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  /** A route the backend does not mount yet — e.g. UM-US-03's GET /users. */
  NOT_FOUND: 'NOT_FOUND',
  /** SS-US-01: unknown email, wrong password, or a DEACTIVATED account — one
   * generic outcome for all three (spec AC-03/AC-04, constitution SEC-10). */
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  /** SS-US-01 AC-02: a PENDING account, named specifically per the SRS. */
  ACCOUNT_NOT_ACTIVATED: 'ACCOUNT_NOT_ACTIVATED',
  /** UM-US-02: an unrecognised, used, superseded, or wrong-state token. */
  INVITATION_TOKEN_INVALID: 'INVITATION_TOKEN_INVALID',
  /** UM-US-02: an outstanding token past its TTL. */
  INVITATION_TOKEN_EXPIRED: 'INVITATION_TOKEN_EXPIRED',
  /** Client-side only: the request never reached the server. */
  NETWORK_ERROR: 'NETWORK_ERROR',
  /** TM-US-01: `wallet_id` doesn't resolve to a wallet the caller owns. */
  TRANSACTION_WALLET_NOT_FOUND: 'TRANSACTION_WALLET_NOT_FOUND',
  /** TM-US-01: `category_id` doesn't resolve to a category the caller owns. */
  TRANSACTION_CATEGORY_NOT_FOUND: 'TRANSACTION_CATEGORY_NOT_FOUND',
  /** TM-US-01 BR-03: the transaction's `type` disagrees with the referenced
   * category's own type. */
  TRANSACTION_CATEGORY_TYPE_MISMATCH: 'TRANSACTION_CATEGORY_TYPE_MISMATCH',
  /** TM-US-01 BR-05: an EXPENSE whose amount exceeds the wallet's balance. */
  TRANSACTION_INSUFFICIENT_BALANCE: 'TRANSACTION_INSUFFICIENT_BALANCE',
} as const;

export type ErrorCodeValue = (typeof ErrorCode)[keyof typeof ErrorCode] | string;

export type ErrorEnvelope = {
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
};

export class ApiError extends Error {
  readonly code: ErrorCodeValue;
  readonly status: number;
  readonly details: Record<string, unknown>;

  constructor(code: ErrorCodeValue, message: string, status: number, details = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }

  /** True when the caller's credentials are absent, invalid, or expired. */
  get isUnauthenticated(): boolean {
    return this.status === 401 || this.code === ErrorCode.NOT_AUTHENTICATED;
  }
}

function isEnvelope(value: unknown): value is ErrorEnvelope {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as ErrorEnvelope).error_code === 'string' &&
    typeof (value as ErrorEnvelope).message === 'string'
  );
}

/** Normalise any thrown value into an ApiError. Never throws. */
export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;

  // Axios-shaped error, without importing axios types here.
  const response = (err as { response?: { status?: number; data?: unknown } })?.response;

  if (response && isEnvelope(response.data)) {
    const { error_code, message, details } = response.data;
    return new ApiError(error_code, message, response.status ?? 500, details ?? {});
  }

  if (response) {
    return new ApiError(
      ErrorCode.INTERNAL_ERROR,
      'The server returned an unexpected response.',
      response.status ?? 500,
    );
  }

  return new ApiError(
    ErrorCode.NETWORK_ERROR,
    'Could not reach the server. Check your connection and try again.',
    0,
  );
}

/**
 * Field-level messages from a 422, for rendering inline on the offending input.
 * The backend groups validation errors under `details` (constitution VL-02).
 */
export function fieldErrors(err: ApiError): Record<string, string> {
  const out: Record<string, string> = {};
  const raw = err.details;
  for (const [key, value] of Object.entries(raw)) {
    if (typeof value === 'string') out[key] = value;
    else if (Array.isArray(value) && typeof value[0] === 'string') out[key] = value[0];
  }
  return out;
}
