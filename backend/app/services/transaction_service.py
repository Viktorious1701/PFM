"""Transaction business rules (spec TM-US-01, TM-US-02, SDS §5.6.1, §5.6.2).

Constitution:
  AR-01  the ownership/type-consistency/balance-sufficiency refusal
         decisions live here, not in the router
  AR-05  no framework objects — plain values only
  AR-06  this module flushes; the router commits. One request, one
         transaction

No audit call (plan.md A13/A10) — neither creating nor listing transactions
is one of constitution LA-04's three named audited events, and no AC or FR
in spec.md asks for one.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import (
    TransactionCategoryNotFoundError,
    TransactionCategoryTypeMismatchError,
    TransactionInsufficientBalanceError,
    TransactionNotFoundError,
    TransactionWalletNotFoundError,
    ValidationError,
)
from app.models.transaction import TransactionType
from app.models.user import UserModel
from app.repositories import category_repo, transaction_repo, wallet_repo
from app.schemas.transaction import TransactionListRead, TransactionRead


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


def update_transaction(
    db: Session,
    *,
    owner: UserModel,
    transaction_id: str,
    category_id: str | None,
    amount: Decimal | None,
    type: TransactionType | None,
    note: str | None,
) -> TransactionRead:
    """spec TM-US-04 AC-01..AC-18, FR-03, FR-06, FR-07, FR-11, FR-12, FR-13
    (plan.md A3, A4, A5, A6). Looks up the transaction scoped to the caller,
    then -- uniformly, regardless of which field(s) were actually submitted
    -- reverses its current stored effect on its wallet and applies its
    effective new effect, before writing the submitted field(s) onto the
    row itself. A failed reapplication (insufficient balance) raises before
    the row is ever touched; app.db.session.get_db()'s own
    `except Exception: db.rollback()` discards the already-flushed reversal
    along with it, so nothing is left partially applied (A6).
    """
    transaction = transaction_repo.get_owned_by_id(
        db, transaction_id=transaction_id, user_id=owner.id
    )
    if transaction is None:
        raise TransactionNotFoundError()

    category = None
    if category_id is not None:
        category = category_repo.get_owned_by_id(db, category_id=category_id, user_id=owner.id)
        if category is None:
            raise TransactionCategoryNotFoundError()

    effective_type = type if type is not None else transaction.type
    effective_amount = amount if amount is not None else transaction.amount
    category_changed = category_id is not None and category_id != transaction.category_id
    type_changed = type is not None and type != transaction.type

    # spec BR-02, FR-07, plan.md A4: re-validate only when the effective
    # category or the effective type actually changed -- otherwise the
    # pairing is already known valid from creation time (TM-US-01 BR-03).
    if category_changed or type_changed:
        if category is None:
            category = category_repo.get_owned_by_id(
                db, category_id=transaction.category_id, user_id=owner.id
            )
            # transaction.category_id was itself validated as owner-owned at
            # creation time (TM-US-01 BR-01/FR-06) and is never written by
            # any other operation, so this lookup can never miss.
            assert category is not None
        if category.type.value != effective_type.value:
            raise TransactionCategoryTypeMismatchError()

    # spec BR-03, BR-04, plan.md A3, A5: reverse the stored effect first --
    # unconditionally either way, since undoing a real, already-applied
    # effect must never be refused.
    if transaction.type is TransactionType.EXPENSE:
        wallet_repo.increment_balance(
            db, wallet_id=transaction.wallet_id, amount=transaction.amount
        )
    else:
        wallet_repo.decrement_balance_unconditional(
            db, wallet_id=transaction.wallet_id, amount=transaction.amount
        )

    # spec BR-05: apply the effective new effect exactly as creation does.
    if effective_type is TransactionType.EXPENSE:
        affected = wallet_repo.decrement_balance(
            db, wallet_id=transaction.wallet_id, amount=effective_amount
        )
        if affected == 0:
            raise TransactionInsufficientBalanceError()
    else:
        wallet_repo.increment_balance(db, wallet_id=transaction.wallet_id, amount=effective_amount)

    transaction = transaction_repo.update_transaction(
        db,
        transaction=transaction,
        category_id=category_id,
        amount=amount,
        type=type,
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


def list_transactions(
    db: Session,
    *,
    owner: UserModel,
    page: int,
    page_size: int,
    wallet_id: str | None,
    category_id: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> TransactionListRead:
    """Assemble a page of the caller's own matching transactions into the
    TransactionListRead envelope (spec TM-US-02 AC-01, AC-09; plan.md A8),
    after resolving each date bound to an aware UTC instant (A6) and
    rejecting an inverted range (A7).
    """
    if date_from is not None:
        date_from = clock.ensure_aware(date_from)
    if date_to is not None:
        date_to = clock.ensure_aware(date_to)

    # spec AC-15, FR-12, BR-06, plan.md A7: the one cross-field rule Pydantic
    # cannot express alone. Reuses the existing generic ValidationError — no
    # new TRANSACTION_-prefixed code, the identical details.fields shape the
    # RequestValidationError handler already produces.
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValidationError(
            details={
                "fields": [
                    {
                        "location": ["query", "date_to"],
                        "message": "date_to must not be earlier than date_from.",
                        "type": "value_error",
                    }
                ]
            }
        )

    items, total = transaction_repo.list_owned(
        db,
        user_id=owner.id,
        page=page,
        page_size=page_size,
        wallet_id=wallet_id,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
    )
    return TransactionListRead(
        items=[
            TransactionRead(
                id=t.id,
                wallet_id=t.wallet_id,
                category_id=t.category_id,
                amount=t.amount,
                type=t.type,
                timestamp=clock.ensure_aware(t.timestamp),
                note=t.note,
            )
            for t in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_transaction(db: Session, *, owner: UserModel, transaction_id: str) -> TransactionRead:
    """Fetch one of `owner`'s own transactions by its own id (spec TM-US-03
    AC-01, FR-03; plan.md A1).

    No further precondition follows ownership — unlike
    `create_transaction()`'s multi-step check order (TM-US-01 A4), there is
    nothing else about a transaction's own state to check once it is
    confirmed to belong to the caller, because a view changes nothing.
    """
    transaction = transaction_repo.get_owned_by_id(
        db, transaction_id=transaction_id, user_id=owner.id
    )
    if transaction is None:
        raise TransactionNotFoundError()

    return TransactionRead(
        id=transaction.id,
        wallet_id=transaction.wallet_id,
        category_id=transaction.category_id,
        amount=transaction.amount,
        type=transaction.type,
        timestamp=clock.ensure_aware(transaction.timestamp),
        note=transaction.note,
    )
