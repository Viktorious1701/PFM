"""FastAPI dependencies.

Includes the auth chain designed as plan.md T-15. See **plan.md A11**: UM-US-01
ships JWT *verification*; the login endpoint that issues tokens remains
SS-US-01's to deliver. That is enough for spec AC-04 and AC-05, which only need
a caller's identity and role to be established.

Constitution: AR-02 (thin router — dependencies do the resolving), SEC-06,
SEC-07, API-08.
"""

import logging
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import Settings, get_settings
from app.core.errors import ForbiddenError, NotAuthenticatedError

# Re-exported so every dependency this app uses is discoverable here. The
# transaction rule it enforces is unchanged: it rolls back on exception, and
# services never commit — the router owns the boundary (AR-06).
from app.db.session import get_db
from app.models.user import UserModel, UserRole, UserStatus
from app.repositories import user_repo
from app.services.email.outbox import FileOutboxSender
from app.services.email.sender import EmailSender, RecordingEmailSender
from app.services.email.smtp import GmailSmtpSender

logger = logging.getLogger(__name__)


SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[Session, Depends(get_db)]


def get_email_sender(settings: SettingsDep) -> EmailSender:
    """Choose a sender per `settings.email_transport` (UM-US-01 A13).

    `"outbox"` writes to a file so an ADMIN can read the activation link
    without a real mailbox (the dev outbox route, A14). `"smtp"` forces the
    real sender even without credentials, so a misconfiguration surfaces
    immediately as `EmailDeliveryFailed` rather than silently degrading —
    intentionally the opposite default from `"auto"`. `"auto"` (default)
    keeps the original behaviour: real SMTP when credentials exist, a
    recording double otherwise, so a developer with no Gmail App Password
    still gets a working invite flow while `EMAIL_SEND_MODE=sync` with real
    credentials still produces the 502 spec EC-07 requires.
    """
    if settings.email_transport == "outbox":
        return FileOutboxSender(directory=settings.outbox_dir)

    if settings.email_transport == "smtp" or settings.smtp_configured:
        return GmailSmtpSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
            from_address=settings.email_from,
        )

    logger.warning(
        "SMTP is not configured — using RecordingEmailSender. No mail will actually be sent."
    )
    return RecordingEmailSender()


EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]


# SDS §6.1: `Authorization: Bearer <JWT_ACCESS_TOKEN>`.
#
# Declared as a security scheme rather than a raw `Header()` parameter for two
# reasons. It puts the scheme in the OpenAPI document, so Swagger renders an
# **Authorize** button that prepends "Bearer " itself — a plain header box
# invites pasting the bare token, which then fails with a 401 that looks like a
# bad token rather than a missing prefix. And it keeps the parsing in one
# audited place instead of hand-rolled string splitting.
#
# `auto_error=False` is load-bearing: with the default, FastAPI raises its own
# error for absent credentials, bypassing the API-02 envelope and the single 401
# that spec AC-05 requires. Returning None instead lets the check below raise
# `NotAuthenticatedError` for every failure mode alike. HTTPBearer returns None
# for a missing header, a missing scheme, missing credentials, and a non-bearer
# scheme — all of which must be 401.
bearer_scheme = HTTPBearer(
    scheme_name="BearerToken",
    description=(
        "Paste only the JWT — Swagger adds the `Bearer ` prefix. "
        "Get one with: uv run python -m app.cli mint-token --email you@example.com"
    ),
    auto_error=False,
)

BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_current_user(
    db: DbDep,
    settings: SettingsDep,
    credentials: BearerDep = None,
) -> UserModel:
    """Resolve the caller from a bearer token (spec AC-05, FR-15).

    Every failure mode — header absent, wrong scheme, bad signature, expired,
    subject unknown, account not ACTIVE — produces the same 401. Spec AC-05 draws
    no distinction between "no credentials" and "invalid or expired credentials",
    and distinguishing them would tell an attacker which half to work on
    (SEC-10).

    This dependency runs **before** `require_admin`, so 401 always takes
    precedence over 403 (plan.md A8, test_cases TC-13).
    """
    if credentials is None:
        raise NotAuthenticatedError()

    token = credentials.credentials

    try:
        payload = security.decode_jwt(token, settings.jwt_secret, settings.jwt_algorithm)
    except jwt.InvalidTokenError as exc:
        # Covers ExpiredSignatureError, InvalidSignatureError, DecodeError.
        raise NotAuthenticatedError() from exc

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise NotAuthenticatedError()

    user = user_repo.get_by_id(db, subject)
    if user is None:
        raise NotAuthenticatedError()

    # spec BR-06: a PENDING account holds no credentials and cannot act. A
    # DEACTIVATED one has had them withdrawn. Neither may pass, even holding a
    # token that is still cryptographically valid.
    if user.status is not UserStatus.ACTIVE:
        raise NotAuthenticatedError()

    return user


CurrentUserDep = Annotated[UserModel, Depends(get_current_user)]


def require_admin(current_user: CurrentUserDep) -> UserModel:
    """Restrict to ADMIN callers (spec AC-04, FR-14, BR-05).

    Depends on `get_current_user`, which is what guarantees the 401-before-403
    ordering rather than leaving it to route declaration order.
    """
    if current_user.role is not UserRole.ADMIN:
        raise ForbiddenError()
    return current_user


AdminDep = Annotated[UserModel, Depends(require_admin)]
