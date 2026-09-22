"""Category queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from sqlalchemy import select
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
