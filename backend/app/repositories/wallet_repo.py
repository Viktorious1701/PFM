"""Wallet queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from decimal import Decimal
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

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
