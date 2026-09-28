"""Transaction queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.transaction import TransactionModel, TransactionType


def add_transaction(
    db: Session,
    *,
    wallet_id: str,
    category_id: str,
    amount: Decimal,
    type: TransactionType,
    timestamp: datetime,
    note: str | None,
) -> TransactionModel:
    """Insert a new transaction (spec AC-01, AC-02, FR-16, BR-01).

    Flushed, not committed (AR-06) — the router owns the transaction
    boundary; this call and `wallet_repo`'s balance mutation are flushed
    within the same request so both changes reach the database inside one
    commit (FR-13, BR-07, plan.md A10).
    """
    transaction = TransactionModel(
        wallet_id=wallet_id,
        category_id=category_id,
        amount=amount,
        type=type,
        timestamp=timestamp,
        note=note,
    )
    db.add(transaction)
    db.flush()
    return transaction
