"""Category business rules (spec CM-US-01, SDS §5.4.1).

Constitution:
  AR-01  the owner-assignment rule lives here, not in the router
  AR-05  no framework objects — plain values only
  AR-06  this module flushes; the router commits. One request, one transaction

No audit call (plan.md A8) — category creation is not one of constitution
LA-04's three named audited events, and no AC or FR in spec.md asks for one.
"""

from sqlalchemy.orm import Session

from app.models.category import CategoryType
from app.models.user import UserModel
from app.repositories import category_repo
from app.schemas.category import CategoryListRead, CategoryRead


def create_category(
    db: Session,
    *,
    owner: UserModel,
    name: str,
    category_type: CategoryType,
) -> CategoryRead:
    """Create a category owned by `owner` (spec AC-01, AC-07, FR-05, BR-01).

    The owner is read from `owner.id` — the authenticated caller resolved by
    `CurrentUserDep` — never from any value in the request payload
    (`CategoryCreate` declares no `user_id` field to read from instead;
    plan.md A6).
    """
    category = category_repo.add_category(
        db,
        user_id=owner.id,
        name=name,
        category_type=category_type,
    )
    return CategoryRead(
        id=category.id,
        user_id=category.user_id,
        name=category.name,
        type=category.type,
    )


def list_categories(
    db: Session, *, owner: UserModel, page: int, page_size: int
) -> CategoryListRead:
    """Assemble a page of the caller's own categories into the
    `CategoryListRead` envelope (spec CM-US-02 AC-01, AC-04, AC-05, AC-07,
    AC-09; plan.md A2, A3).

    Unlike `user_service.list_users`, this calls no `clock.ensure_aware()` —
    `CategoryRead` carries no datetime field to normalise (mirrors
    `wallet_service.list_wallets`, WM-US-02).
    """
    items, total = category_repo.list_owned(db, user_id=owner.id, page=page, page_size=page_size)
    return CategoryListRead(
        items=[
            CategoryRead(
                id=c.id,
                user_id=c.user_id,
                name=c.name,
                type=c.type,
            )
            for c in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
