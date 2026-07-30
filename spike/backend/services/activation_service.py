"""US-01-02: Activate User Account."""

from sqlalchemy.orm import Session

from app.core.clock import ensure_aware, utcnow
from app.core.errors import TokenExpiredError, TokenNotFoundError
from app.core.security import hash_password, hash_token
from app.models.user import User, UserStatus
from app.repositories import user_repo


def resolve_invitation(db: Session, raw_token: str) -> User:
    """AC-1 + AC-2: the token must exist and must not have expired.

    Used both by the pre-flight GET and by activation itself, so the two can
    never disagree about whether a token is usable.
    """
    user = user_repo.get_by_token_hash(db, hash_token(raw_token))

    # AC-1. Also the already-activated case: activation nulls the hash, so a
    # replayed link lands here rather than reporting 'expired'.
    if user is None or user.status is not UserStatus.PENDING:
        raise TokenNotFoundError()

    if user.token_expires_at is None:
        raise TokenNotFoundError()

    # AC-2. `ensure_aware` because SQLite hands back naive datetimes.
    if ensure_aware(user.token_expires_at) <= utcnow():
        raise TokenExpiredError(
            f"Invitation token expired at {ensure_aware(user.token_expires_at).isoformat()}."
        )

    return user


def activate(db: Session, *, raw_token: str, full_name: str, password: str) -> User:
    """AC-3 through AC-6. Caller commits, so the whole state change lands in one
    transaction (NFR-4): status flip and token invalidation cannot diverge."""
    user = resolve_invitation(db, raw_token)

    user.full_name = full_name.strip()
    user.password_hash = hash_password(password)  # AC-4
    user.status = UserStatus.ACTIVE  # AC-5
    # AC-5: single-use. Clearing these is what makes the link unreplayable.
    user.invitation_token_hash = None
    user.token_expires_at = None

    db.add(user)
    db.flush()
    return user
