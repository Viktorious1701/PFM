"""Invitation DTOs (SDS §6.2.1, §6.4.1).

Constitution: VL-01 (Pydantic is the source of truth for request validation),
PF-03 (DTO projection, never an ORM graph), NC-02.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserStatus


class InviteCreate(BaseModel):
    """SDS §6.2.1 `InviteCreate`.

    `EmailStr` gives spec AC-03 / FR-02 for free and *before* the service runs —
    a malformed address never reaches business logic. `max_length` gives EC-04:
    320 is the inclusive maximum (test_cases QF-08), so 321 characters is a 422
    rather than a silent truncation.

    Normalisation is NOT done here. Trimming and case-folding are a business rule
    (FR-03, BR-01) with exactly one definition, in `user_repo.normalize_email`.
    """

    email: EmailStr = Field(max_length=320, description="Email address to invite.")


class InvitationRead(BaseModel):
    """Success response for `POST /api/v1/users/invite`.

    **Exactly six fields, and no token.** test_cases TC-18 asserts the key set is
    closed precisely so that a future field cannot leak the token unnoticed
    (spec AC-08, FR-13, BR-07, SEC-03). If you add a field here, TC-18 fails —
    that is the guard working, not a broken test.

    SDS §6.4.1's example shows four fields; spec AC-01/FR-16 additionally require
    the expiry, and `created_at` completes the record. The spec wins over the
    SDS's abbreviated illustration.
    """

    id: str
    email: str
    status: UserStatus
    token_expires_at: datetime
    created_at: datetime
    message: str
