"""Budget business rules (spec BM-US-01, SDS §5.5.1).

Constitution:
  AR-01  the ownership/duplicate refusal decisions live here, not in the router
  AR-05  no framework objects — plain values only
  AR-06  this module flushes; the router commits. One request, one transaction

No audit call (plan.md A10) — budget creation is not one of constitution
LA-04's three named audited events, and no AC or FR in spec.md asks for one.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import (
    BudgetAlreadyExistsError,
    BudgetCategoryNotFoundError,
    BudgetWalletNotFoundError,
)
from app.models.user import UserModel
from app.repositories import budget_repo, category_repo, wallet_repo
from app.schemas.budget import BudgetRead


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
