"""Budget queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.budget import BudgetModel


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
