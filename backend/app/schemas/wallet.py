"""Wallet DTOs (SDS §6.2.1 `WalletCreate`; spec WM-US-01).

Constitution: VL-01 (Pydantic is the source of truth), VL-07 (Decimal money),
PF-03 (DTO projection).
"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class WalletCreate(BaseModel):
    """plan.md DTO block. No `user_id` field at all (plan.md A7, spec AC-10) —
    the owner comes only from `CurrentUserDep`; an extra `user_id` key in the
    submitted JSON is silently ignored by Pydantic's default `BaseModel`
    behaviour, matching every existing schema in this codebase.
    """

    # Trimmed and required non-empty after trimming (spec AC-03, EC-04);
    # bounded at the column width (spec AC-04).
    name: str = Field(min_length=1, max_length=100)

    # Free text, no enum (plan.md A1); bounded the same way as name (spec
    # AC-05, AC-06).
    type: str = Field(min_length=1, max_length=50)

    # ISO-4217 shape only, no case-folding (plan.md A2; spec AC-07, EC-03).
    currency: str = Field(pattern=r"^[A-Z]{3}$")

    # Decimal(15,2), reject-don't-round (plan.md A3; spec AC-08, AC-09,
    # constitution VL-07).
    initial_balance: Decimal = Field(max_digits=15, decimal_places=2)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """spec AC-03, EC-04: trimmed, and a trimmed-to-empty name still
        fails — matching AC-03's "empty or only whitespace" wording. Opt-in
        per field, the same technique `ActivateRequest.full_name` uses — no
        model-wide `str_strip_whitespace`.
        """
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Wallet name cannot be empty or whitespace only")
        return trimmed


class WalletRead(BaseModel):
    """SDS §2.2, §6.2.1. Exactly six fields (spec AC-11, FR-10, constitution
    PF-03) — no `created_at` (plan.md A5, test_cases QF-04).
    """

    id: str
    user_id: str
    name: str
    type: str
    currency: str
    balance: Decimal
