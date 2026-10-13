"""Category model (SDS §2.2, §4.3.3 as aligned; spec CM-US-01).

A label a User defines to classify money movement as one kind of income or
expense (SRS §1.5). Unlike `WalletModel.type` (free text, WM-US-01 A1),
`CategoryType` is a real closed enum — SRS FR-04 names exactly two literals,
`INCOME` and `EXPENSE` — modelled on the `UserStatus`/`UserRole` pattern in
`app/models/user.py` (constitution NC-05), not on Wallet's free-text `type`.

`icon` (CM-US-04 plan.md A5) is nullable, `String(50)`, no default — SDS
§4.3.3's ERD was aligned to add it at the document level back in CM-US-01
(plan.md G1), and this is the story whose own goal names icon-editing, so the
column lands here rather than at creation time.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
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

    # CM-US-04 plan.md A5/A11: nullable, no default -- absent until a caller
    # sets it through PATCH /categories/{category_id}. Bounded at 50, not
    # name's own 100 -- an icon is a short identifier/slug, not a label.
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # spec AC-01/AC-05/FR-04/FR-05, plan.md A1: NULL means active; a non-NULL
    # value means archived and records the moment -- set at most once
    # (archive_category() never overwrites an existing value, A6).
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<CategoryModel id={self.id} user_id={self.user_id} name={self.name}>"
