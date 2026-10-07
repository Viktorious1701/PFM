"""Transaction DTOs (SDS §2.1 `TransactionRead`/`TransactionCreate`; spec TM-US-01).

Constitution: VL-01 (Pydantic is the source of truth), VL-07 (Decimal money),
PF-03 (DTO projection).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

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


class TransactionUpdate(BaseModel):
    """Request DTO for PATCH /transactions/{transaction_id} (TM-US-04).
    Four independently optional fields -- None means "leave this field's
    stored value unchanged," whether the key was omitted or submitted
    explicitly as null (mirrors WalletUpdate/CategoryUpdate's own
    convention). No wallet_id field at all (plan.md A1, spec BR-01) -- a
    caller cannot even name it meaningfully; any such key submitted anyway
    is silently ignored by Pydantic's default BaseModel behaviour (spec
    EC-01).

    Validation identical to TransactionCreate's own bounds (TM-US-01),
    reused unchanged. Unlike name/icon (WalletUpdate/CategoryUpdate), note
    carries no non-blank requirement -- a caller clears an existing note by
    submitting an empty string, a real value distinct from both "omitted"
    and "null" under this convention (plan.md A8).
    """

    category_id: str | None = Field(default=None, min_length=1)
    amount: Decimal | None = Field(default=None, max_digits=15, decimal_places=2, gt=0)
    type: TransactionType | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "TransactionUpdate":
        """spec AC-11, FR-04 (plan.md A8) -- the one cross-field rule
        Pydantic cannot express on a single field, the identical shape
        CategoryUpdate (CM-US-04) already needed.
        """
        if (
            self.category_id is None
            and self.amount is None
            and self.type is None
            and self.note is None
        ):
            raise ValueError("At least one field must be provided to update a transaction.")
        return self


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
