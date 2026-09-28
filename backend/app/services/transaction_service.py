"""Transaction business rules (spec TM-US-01, SDS §5.6.1).

Constitution:
  AR-01  the ownership/type-consistency/balance-sufficiency refusal
         decisions live here, not in the router
  AR-05  no framework objects — plain values only
  AR-06  this module flushes; the router commits. One request, one
         transaction

No audit call (plan.md A13) — transaction creation is not one of
constitution LA-04's three named audited events, and no AC or FR in spec.md
asks for one.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import (
    TransactionCategoryNotFoundError,
    TransactionCategoryTypeMismatchError,
    TransactionInsufficientBalanceError,
    TransactionWalletNotFoundError,
)
from app.models.transaction import TransactionType
from app.models.user import UserModel
from app.repositories import category_repo, transaction_repo, wallet_repo
from app.schemas.transaction import TransactionRead


def create_transaction(
    db: Session,
    *,
    owner: UserModel,
    wallet_id: str,
    category_id: str,
    amount: Decimal,
    type: TransactionType,
    note: str | None,
) -> TransactionRead:
    """Create a transaction scoped to `owner`'s own wallet and category
    (spec AC-01, AC-02, FR-18, BR-02).

    Fixed check order — wallet ownership, then category ownership, then
    category-type consistency, then (EXPENSE only) balance sufficiency — so
    a request that fails more than one reports only the first (plan.md A4).
    """
    wallet = wallet_repo.get_owned_by_id(db, wallet_id=wallet_id, user_id=owner.id)
    if wallet is None:
        raise TransactionWalletNotFoundError()

    category = category_repo.get_owned_by_id(db, category_id=category_id, user_id=owner.id)
    if category is None:
        raise TransactionCategoryNotFoundError()

    # spec BR-03, plan.md A3/A7: compared by value — TransactionType and
    # CategoryType are deliberately separate enum classes with matching
    # literals.
    if category.type.value != type.value:
        raise TransactionCategoryTypeMismatchError()

    # spec BR-05, plan.md A2/A9: the sufficiency check is the conditional
    # UPDATE itself for EXPENSE; INCOME never checks (A2).
    if type is TransactionType.EXPENSE:
        affected = wallet_repo.decrement_balance(db, wallet_id=wallet_id, amount=amount)
        if affected == 0:
            raise TransactionInsufficientBalanceError()
    else:
        wallet_repo.increment_balance(db, wallet_id=wallet_id, amount=amount)

    # spec BR-06, plan.md A5: never from the request payload.
    timestamp = clock.utcnow()

    transaction = transaction_repo.add_transaction(
        db,
        wallet_id=wallet_id,
        category_id=category_id,
        amount=amount,
        type=type,
        timestamp=timestamp,
        note=note,
    )
    return TransactionRead(
        id=transaction.id,
        wallet_id=transaction.wallet_id,
        category_id=transaction.category_id,
        amount=transaction.amount,
        type=transaction.type,
        timestamp=clock.ensure_aware(transaction.timestamp),
        note=transaction.note,
    )
