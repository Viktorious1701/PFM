"""Category queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from sqlalchemy.orm import Session

from app.models.category import CategoryModel, CategoryType


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
