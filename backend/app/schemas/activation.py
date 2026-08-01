"""Activation DTOs (SDS §6.2.1, §6.4.2, §6.4.3).

Constitution: VL-01, VL-04, PF-03, NC-02.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core import security


class ActivateRequest(BaseModel):
    """SDS §6.2.1 `ActivateRequest`.

    Note: token is NOT stripped or normalized (EC-08 exact match requirement).
    """

    token: str = Field(min_length=1, max_length=64, description="Raw invitation token")
    full_name: str = Field(min_length=1, max_length=255, description="Full name of the user")
    password: str = Field(description="Password satisfying security policy")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Full name cannot be empty or whitespace only")
        return trimmed

    @field_validator("password")
    @classmethod
    def validate_password_policy(cls, v: str) -> str:
        """VL-04 Password Policy: 8..72 UTF-8 bytes, >=1 upper, >=1 digit, >=1 special char."""
        encoded = v.encode("utf-8")
        if len(encoded) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(encoded) > security.BCRYPT_MAX_BYTES:
            raise ValueError(
                f"Password exceeds maximum length of {security.BCRYPT_MAX_BYTES} bytes"
            )
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\\/\[\];']", v):
            raise ValueError("Password must contain at least one special character")
        return v


class ActivationResult(BaseModel):
    """Response DTO for POST /api/v1/users/activate (no token or session issued)."""

    status: Literal["SUCCESS"]
    message: str


class TokenStateRead(BaseModel):
    """Response DTO for GET /api/v1/users/activate (token state pre-check)."""

    state: Literal["usable", "expired", "not_usable"]