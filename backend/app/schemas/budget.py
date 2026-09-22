"""Budget DTOs (SDS §2.1 `BudgetRead`/`BudgetCreate`; spec BM-US-01).

Constitution: VL-01 (Pydantic is the source of truth), VL-07 (Decimal money),
PF-03 (DTO projection).
"""

from datetime import date
from decimal import Decimal

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


class BudgetRead(BaseModel):
    """SDS §2.2. Exactly five fields (spec AC-12, FR-11, constitution
    PF-03) — no owner field of any kind (A7), no status (A8).
    """

    id: str
    wallet_id: str
    category_id: str
    amount_limit: Decimal
    period: date
