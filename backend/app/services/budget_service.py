"""Budget business rules (spec BM-US-01, SDS §5.5.1).

Constitution:
  AR-01  the ownership/duplicate refusal decisions live here, not in the router
  AR-05  no framework objects — plain values only
  AR-06  this module flushes; the router commits. One request, one transaction

No audit call (plan.md A10) — budget creation is not one of constitution
LA-04's three named audited events, and no AC or FR in spec.md asks for one.
"""

from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import (
    BudgetAlreadyExistsError,
    BudgetCategoryNotFoundError,
    BudgetWalletNotFoundError,
)
from app.models.user import UserModel
from app.repositories import budget_repo, category_repo, transaction_repo, wallet_repo
from app.schemas.budget import BudgetListRead, BudgetProgressRead, BudgetRead


def create_budget(
    db: Session,
    *,
    owner: UserModel,
    wallet_id: str,
    category_id: str,
    amount_limit: Decimal,
) -> BudgetRead:
    """Create a budget scoped to `owner`'s own wallet and category (spec
    AC-01, FR-13, BR-02).

    Fixed check order — wallet ownership, then category ownership, then the
    duplicate-budget check — so a request that fails more than one reports
    only the first (plan.md A6; test_cases QF-06).
    """
    wallet = wallet_repo.get_owned_by_id(db, wallet_id=wallet_id, user_id=owner.id)
    if wallet is None:
        raise BudgetWalletNotFoundError()

    category = category_repo.get_owned_by_id(db, category_id=category_id, user_id=owner.id)
    if category is None:
        raise BudgetCategoryNotFoundError()

    # spec BR-04, plan.md A2: never from the request payload.
    period = clock.utcnow().date().replace(day=1)

    existing = budget_repo.get_by_wallet_category_period(
        db, wallet_id=wallet_id, category_id=category_id, period=period
    )
    if existing is not None:
        raise BudgetAlreadyExistsError()

    budget = budget_repo.add_budget(
        db,
        wallet_id=wallet_id,
        category_id=category_id,
        amount_limit=amount_limit,
        period=period,
    )
    return BudgetRead(
        id=budget.id,
        wallet_id=budget.wallet_id,
        category_id=budget.category_id,
        amount_limit=budget.amount_limit,
        period=budget.period,
    )


def _month_bounds(today: date) -> tuple[datetime, datetime]:
    """The current calendar month as a half-open UTC interval [start, end)
    (plan.md A5, A11) -- local to this module, deliberately not imported
    from report_service (A11). `today` is always clock.utcnow().date().
    """
    start_date = today.replace(day=1)
    if start_date.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1)
    return (
        datetime.combine(start_date, time.min, tzinfo=UTC),
        datetime.combine(end_date, time.min, tzinfo=UTC),
    )


def _classify_status(progress_percentage: Decimal) -> Literal["NORMAL", "WARNING", "EXCEEDED"]:
    """SDS §2.4.3, read literally (plan.md A1, A6): `<= 75%` is NORMAL
    (inclusive upper bound), the open interval `(75%, 100%)` is WARNING, and
    `>= 100%` is EXCEEDED (inclusive lower bound). `DRAFT`/`ARCHIVED` are
    never produced here — neither is reachable through this endpoint (A1),
    and the return type admits no other value (A9).
    """
    if progress_percentage <= Decimal("75.00"):
        return "NORMAL"
    if progress_percentage < Decimal("100.00"):
        return "WARNING"
    return "EXCEEDED"


def list_budgets(db: Session, *, owner: UserModel, page: int, page_size: int) -> BudgetListRead:
    """Assemble a page of the caller's own active budgets, each with its
    computed spending progress (A2, A4, A5, A7, A12).
    """
    today = clock.utcnow().date()
    period = today.replace(day=1)
    period_start, period_end = _month_bounds(today)

    items, total = budget_repo.list_owned(
        db, user_id=owner.id, period=period, page=page, page_size=page_size
    )
    spending = transaction_repo.get_expense_totals_by_wallet_category(
        db, user_id=owner.id, period_start=period_start, period_end=period_end
    )

    results = [
        BudgetProgressRead(
            id=budget.id,
            wallet_id=budget.wallet_id,
            category_id=budget.category_id,
            amount_limit=budget.amount_limit,
            period=budget.period,
            amount_spent=(
                spent := spending.get((budget.wallet_id, budget.category_id), Decimal("0.00"))
            ),
            progress_percentage=(
                progress := (spent / budget.amount_limit * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            ),
            status=_classify_status(progress),
        )
        for budget in items
    ]
    return BudgetListRead(items=results, total=total, page=page, page_size=page_size)
