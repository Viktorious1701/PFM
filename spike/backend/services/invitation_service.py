"""US-01-01: Invite a User via Email.

Split in two on purpose:
  create_invitation()      -> DB work, returns the raw token to the caller
  send_invitation_email()  -> pure I/O, safe to run in a BackgroundTask

That split is what lets the endpoint answer inside NFR-3's 500ms budget while
still satisfying AC-5, and it keeps the DB logic testable without any SMTP.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import Settings
from app.core.errors import EmailAlreadyActiveError
from app.core.security import generate_invitation_token, hash_token
from app.models.user import User, UserStatus
from app.repositories import user_repo
from app.services.email.sender import EmailSender
from app.services.email.templates import build_invitation_email

logger = logging.getLogger(__name__)


@dataclass
class Invitation:
    user: User
    raw_token: str
    was_resent: bool


def create_invitation(
    db: Session,
    *,
    email: str,
    settings: Settings,
    invited_by_id: str | None = None,
) -> Invitation:
    """AC-2 through AC-4. Caller commits.

    Email *format* validation (AC-1) happens earlier, in the Pydantic schema.
    """
    existing = user_repo.get_by_email(db, email)

    if existing is not None and existing.status is UserStatus.ACTIVE:
        # AC-2. Note this is an intentional existence disclosure: an admin
        # inviting someone needs to know the account is already live.
        raise EmailAlreadyActiveError()

    raw_token = generate_invitation_token()  # AC-3
    expires_at = utcnow() + timedelta(hours=settings.invitation_ttl_hours)

    if existing is None:
        user = user_repo.add_pending_user(  # AC-4
            db,
            email=email,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
            invited_by_id=invited_by_id,
        )
        was_resent = False
    else:
        # Re-inviting a PENDING address: rotate the token and restart the TTL.
        # The SRS only forbids duplicates in ACTIVE status, and this is the
        # obvious recovery path once a first invitation has expired.
        user = user_repo.refresh_invitation(
            db,
            existing,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
            invited_by_id=invited_by_id,
        )
        was_resent = True

    return Invitation(user=user, raw_token=raw_token, was_resent=was_resent)


def send_invitation_email(
    *,
    sender: EmailSender,
    settings: Settings,
    recipient: str,
    raw_token: str,
) -> None:
    """AC-5. Raises EmailDeliveryError, which is fatal in sync mode and logged
    in background mode (the response has already been sent by then)."""
    message = build_invitation_email(
        recipient=recipient,
        activation_url=settings.activation_url(raw_token),
        ttl_hours=settings.invitation_ttl_hours,
    )
    sender.send(message)


def send_invitation_email_safely(
    *,
    sender: EmailSender,
    settings: Settings,
    recipient: str,
    raw_token: str,
) -> None:
    """Background-task wrapper: never raise into the event loop, always log.

    A failure here means the user got a 201 but no email. The recovery path is
    to invite the same address again, which rotates the token and resends.
    """
    try:
        send_invitation_email(
            sender=sender, settings=settings, recipient=recipient, raw_token=raw_token
        )
    except Exception:
        logger.exception("invitation email dispatch failed for %s", recipient)
