"""Category queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import CategoryModel, CategoryType


def get_owned_by_id(db: Session, *, category_id: str, user_id: str) -> CategoryModel | None:
    """spec FR-06, BR-01/BR-02, constitution SEC-08. Same shape as
    `wallet_repo.get_owned_by_id()` (BM-US-01 plan.md A6).
    """
    return db.scalar(
        select(CategoryModel).where(
            CategoryModel.id == category_id, CategoryModel.user_id == user_id
        )
    )


def add_category(
    db: Session,
    *,
    user_id: str,
    name: str,
    category_type: CategoryType,
) -> CategoryModel:
    """Insert a new category (spec AC-01, FR-01, BR-01).

    Flushed, not committed (AR-06) — the router owns the transaction
    boundary, the same one-request-one-transaction shape as every other
    story.
    """
    category = CategoryModel(
        user_id=user_id,
        name=name,
        type=category_type,
    )
    db.add(category)
    db.flush()
    return category


def list_owned(
    db: Session, *, user_id: str, page: int, page_size: int
) -> tuple[Sequence[CategoryModel], int]:
    """A page of categories owned by `user_id`, plus that owner's own total
    count (spec CM-US-02 AC-01, AC-04, AC-05, AC-07; plan.md A1, A3).

    Both queries carry the identical `user_id` predicate (constitution
    SEC-08) — the total is the caller's own category count, never the
    system-wide row count (test_cases.md QF-05). Ordered by `id`, the one
    column guaranteed to exist and be unique without a schema change (A1);
    this order carries no chronological meaning. Mirrors
    `wallet_repo.list_owned()` exactly (WM-US-02) — the same single-table
    shape, no join.
    """
    total = (
        db.scalar(
            select(func.count()).select_from(CategoryModel).where(CategoryModel.user_id == user_id)
        )
        or 0
    )
    items = db.scalars(
        select(CategoryModel)
        .where(CategoryModel.user_id == user_id)
        .order_by(CategoryModel.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total
