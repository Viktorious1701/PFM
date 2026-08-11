"""List-users business rules (spec UM-US-03, SDS §5.2.3).

Constitution:
  AR-01  DTO assembly lives here, not in the router
  AR-05  no framework objects — plain `page`/`page_size` ints in, a DTO out
  AR-06  pure read; there is nothing to commit (plan.md A4)
"""

from sqlalchemy.orm import Session

from app.core import clock
from app.repositories import user_repo
from app.schemas.user import UserListRead, UserRead


def list_users(db: Session, *, page: int, page_size: int) -> UserListRead:
    """Assemble a page of users into the `UserListRead` envelope (plan.md A6).

    `created_at` passes through `clock.ensure_aware()` before serialising —
    SQLite drops `tzinfo` on read, and a naive timestamp in the response is
    the exact defect UM-US-01 shipped once already.
    """
    items, total = user_repo.list_users(db, page=page, page_size=page_size)
    return UserListRead(
        items=[
            UserRead(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                status=user.status,
                created_at=clock.ensure_aware(user.created_at),
            )
            for user in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
