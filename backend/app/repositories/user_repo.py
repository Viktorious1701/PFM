"""User queries.

Constitution AR-03: queries only. No business rules, no commits — the service
decides *what* to do, this module only knows *how* to ask the database.
"""

from collections.abc import Sequence
from datetime import datetime

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
    """A page of every family member, newest first, plus their total count
    (spec UM-US-03 AC-01, AC-04, AC-05, AC-07; plan.md A1, A3).

    No status predicate — `PENDING`/`ACTIVE`/`DEACTIVATED` are all included
    (A1). Two queries: one for the bounded page, one for the total, since a
    single query cannot both `LIMIT` a page and count every row.

    SS-US-03 plan.md A13: guests are not family members (spec AC-08), so both
    queries exclude `role = GUEST` — the page and the total agree.
    """
    not_guest = UserModel.role != UserRole.GUEST
    total = db.scalar(select(func.count()).select_from(UserModel).where(not_guest)) or 0
    items = db.scalars(
        select(UserModel)
        .where(not_guest)
        .order_by(UserModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total


# --- SS-US-03: Guest trial ---------------------------------------------------


def add_guest_user(db: Session, *, email: str, expires_at: datetime) -> UserModel:
    """Insert a guest trial account (SS-US-03 spec FR-02; plan.md A1, A2).

    Usable at once (`ACTIVE`), never invited, no password and no name, and a
    trial end. `email` is the caller's reserved `.invalid` placeholder, so the
    row is never mailable (SEC-12). Flushed, not committed (AR-06).
    """
    user = UserModel(
        email=email,
        password_hash=None,
        full_name=None,
        status=UserStatus.ACTIVE,
        role=UserRole.GUEST,
        expires_at=expires_at,
    )
    db.add(user)
    db.flush()
    return user


def list_ended_guests(db: Session, *, now: datetime) -> Sequence[UserModel]:
    """Guests whose trial is over at `now` — `expires_at <= now` (spec BR-01:
    over *at* its end, not one tick after)."""
    return db.scalars(
        select(UserModel).where(UserModel.role == UserRole.GUEST, UserModel.expires_at <= now)
    ).all()


def count_guests(db: Session) -> int:
    """Every remaining guest row. Called after the purge, so each is live (A12)."""
    return (
        db.scalar(
            select(func.count()).select_from(UserModel).where(UserModel.role == UserRole.GUEST)
        )
        or 0
    )


def delete_user(db: Session, user: UserModel) -> None:
    """Delete one user row. Its owned rows must already be gone (plan.md A8 —
    nothing cascades). Flushed, not committed (AR-06)."""
    db.delete(user)
    db.flush()
