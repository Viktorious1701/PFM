"""Category DTOs (SDS §2.1; spec CM-US-01).

Constitution: VL-01 (Pydantic is the source of truth), PF-03 (DTO projection),
NC-05 (enum serialisation).
"""

from pydantic import BaseModel, Field, field_validator

from app.models.category import CategoryType


class CategoryCreate(BaseModel):
    """plan.md DTO block. No `user_id` field at all (plan.md A6, spec AC-07) —
    the owner comes only from `CurrentUserDep`; an extra `user_id` (or
    `icon`) key in the submitted JSON is silently ignored by Pydantic's
    default `BaseModel` behaviour, matching every existing schema in this
    codebase.
    """

    # Trimmed and required non-empty after trimming (spec AC-03, EC-02);
    # bounded at the column width (spec AC-04; plan.md A1).
    name: str = Field(min_length=1, max_length=100)

    # Closed enum, no case-folding, no trimming (plan.md A2; spec AC-05,
    # AC-06, EC-01, EC-06) — Pydantic's own enum-membership validation
    # rejects anything that is not exactly `"INCOME"` or `"EXPENSE"`.
    type: CategoryType

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """spec AC-03, EC-02: trimmed, and a trimmed-to-empty name still
        fails — matching `WalletCreate.name`'s exact technique. Opt-in per
        field, no model-wide `str_strip_whitespace`.
        """
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Category name cannot be empty or whitespace only")
        return trimmed


class CategoryRead(BaseModel):
    """SDS §2.2 (as aligned). Exactly four fields (spec AC-08, FR-06,
    constitution PF-03) — no `icon` (plan.md A4, test_cases QF-04).
    """

    id: str
    user_id: str
    name: str
    type: CategoryType


class CategoryListRead(BaseModel):
    """New envelope (CM-US-02 plan.md A2) — mirrors `WalletListRead`
    (WM-US-02 plan.md A2) and `TransactionListRead` (TM-US-02 plan.md A8).
    `CategoryRead`'s own four fields are reused unchanged as the per-item
    shape — no icon, no other entity's data folded in.
    """

    items: list[CategoryRead]
    total: int
    page: int
    page_size: int
