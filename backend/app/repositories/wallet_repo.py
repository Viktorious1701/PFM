"""Wallet queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.core import clock
from app.models.wallet import WalletModel


def get_owned_by_id(db: Session, *, wallet_id: str, user_id: str) -> WalletModel | None:
    """spec FR-04, BR-01/BR-02, constitution SEC-08. Scoped by `user_id` in
    the query itself, so "does not exist" and "belongs to someone else"
    return the identical `None` — collapsed by construction, not by a check
    that could be forgotten (BM-US-01 plan.md A6).
    """
    return db.scalar(
        select(WalletModel).where(WalletModel.id == wallet_id, WalletModel.user_id == user_id)
    )


def update_wallet(
    db: Session, *, wallet: WalletModel, name: str | None, wallet_type: str | None
) -> WalletModel:
    """spec AC-01, FR-05, FR-06, FR-07, FR-10, BR-01 (plan.md A1, A3). Mutates
    only the field(s) actually submitted on an already-fetched,
    already-ownership-verified row -- currency and balance are never
    touched, and a field left as None keeps its existing stored value
    exactly. Flushed, not committed (AR-06) -- the router owns the
    transaction boundary.
    """
    if name is not None:
        wallet.name = name
    if wallet_type is not None:
        wallet.type = wallet_type
    db.add(wallet)
    db.flush()
    return wallet


def add_wallet(
    db: Session,
    *,
    user_id: str,
    name: str,
    wallet_type: str,
    currency: str,
    balance: Decimal,
) -> WalletModel:
    """Insert a new wallet (spec AC-01, FR-08, FR-09, BR-01).

    Flushed, not committed (AR-06) — the router owns the transaction
    boundary, so this is the same one-request-one-transaction shape as every
    other story, even though this story only ever writes one row.
    """
    wallet = WalletModel(
        user_id=user_id,
        name=name,
        type=wallet_type,
        currency=currency,
        balance=balance,
    )
    db.add(wallet)
    db.flush()
    return wallet


def decrement_balance(db: Session, *, wallet_id: str, amount: Decimal) -> int:
    """Conditionally subtract `amount` from a wallet's balance (spec FR-11,
    BR-05; plan.md A9).

    The sufficiency check *is* the WHERE clause — not a prior
    read-the-balance-then-compare-in-Python step — so two concurrent EXPENSE
    requests against the same wallet cannot both read the same pre-decrement
    balance and both conclude "sufficient" (the TOCTOU race plan.md A9 rules
    out by construction). Returns the affected row count: 1 if the balance
    was sufficient and the decrement applied, 0 if not — the service raises
    `TransactionInsufficientBalanceError` on 0. Mirrors
    `invitation_repo.mark_accepted()`'s conditional-UPDATE-as-atomic-mutex
    technique (UM-US-02 EC-05). Flushed, not committed (AR-06).
    """
    result = cast(
        "CursorResult[Any]",
        db.execute(
            update(WalletModel)
            .where(WalletModel.id == wallet_id, WalletModel.balance >= amount)
            .values(balance=WalletModel.balance - amount)
        ),
    )
    db.flush()
    return int(result.rowcount or 0)


def decrement_balance_unconditional(db: Session, *, wallet_id: str, amount: Decimal) -> None:
    """Unconditionally subtract `amount` from a wallet's balance (spec
    TM-US-04 BR-04; plan.md A5).

    Used only to reverse a previously applied INCOME transaction's effect.
    Unlike `decrement_balance()`'s conditional sufficiency check (TM-US-01
    A9), undoing a credit the wallet already legitimately holds must never
    be refused, regardless of the wallet's current balance. Flushed, not
    committed (AR-06).
    """
    db.execute(
        update(WalletModel)
        .where(WalletModel.id == wallet_id)
        .values(balance=WalletModel.balance - amount)
    )
    db.flush()


def list_owned(
    db: Session, *, user_id: str, page: int, page_size: int
) -> tuple[Sequence[WalletModel], int]:
    """A page of wallets owned by `user_id`, plus that owner's own total count
    (spec WM-US-02 AC-01, AC-04, AC-05, AC-07; plan.md A1, A3). WM-US-05
    A3: both queries also exclude archived wallets
    (`WalletModel.archived_at.is_(None)`), so an archived wallet disappears
    from the caller's default list (WM-US-05 AC-06) without reopening this
    story's own pagination, ordering, or ownership-scoping decisions -- the
    identical kind of additive WHERE predicate this function's own
    ownership scope already required to apply to both queries together.

    Both queries carry the identical `user_id` predicate (constitution
    SEC-08) — the total is the caller's own wallet count, never the
    system-wide row count (test_cases.md QF-05). Ordered by `id`, the one
    column guaranteed to exist and be unique without a schema change (A1);
    this order carries no chronological meaning.
    """
    total = (
        db.scalar(
            select(func.count())
            .select_from(WalletModel)
            .where(
                WalletModel.user_id == user_id,
                WalletModel.archived_at.is_(None),
            )
        )
        or 0
    )
    items = db.scalars(
        select(WalletModel)
        .where(
            WalletModel.user_id == user_id,
            WalletModel.archived_at.is_(None),
        )
        .order_by(WalletModel.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total


def archive_wallet(db: Session, *, wallet: WalletModel) -> WalletModel:
    """spec AC-01, AC-05, FR-04, FR-05 (plan.md A1, A6). Idempotent: stamps
    `archived_at` with the current time only if the wallet is not already
    archived -- a repeat call leaves the original timestamp untouched
    rather than overwriting it with a fresh one. Flushed, not committed
    (AR-06) -- the router owns the transaction boundary.
    """
    if wallet.archived_at is None:
        wallet.archived_at = clock.utcnow()
        db.add(wallet)
        db.flush()
    return wallet


def increment_balance(db: Session, *, wallet_id: str, amount: Decimal) -> None:
    """Unconditionally add `amount` to a wallet's balance (spec FR-12, BR-05;
    plan.md A9).

    An INCOME transaction has no sufficiency condition to check (A2), so
    this is a plain unconditional UPDATE. Flushed, not committed (AR-06).
    """
    db.execute(
        update(WalletModel)
        .where(WalletModel.id == wallet_id)
        .values(balance=WalletModel.balance + amount)
    )
    db.flush()


def delete_all_for_owner(db: Session, *, user_id: str) -> int:
    """Delete every wallet `user_id` owns; returns how many (SS-US-03 plan.md
    A8). Called only by the guest purge, after the transactions and budgets on
    these wallets are gone. Flushed, not committed (AR-06).
    """
    result = cast(
        "CursorResult[Any]",
        db.execute(
            delete(WalletModel)
            .where(WalletModel.user_id == user_id)
            .execution_options(synchronize_session=False)
        ),
    )
    db.flush()
    return int(result.rowcount or 0)
