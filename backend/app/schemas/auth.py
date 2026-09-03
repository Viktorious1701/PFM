"""Login DTOs (SDS §6.2.1, §6.3 SS-API-01).

Constitution: VL-01, PF-03, NC-02.
"""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """No `max_length` on password — login only *compares* against an existing
    hash, it never derives a new one, so VL-04's 72-byte bcrypt ceiling (which
    exists to avoid silent truncation on *creation*) does not apply here.
    """

    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """SDS §7.1.3/§7.1.6: HS256 bearer token, 60-minute expiry.

    No field for the password or the stored hash — the structural guard
    (spec AC-06), same technique as `InvitationRead` / `ActivationResult`.
    """

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    role: Literal["ADMIN", "USER"]


class LogoutResult(BaseModel):
    """Response DTO for POST /api/v1/auth/logout (SS-US-02 plan.md A1).

    Same technique as `ActivationResult`: no field for a token or any other
    credential, so there is nothing to leak even by accident (spec FR-04).
    """

    status: Literal["SUCCESS"]
    message: str
