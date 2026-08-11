"""User queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import UserModel, UserRole, UserStatus


def normalize_email(raw: str) -> str:
    """The single definition of "the same mailbox" (spec FR-03, BR-01, VL-03).

    Trimmed and case-folded. Every uniqueness comparison and every insert goes
    through here, which is what makes EC-01 hold — `"  Family.Member@Gmail.COM  "`
    and `family.member@gmail.com` are one address, so no second account is
    created for a mailbox that already has one.

    `casefold()` rather than `lower()`: it is the Unicode-correct operation, and
    email local parts are not guaranteed ASCII.
    """
    return raw.strip().casefold()


def get_by_email(db: Session, email: str) -> UserModel | None:
    """Look a user up by *already normalised* email.

    Callers pass the output of `normalize_email`. Normalising here as well would
    hide the caller's obligation and make it easy to write a comparison that
    silently skips it.
    """
    return db.scalars(select(UserModel).where(UserModel.email == email)).one_or_none()


def get_by_id(db: Session, user_id: str) -> UserModel | None:
    return db.get(UserModel, user_id)


def add_pending_user(db: Session, email: str) -> UserModel:
    """Insert an invited account (spec AC-07, FR-05, FR-06).

    No password, no full name, non-privileged role. Flushed but **not
    committed** — the router owns the transaction boundary (AR-06, BR-08), so
    this row and its invitation commit together or not at all.
    """
    user = UserModel(
        email=email,
        password_hash=None,
        full_name=None,
        status=UserStatus.PENDING,
        role=UserRole.USER,
    )
    db.add(user)
    db.flush()
    return user


def activate(db: Session, user: UserModel, full_name: str, password_hash: str) -> UserModel:
    """Activate a PENDING user with their full name and password hash.

    Flushed, not committed (AR-06).
    """
    user.status = UserStatus.ACTIVE
    user.full_name = full_name
    user.password_hash = password_hash
    db.flush()
    return user


def list_users(db: Session, *, page: int, page_size: int) -> tuple[Sequence[UserModel], int]:
    """A page of every user, newest first, plus the unfiltered total count
    (spec UM-US-03 AC-01, AC-04, AC-05, AC-07; plan.md A1, A3).

    No status predicate — `PENDING`/`ACTIVE`/`DEACTIVATED` are all included
    (A1). Two queries: one for the bounded page, one for the total, since a
    single query cannot both `LIMIT` a page and count every row.
    """
    total = db.scalar(select(func.count()).select_from(UserModel)) or 0
    items = db.scalars(
        select(UserModel)
        .order_by(UserModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total
