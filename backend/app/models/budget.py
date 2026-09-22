"""Budget model (SDS §2.2, §4.3.3; spec BM-US-01).

A spending limit a User sets for one Category within one Wallet, over a
monthly period, that Transactions are measured against (SRS §1.5). Unlike
`WalletModel`/`CategoryModel`, this table carries no `user_id` at all (plan.md
A7) — SDS §4.3.3's `BUDGETS` ERD has no owner column; ownership is entirely
transitive through `wallet_id` and `category_id` (spec BR-01).

No `status` column (plan.md A8) and no `created_at` column (plan.md A11) —
the ERD lists exactly `id`, `wallet_id`, `category_id`, `amount_limit`,
`period` for `budgets`, and adding a column the ERD does not list is a
domain-model change this story may not make unilaterally. Both flagged, not
silently patched — see spec.md Assumptions.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import new_uuid


class BudgetModel(Base):
    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    # spec BR-01: ownership is entirely transitive through this FK — no
    # user_id column exists on this table at all (A7).
    wallet_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wallets.id"), nullable=False, index=True
    )
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("categories.id"), nullable=False, index=True
    )

    # spec BR-03, constitution VL-07: Decimal(15,2), strictly positive (A4).
    amount_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    # spec BR-04: always the 1st of the current month at creation (A2).
    period: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        # spec BR-05, plan.md A3: at most one budget per wallet+category+period.
        UniqueConstraint(
            "wallet_id", "category_id", "period", name="uq_budgets_wallet_category_period"
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<BudgetModel id={self.id} wallet_id={self.wallet_id} category_id={self.category_id}>"
        )
