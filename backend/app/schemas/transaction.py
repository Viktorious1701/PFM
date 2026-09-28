"""Transaction DTOs (SDS §2.1 `TransactionRead`/`TransactionCreate`; spec TM-US-01).

Constitution: VL-01 (Pydantic is the source of truth), VL-07 (Decimal money),
PF-03 (DTO projection).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.transaction import TransactionType


class TransactionCreate(BaseModel):
    """plan.md DTO block. No `timestamp` field at all (plan.md A5, spec
    AC-15) — the system always sets it to the moment of creation; a
    submitted timestamp-shaped value is silently ignored, the same
    "structurally impossible to honour" pattern as `BudgetCreate`'s absent
    `period` field. No UUID-shape validation on the two references (plan.md
    A8) — an unresolvable value of any shape is refused identically by the
    ownership-scoped lookup.
    """

    wallet_id: str = Field(min_length=1)
    category_id: str = Field(min_length=1)

    # Decimal(15,2), reject-don't-round (WM-US-01 A3 precedent) plus a
    # strict positivity bound — amount is a magnitude, type carries
    # direction (spec BR-04).
    amount: Decimal = Field(max_digits=15, decimal_places=2, gt=0)

    # Closed enum — Pydantic's own enum-membership validation rejects
    # anything that is not exactly "INCOME" or "EXPENSE" (spec AC-13).
    type: TransactionType

    # Optional free text (plan.md A6, spec AC-17); bounded at 500 chars.
    note: str | None = Field(default=None, max_length=500)


class TransactionRead(BaseModel):
    """SDS §2.2. Exactly seven fields (spec AC-18, FR-16, constitution
    PF-03) — no owner field of any kind (plan.md A11), no echoed wallet
    balance, no message (plan.md A14).
    """

    id: str
    wallet_id: str
    category_id: str
    amount: Decimal
    type: TransactionType
    timestamp: datetime
    note: str | None


class TransactionListRead(BaseModel):
    """New envelope (TM-US-02 plan.md A8) — mirrors `WalletListRead` (WM-US-02
    plan.md A2) and `UserListRead` (UM-US-03 plan.md A6). `TransactionRead`'s
    own seven fields are reused unchanged as the per-item shape (TM-US-01
    A14, this story's A8) — no embedded wallet or category name.
    """

    items: list[TransactionRead]
    total: int
    page: int
    page_size: int
