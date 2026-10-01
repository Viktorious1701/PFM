"""Budget queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.budget import BudgetModel
from app.models.wallet import WalletModel


def get_by_wallet_category_period(
    db: Session, *, wallet_id: str, category_id: str, period: date
) -> BudgetModel | None:
    """spec FR-10, BR-05, plan.md A3. The existence half of the two-level
    uniqueness check (constitution VL-05) — the refusal decision is the
    service's, not this query's (plan.md A6).
    """
    return db.scalar(
        select(BudgetModel).where(
            BudgetModel.wallet_id == wallet_id,
            BudgetModel.category_id == category_id,
            BudgetModel.period == period,
        )
    )


def add_budget(
    db: Session,
    *,
    wallet_id: str,
    category_id: str,
    amount_limit: Decimal,
    period: date,
) -> BudgetModel:
    """Insert a new budget (spec AC-01, FR-09..FR-11, BR-01).

    Flushed, not committed (AR-06) — the router owns the transaction
    boundary.
    """
    budget = BudgetModel(
        wallet_id=wallet_id,
        category_id=category_id,
        amount_limit=amount_limit,
        period=period,
    )
    db.add(budget)
    db.flush()
    return budget


def list_owned(
    db: Session, *, user_id: str, period: date, page: int, page_size: int
) -> tuple[Sequence[BudgetModel], int]:
    """A page of the caller's own budgets whose `period` equals the current
    calendar month, plus that owner's own total count (spec AC-01, AC-04,
    AC-05, AC-07, AC-09; plan.md A1, A3, A5).

    Ownership is transitive through a join to `wallets` (A3) — there is no
    `budgets.user_id` column, the same shape `transaction_repo.list_owned()`
    already established for `transactions`. A single join on `wallets` is
    sufficient: BM-US-01 FR-13/BR-02 validates `wallet_id` and `category_id`
    independently against the same caller at creation, so every stored row's
    `category_id` is already guaranteed to belong to whoever owns its
    `wallet_id` (A3). Ordered by `id`, the one column guaranteed to exist and
    be unique without a schema change (A1).
    """
    conditions = [WalletModel.user_id == user_id, BudgetModel.period == period]

    joined = select(BudgetModel).join(WalletModel, BudgetModel.wallet_id == WalletModel.id)

    total = (
        db.scalar(
            select(func.count())
            .select_from(BudgetModel)
            .join(WalletModel, BudgetModel.wallet_id == WalletModel.id)
            .where(*conditions)
        )
        or 0
    )
    items = db.scalars(
        joined.where(*conditions)
        .order_by(BudgetModel.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total
