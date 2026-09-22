"""Wallet queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.wallet import WalletModel


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
