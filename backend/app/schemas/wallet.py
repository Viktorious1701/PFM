"""Wallet DTOs (SDS §6.2.1 `WalletCreate`; spec WM-US-01).

Constitution: VL-01 (Pydantic is the source of truth), VL-07 (Decimal money),
PF-03 (DTO projection).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


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


class WalletUpdate(BaseModel):
    """Request DTO for PATCH /wallets/{wallet_id} (WM-US-04). Both fields are
    optional -- None means "leave this field's stored value unchanged,"
    whether the key was omitted or submitted explicitly as null (plan.md
    A11). `currency`/`balance` have no corresponding field at all (plan.md
    A1) -- a caller cannot even name them meaningfully; any such key
    submitted anyway is silently ignored by Pydantic's default BaseModel
    behaviour (spec EC-07).

    Validation identical to WalletCreate's own name/type bounds (WM-US-01),
    reused unchanged -- including type's own lack of a trim/whitespace
    validator (plan.md A10).
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: str | None = Field(default=None, min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Mirrors WalletCreate.validate_name exactly, applied only when a
        value is actually submitted (spec AC-06, EC-01)."""
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Wallet name cannot be empty or whitespace only")
        return trimmed

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "WalletUpdate":
        """spec AC-05, BR-04 (plan.md A4) -- the first model-level (as
        opposed to field-level) validator in this codebase. A submission
        naming neither name nor type has nothing for this endpoint to do,
        and is refused rather than silently treated as a no-op 200."""
        if self.name is None and self.type is None:
            raise ValueError("At least one of name or type must be provided")
        return self


class WalletListRead(BaseModel):
    """New envelope (WM-US-02 plan.md A2) — mirrors `UserListRead` (UM-US-03
    plan.md A6) exactly. Not in SDS's DTO registry, which names only
    `WalletCreate` directly in §6.2.1; `WalletRead`'s own six fields were
    settled in WM-US-01 and are reused unchanged here as the per-item shape.
    """

    items: list[WalletRead]
    total: int
    page: int
    page_size: int


class WalletArchiveRead(BaseModel):
    """Response DTO for DELETE /wallets/{wallet_id} (WM-US-05 plan.md A5).
    WalletRead's own six fields, reused unchanged, plus archived_at -- a new,
    dedicated envelope rather than widening WalletRead itself, so
    WM-US-01/02/03/04's own already-shipped "exactly six fields" response
    contracts (TC-18, TC-24, TC-57, TC-68) are never touched by this story.
    Mirrors WalletListRead's own precedent (WM-US-02 plan.md A2) of adding a
    new envelope rather than mutating WalletRead.
    """

    id: str
    user_id: str
    name: str
    type: str
    currency: str
    balance: Decimal
    archived_at: datetime
