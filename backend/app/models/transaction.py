"""Transaction model (SDS §2.1, §2.2, §4.3.3; spec TM-US-01, TM-US-02).

A single recorded movement of money, in or out, against one Wallet and one
Category, at a point in time (SRS §1.5). Same ownerless shape as
`BudgetModel` (plan.md A11) — SDS §4.3.3's `TRANSACTIONS` ERD has no
`user_id` column; ownership is entirely transitive through `wallet_id` and
`category_id` (spec BR-01).

`TransactionType` is declared as its own enum here rather than importing
`CategoryType` (plan.md A7) — every enum in this codebase belongs to, and
lives beside, the one model whose column it types (`UserStatus`/`UserRole`
in `user.py`, `InvitationStatus` in `invitation.py`, `CategoryType` in
`category.py`). BR-03's type-agreement check compares the two enums' values,
which needs no shared class.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import new_uuid


class TransactionType(enum.StrEnum):
    """SRS FR-06, SDS §6.2.1 TransactionCreate example. Same two literal
    values as CategoryType (spec BR-03 requires them to agree) — declared as
    its own enum rather than importing CategoryType, matching this
    codebase's one-enum-per-owning-model convention (plan.md A7).
    """

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class TransactionModel(Base):
    __tablename__ = "transactions"

    # TM-US-02 plan.md A5, constitution PF-02: every query this endpoint
    # issues joins through `wallet_id` and orders by `timestamp` (A2, A4), so
    # the composite serves the join, the wallet filter, and the order in one
    # index range scan. Replaces the plain `ix_transactions_wallet_id`
    # TM-US-01 created — a strict subset of what this composite already
    # provides (migration 2187429f50ce). `category_id` keeps its own plain
    # index below; no compound-ordering case is forced onto it (A5).
    __table_args__ = (Index("ix_transactions_wallet_id_timestamp", "wallet_id", "timestamp"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    # spec BR-01: ownership is entirely transitive through these two FKs — no
    # user_id column exists on this table at all, the same shape BM-US-01
    # established for budgets (plan.md A11). No standalone `index=True` here
    # any more — `__table_args__` above already indexes `wallet_id` as the
    # leading column of the composite (TM-US-02 plan.md A5).
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("wallets.id"), nullable=False)
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("categories.id"), nullable=False, index=True
    )

    # spec BR-04, constitution VL-07: Decimal(15,2), strictly positive — a
    # magnitude; direction is carried by `type`, not by the sign of `amount`.
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    # spec BR-03, FR-10: closed enum, must agree with the referenced
    # category's own type (plan.md A3, A7).
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False, length=10), nullable=False
    )

    # spec BR-06: always the moment of creation, from app.core.clock.utcnow()
    # — never client input (plan.md A5). No standalone index of its own —
    # it is the trailing column of the `wallet_id`/`timestamp` composite
    # above (TM-US-02 plan.md A5), not indexed alone.
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # spec FR-15, plan.md A6: optional free text, bounded at the DTO layer
    # only — the column itself is unbounded, matching SDS §4.3.3's `text
    # note` typing.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<TransactionModel id={self.id} wallet_id={self.wallet_id} "
            f"category_id={self.category_id} type={self.type}>"
        )
