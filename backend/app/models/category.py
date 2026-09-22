"""Category model (SDS §2.2, §4.3.3 as aligned; spec CM-US-01).

A label a User defines to classify money movement as one kind of income or
expense (SRS §1.5). Unlike `WalletModel.type` (free text, WM-US-01 A1),
`CategoryType` is a real closed enum — SRS FR-04 names exactly two literals,
`INCOME` and `EXPENSE` — modelled on the `UserStatus`/`UserRole` pattern in
`app/models/user.py` (constitution NC-05), not on Wallet's free-text `type`.

No `icon` column (plan.md A4) — SDS §4.3.3's ERD was aligned to add a nullable
`icon` at the document level (plan.md G1), but no AC in this story's own set
asks for it, so the column is deferred to CM-US-04. Flagged, not silently
patched — see spec.md Assumptions.
"""

import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import new_uuid


class CategoryType(enum.StrEnum):
    """SRS FR-04: a closed, two-value vocabulary (plan.md A2)."""

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    # spec BR-01 / AC-07 / constitution SEC-08: every future query on this
    # table filters by owner, so the FK carries an index now (PF-02), the same
    # forward-looking index WM-US-01 added for `wallets.user_id`.
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    # spec AC-03/AC-04/FR-03, plan.md A1: required, trimmed by the DTO,
    # bounded at 100 — the same bound WM-US-01 settled on for `wallets.name`.
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # spec AC-05/AC-06/FR-04, plan.md A2: closed enum, no case-folding.
    type: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType, native_enum=False, length=10), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<CategoryModel id={self.id} user_id={self.user_id} name={self.name}>"
