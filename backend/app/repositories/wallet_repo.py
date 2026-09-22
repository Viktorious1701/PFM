"""Wallet queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from decimal import Decimal

from sqlalchemy import select
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
