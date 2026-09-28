"""Domain error base and the single response envelope (SDS §6.6)."""

from typing import Any


class AppError(Exception):
    """Base for expected, client-facing failures."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    default_message: str = "Unexpected server error."

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)

    def to_envelope(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(AppError):
    """API-03: payload validation failures are 422, in the same envelope."""

    status_code = 422
    error_code = "VALIDATION_ERROR"
    default_message = "Request payload is invalid."


# --- UM-US-01: Invite a user via email ------------------------------------


class NotAuthenticatedError(AppError):
    """spec AC-05 / FR-15. Raised before the payload is examined (plan.md A8)."""

    status_code = 401
    error_code = "NOT_AUTHENTICATED"
    default_message = "Authentication credentials were not provided or are no longer valid."


class ForbiddenError(AppError):
    """spec AC-04 / FR-14. Authenticated, but the role is not ADMIN."""

    status_code = 403
    error_code = "FORBIDDEN"
    default_message = "Only an administrator can perform this action."


class UserEmailAlreadyActiveError(AppError):
    """spec AC-02 / FR-04 / BR-02."""

    status_code = 409
    error_code = "USER_EMAIL_ALREADY_ACTIVE"
    default_message = "An account with this email already exists"


class UserEmailDeactivatedError(AppError):
    """plan.md T-18 / Finding F1. Prevents silent reactivation of disabled accounts."""

    status_code = 409
    error_code = "USER_EMAIL_DEACTIVATED"
    default_message = "An account with this email has been deactivated"


class EmailDeliveryError(AppError):
    """spec EC-07 / FR-20. Only reachable in EMAIL_SEND_MODE=sync."""

    status_code = 502
    error_code = "EMAIL_DELIVERY_FAILED"
    default_message = "The invitation could not be emailed. Please try again."


# --- UM-US-02: Activate a user account -----------------------------------


class InvitationTokenExpiredError(AppError):
    """spec AC-02 / FR-04 / EC-10. HTTP 400 when the token's TTL has passed."""

    status_code = 400
    error_code = "INVITATION_TOKEN_EXPIRED"
    default_message = "The provided invitation link has expired. Please request a new invitation."


class InvitationTokenInvalidError(AppError):
    """spec AC-03 / AC-04 / AC-05 / EC-06 / EC-07 / EC-08 / EC-11 / BR-10.

    HTTP 400 for every non-expiry refusal: token unknown, used, superseded, or user not PENDING.
    """

    status_code = 400
    error_code = "INVITATION_TOKEN_INVALID"
    default_message = "The provided invitation link is invalid or has already been used."


# --- SS-US-01: Login -------------------------------------------------------


class InvalidCredentialsError(AppError):
    """spec AC-03 / AC-04 / FR-05 / FR-07.

    One generic 401 for an unknown email, a wrong password, or a DEACTIVATED
    account — never distinguished (constitution SEC-10).
    """

    status_code = 401
    error_code = "INVALID_CREDENTIALS"
    default_message = "The email or password is incorrect."


class AccountNotActivatedError(AppError):
    """spec AC-02 / FR-06. Only reachable with a correct password (BR-01) —

    the SRS's own message, disclosed deliberately because the caller has
    already proven they hold the right credentials.
    """

    status_code = 403
    error_code = "ACCOUNT_NOT_ACTIVATED"
    default_message = "Your account is not activated. Please check your email invitation."


# --- BM-US-01: Create a Budget ---------------------------------------------


class BudgetWalletNotFoundError(AppError):
    """spec AC-04 / FR-04. Identical for "no such wallet" and "not this

    caller's wallet" (constitution VL-06's `404 if absent` branch).
    """

    status_code = 404
    error_code = "BUDGET_WALLET_NOT_FOUND"
    default_message = "The referenced wallet was not found."


class BudgetCategoryNotFoundError(AppError):
    """spec AC-06 / FR-06. Same collapsed shape as BudgetWalletNotFoundError."""

    status_code = 404
    error_code = "BUDGET_CATEGORY_NOT_FOUND"
    default_message = "The referenced category was not found."


class BudgetAlreadyExistsError(AppError):
    """spec AC-11 / FR-10 / BR-05, constitution VL-05."""

    status_code = 409
    error_code = "BUDGET_ALREADY_EXISTS"
    default_message = "A budget already exists for this wallet, category, and period."


# --- TM-US-01: Create a Transaction -----------------------------------------


class TransactionWalletNotFoundError(AppError):
    """spec AC-05 / FR-04. Identical for "no such wallet" and "not this

    caller's wallet" (constitution VL-06's `404 if absent` branch).
    """

    status_code = 404
    error_code = "TRANSACTION_WALLET_NOT_FOUND"
    default_message = "The referenced wallet was not found."


class TransactionCategoryNotFoundError(AppError):
    """spec AC-07 / FR-06. Same collapsed shape as TransactionWalletNotFoundError."""

    status_code = 404
    error_code = "TRANSACTION_CATEGORY_NOT_FOUND"
    default_message = "The referenced category was not found."


class TransactionCategoryTypeMismatchError(AppError):
    """spec AC-08 / FR-07 / BR-03. Constitution VL-06's "409 if present but

    in the wrong state" branch — the first story in this codebase to
    exercise it: the category exists and is owned by the caller, but its
    own type disagrees with the submitted transaction type.
    """

    status_code = 409
    error_code = "TRANSACTION_CATEGORY_TYPE_MISMATCH"
    default_message = "The transaction type does not match the referenced category's type."


class TransactionInsufficientBalanceError(AppError):
    """spec AC-14 / FR-11 / BR-05. The SRS's own "(MVP Rule)" scenario and

    its own literal message.
    """

    status_code = 409
    error_code = "TRANSACTION_INSUFFICIENT_BALANCE"
    default_message = "Insufficient balance."
