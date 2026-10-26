"""Login business rules (spec SS-US-01, SDS §5.1.1).

Constitution:
  AR-01  every business rule in this story lives here, not in the router
  SEC-10 no account enumeration
  BR-01  (spec) password verification precedes state checks — for accounts
         that hold a password. PENDING is the deliberate exception: see F2.
"""

from sqlalchemy.orm import Session

from app.core import audit, security
from app.core.config import Settings
from app.core.errors import AccountNotActivatedError, InvalidCredentialsError
from app.models.user import UserModel, UserRole, UserStatus
from app.repositories import user_repo
from app.schemas.auth import LogoutResult, TokenResponse

# A1/A5: a fixed dummy hash, computed once, so a login attempt against an
# unknown email costs the same wall-clock time as one against a known email
# with the wrong password — closing the timing side channel AC-03's
# indistinguishability promise would otherwise leave open.
_DUMMY_PASSWORD_HASH = security.hash_password("dummy-placeholder-for-timing-parity")


def authenticate(
    db: Session, *, raw_email: str, password: str, settings: Settings
) -> TokenResponse:
    """Authenticate a login attempt and issue a token on success.

    Order matters (spec BR-01, F2): PENDING is checked first and
    unconditionally, because a PENDING account holds no password to compare
    against (password_hash is NULL) — checking password first there would
    make AC-02's SRS-mandated message permanently unreachable. Every other
    outcome (ACTIVE, DEACTIVATED, no match) verifies the password first.
    """
    email = user_repo.normalize_email(raw_email)
    user = user_repo.get_by_email(db, email)

    if user is not None and user.status is UserStatus.PENDING:
        audit.record(
            action="LOGIN_FAILED",
            actor_id=user.id,
            target=email,
            result="FAILURE",
            reason="not_activated",
        )
        raise AccountNotActivatedError()

    hash_to_check = user.password_hash if user is not None else None
    # SS-US-03 plan.md F1: the dummy comparison runs for timing parity only —
    # it can never *count* as a match. Before guests, every non-PENDING account
    # had a hash, so a matched user with no hash was unreachable; a guest is
    # the first ACTIVE account without one, and the dummy plaintext is in this
    # file. So a password is verified only against a real hash, and a GUEST is
    # never signed into by credentials at all (SEC-12) — both refused with the
    # same generic outcome as a wrong password (SEC-10).
    password_ok = security.verify_password(password, hash_to_check or _DUMMY_PASSWORD_HASH)
    password_ok = password_ok and hash_to_check is not None

    if user is None or not password_ok or user.role is UserRole.GUEST:
        audit.record(
            action="LOGIN_FAILED",
            actor_id=None,
            target=email,
            result="FAILURE",
            reason="invalid_credentials",
        )
        raise InvalidCredentialsError()

    if user.status is UserStatus.DEACTIVATED:
        audit.record(
            action="LOGIN_FAILED",
            actor_id=user.id,
            target=email,
            result="FAILURE",
            reason="deactivated",
        )
        raise InvalidCredentialsError()

    # user.status is ACTIVE — the only status that reaches here.
    token = security.encode_jwt(
        subject=user.id,
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
        algorithm=settings.jwt_algorithm,
    )

    audit.record(
        action="LOGIN_SUCCESS",
        actor_id=user.id,
        target=email,
        result="SUCCESS",
    )

    # A GUEST was refused above (plan.md F1), so only a member's role remains.
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_ttl_minutes * 60,
        role="ADMIN" if user.role is UserRole.ADMIN else "USER",
    )


def logout(current_user: UserModel) -> LogoutResult:
    """End the caller's session (spec SS-US-02 AC-01, FR-02).

    `current_user` is only accepted to keep this function's signature
    consistent with every other service call taking a resolved caller — it is
    not read. No repository call, no write, no audit event (plan.md A2/A4):
    `CurrentUserDep` already did the one piece of enforcement this endpoint
    needs (BR-01) before this function ever runs. There is no server-side
    revocation store to write to (FR-05, EC-02) — the token presented here
    keeps authenticating until its own natural expiry (BR-02).
    """
    return LogoutResult(status="SUCCESS", message="Session ended. Please discard your token.")
