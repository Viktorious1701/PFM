"""Transaction queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import CategoryModel
from app.models.transaction import TransactionModel, TransactionType
from app.models.wallet import WalletModel


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


def list_owned(
    db: Session,
    *,
    user_id: str,
    page: int,
    page_size: int,
    wallet_id: str | None = None,
    category_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[Sequence[TransactionModel], int]:
    """A page of transactions belonging to a wallet owned by `user_id`, plus
    that owner's own matching total count (spec TM-US-02 AC-01, AC-04, AC-05,
    AC-07, AC-10, AC-12, AC-14; plan.md A2, A3, A4).

    Ownership is transitive through a join to `wallets` (A2) — there is no
    `transactions.user_id` column to filter on directly. Every optional
    filter appends to one shared condition list, and **both** the count
    query and the page query are built from that same list object (not two
    independently-retyped predicates), which is what makes the two queries
    structurally unable to drift apart the way `test_cases.md` QF-10 warns
    against. Ordered by `timestamp` descending, `id` ascending as a
    deterministic tie-break (A4) — the composite index (A5) is keyed to
    serve exactly this ordering once `wallet_id` is also the join column.
    """
    conditions = [WalletModel.user_id == user_id]
    if wallet_id is not None:
        conditions.append(TransactionModel.wallet_id == wallet_id)
    if category_id is not None:
        conditions.append(TransactionModel.category_id == category_id)
    if date_from is not None:
        conditions.append(TransactionModel.timestamp >= date_from)
    if date_to is not None:
        conditions.append(TransactionModel.timestamp <= date_to)

    joined = select(TransactionModel).join(
        WalletModel, TransactionModel.wallet_id == WalletModel.id
    )

    total = (
        db.scalar(
            select(func.count())
            .select_from(TransactionModel)
            .join(WalletModel, TransactionModel.wallet_id == WalletModel.id)
            .where(*conditions)
        )
        or 0
    )
    items = db.scalars(
        joined.where(*conditions)
        .order_by(TransactionModel.timestamp.desc(), TransactionModel.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total


def get_summary_totals(
    db: Session, *, user_id: str, period_start: datetime, period_end: datetime
) -> dict[TransactionType, Decimal]:
    """Sum the caller's own transactions in [period_start, period_end), one
    entry per TransactionType actually present (spec AC-07, AC-08, BR-03;
    plan.md A4).

    A type with no qualifying transactions in the period produces no row at
    all -- GROUP BY omits empty groups (plan.md A7, empirically confirmed) --
    so the caller (report_service.get_summary_report) must default an absent
    key to Decimal("0.00"); a missing key is never an error.
    """
    conditions = [
        WalletModel.user_id == user_id,
        TransactionModel.timestamp >= period_start,
        TransactionModel.timestamp < period_end,
    ]
    rows = db.execute(
        select(TransactionModel.type, func.sum(TransactionModel.amount))
        .join(WalletModel, TransactionModel.wallet_id == WalletModel.id)
        .where(*conditions)
        .group_by(TransactionModel.type)
    ).all()
    return {row[0]: row[1] for row in rows}


def get_top_expense_categories(
    db: Session,
    *,
    user_id: str,
    period_start: datetime,
    period_end: datetime,
    limit: int,
) -> Sequence[tuple[str, str, Decimal]]:
    """The caller's own top `limit` expense categories in
    [period_start, period_end), highest total first, category_id ascending
    as a deterministic tie-break (spec AC-10, AC-12, BR-05; plan.md A5).

    Grouped by both categories.id and categories.name -- not id alone -- so
    this stays correct on PostgreSQL without relying on its primary-key
    functional-dependency allowance for GROUP BY (constitution ENV-03).
    """
    conditions = [
        WalletModel.user_id == user_id,
        TransactionModel.type == TransactionType.EXPENSE,
        TransactionModel.timestamp >= period_start,
        TransactionModel.timestamp < period_end,
    ]
    total = func.sum(TransactionModel.amount)
    rows = db.execute(
        select(CategoryModel.id, CategoryModel.name, total)
        .join(WalletModel, TransactionModel.wallet_id == WalletModel.id)
        .join(CategoryModel, TransactionModel.category_id == CategoryModel.id)
        .where(*conditions)
        .group_by(CategoryModel.id, CategoryModel.name)
        .order_by(total.desc(), CategoryModel.id.asc())
        .limit(limit)
    ).all()
    return [(row[0], row[1], row[2]) for row in rows]
