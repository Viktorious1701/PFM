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
