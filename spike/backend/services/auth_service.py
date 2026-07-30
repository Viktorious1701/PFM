"""Login. Implied by the SRS's 'Caller is authenticated' preconditions."""

from sqlalchemy.orm import Session

from app.core.errors import AccountNotActiveError, InvalidCredentialsError
from app.core.security import verify_password
from app.models.user import User, UserStatus
from app.repositories import user_repo


def authenticate(db: Session, *, email: str, password: str) -> User:
    """Password is verified before status is inspected.

    Order matters: checking status first would let an attacker enumerate which
    addresses have pending invitations. A PENDING user has no password_hash, so
    verify_password fails against a dummy hash and they get a generic 401 —
    the 403 below only triggers for a *correct* password on a non-active
    account, which is the honest case worth distinguishing.
    """
    user = user_repo.get_by_email(db, email)

    if not verify_password(password, user.password_hash if user else None):
        raise InvalidCredentialsError()

    assert user is not None  # verify_password cannot succeed with no user

    if user.status is not UserStatus.ACTIVE:
        raise AccountNotActiveError()

    return user
