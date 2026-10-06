"""Budget DTOs (SDS §2.1 `BudgetRead`/`BudgetCreate`; spec BM-US-01).

Constitution: VL-01 (Pydantic is the source of truth), VL-07 (Decimal money),
PF-03 (DTO projection).
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    """plan.md DTO block. No `period` field (A2, spec EC-04) — a submitted
    one is silently ignored, the same "structurally impossible to honour"
    pattern as `WalletCreate`/`CategoryCreate`'s absent `user_id` field. No
    UUID-shape validation on the two references (A5) — an unresolvable
    value of any shape is refused identically by the ownership-scoped
    lookup (A6).
    """

    wallet_id: str = Field(min_length=1)
    category_id: str = Field(min_length=1)

    # Decimal(15,2), reject-don't-round (WM-US-01 A3 precedent, reused
    # unchanged) plus a strict positivity bound this story adds (A4).
    amount_limit: Decimal = Field(max_digits=15, decimal_places=2, gt=0)


class BudgetUpdate(BaseModel):
    """Request DTO for PATCH /budgets/{budget_id} (BM-US-04). The budget's
    only mutable field (plan.md A1) — wallet_id/category_id/period are
    immutable post-creation (spec BR-03) and have no corresponding field
    here, so a caller cannot even name them meaningfully; any such key
    submitted anyway is silently ignored by Pydantic's default BaseModel
    behaviour (spec EC-06).

    Validation identical to BudgetCreate.amount_limit (BM-US-01 A4), reused
    unchanged — Decimal(15,2), reject-don't-round, strictly positive (A6).
    """

    amount_limit: Decimal = Field(max_digits=15, decimal_places=2, gt=0)


class BudgetRead(BaseModel):
    """SDS §2.2. Exactly five fields (spec AC-12, FR-11, constitution
    PF-03) — no owner field of any kind (A7), no status (A8).
    """

    id: str
    wallet_id: str
    category_id: str
    amount_limit: Decimal
    period: date


class BudgetProgressRead(BaseModel):
    """Per-item shape for the list endpoint (BM-US-02 AC-13, FR-13; SDS
    §5.5.2 "current progress percentages"). Distinct from `BudgetRead`
    (plan.md A2) — that DTO's own five fields are unchanged, this one simply
    repeats the same four non-id fields and adds the two computed ones.

    BM-US-03 adds `status` as an eighth, purely additive field (plan.md A3)
    — the seven fields BM-US-02 already documents are unchanged.
    """

    id: str
    wallet_id: str
    category_id: str
    amount_limit: Decimal
    period: date

    # Computed at read time (A4, A12) — never stored on BudgetModel.
    amount_spent: Decimal
    progress_percentage: Decimal

    # BM-US-03: classified at read time from progress_percentage, never
    # stored on BudgetModel (A1, A2). Only the three reachable states are
    # valid values — Pydantic itself rejects anything else (A9).
    status: Literal["NORMAL", "WARNING", "EXCEEDED"]


class BudgetListRead(BaseModel):
    """New envelope (A2) — mirrors WalletListRead (WM-US-02), CategoryListRead
    (CM-US-02), TransactionListRead (TM-US-02).
    """

    items: list[BudgetProgressRead]
    total: int
    page: int
    page_size: int
