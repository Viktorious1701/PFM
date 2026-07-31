"""Domain error base and the single response envelope (SDS §6.6).

Every failure — domain error, validation failure, or unhandled exception —
serialises to the same flat shape:

    {"error_code": "INVITATION_TOKEN_EXPIRED", "message": "…", "details": {}}

Constitution: API-02, API-04.

Only the base and the generic validation error live here. Story-specific errors
(INVITATION_TOKEN_EXPIRED, USER_EMAIL_ALREADY_ACTIVE, …) are added by the story
whose spec names them, so this module never accumulates speculative codes.
"""

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
    """spec AC-02 / FR-04 / BR-02.

    Deliberately discloses that the address is already in use. Constitution
    SEC-10 forbids account enumeration in general; this is the documented
    exemption — an ADMIN inviting a colleague needs to know why it failed.
    """

    status_code = 409
    error_code = "USER_EMAIL_ALREADY_ACTIVE"
    default_message = "An account with this email already exists"


class EmailDeliveryError(AppError):
    """spec EC-07 / FR-20. Only reachable in EMAIL_SEND_MODE=sync.

    SC-09: a delivery failure never produces a silent success.
    """

    status_code = 502
    error_code = "EMAIL_DELIVERY_FAILED"
    default_message = "The invitation could not be emailed. Please try again."
