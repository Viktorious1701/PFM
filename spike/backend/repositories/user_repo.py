"""Data access for User. Plain functions taking a Session — no ORM cleverness."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserStatus


def normalize_email(email: str) -> str:
    """Single definition of 'the same email'."""
    return email.strip().lower()


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def get_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def get_by_token_hash(db: Session, token_hash: str) -> User | None:
    return db.scalar(select(User).where(User.invitation_token_hash == token_hash))


def list_users(db: Session, status: UserStatus | None = None) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if status is not None:
        stmt = stmt.where(User.status == status)
    return list(db.scalars(stmt).all())


def add_pending_user(
    db: Session,
    *,
    email: str,
    token_hash: str,
    expires_at: datetime,
    invited_by_id: str | None,
) -> User:
    user = User(
        email=normalize_email(email),
        status=UserStatus.PENDING,
        invitation_token_hash=token_hash,
        token_expires_at=expires_at,
        invited_by_id=invited_by_id,
    )
    db.add(user)
    db.flush()
    return user


def refresh_invitation(
    db: Session,
    user: User,
    *,
    token_hash: str,
    expires_at: datetime,
    invited_by_id: str | None,
) -> User:
    """Re-invite an existing PENDING user: new token, TTL reset from now."""
    user.invitation_token_hash = token_hash
    user.token_expires_at = expires_at
    user.invited_by_id = invited_by_id
    db.add(user)
    db.flush()
    return user
