"""Invitation business rules (spec UM-US-01, SDS §5.2.1).

Constitution:
  AR-01  every business rule in this story lives here, not in the router
  AR-05  no framework objects — the router keeps BackgroundTasks to itself
  AR-06  this module flushes; the router commits. One request, one transaction

The service never commits. That is what makes spec BR-08 true: the `users` row
and its `invitations` row reach the database together or not at all.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit, clock, security
from app.core.config import Settings
from app.core.errors import EmailDeliveryError, UserEmailAlreadyActiveError
from app.models.invitation import InvitationModel
from app.models.user import UserModel, UserStatus
from app.repositories import invitation_repo, user_repo
from app.services.email.sender import EmailDeliveryFailed, EmailSender
from app.services.email.templates import build_invitation_email

logger = logging.getLogger(__name__)

SUCCESS_MESSAGE = "Invitation sent successfully"
REINVITE_MESSAGE = "A new invitation has been sent. The previous link no longer works."


@dataclass(frozen=True)
class InvitationResult:
    """Outcome of a successful invitation.

    `raw_token` is carried out of the service **only** so the router can hand it
    to the email sender. It must never reach a response body, a log line or an
    audit record (spec AC-08, BR-07, SEC-03) — `InvitationRead` has no field for
    it, which is the structural guard.
    """

    user: UserModel
    invitation: InvitationModel
    raw_token: str
    reinvited: bool

    @property
    def message(self) -> str:
        return REINVITE_MESSAGE if self.reinvited else SUCCESS_MESSAGE


def create_invitation(
    db: Session,
    *,
    raw_email: str,
    invited_by: UserModel,
    settings: Settings,
) -> InvitationResult:
    """Create (or re-issue) an invitation for an email address.

    Raises `UserEmailAlreadyActiveError` when the address already belongs to an
    account that must not be replaced (spec AC-02, EC-01, EC-05).
    """
    # spec FR-03 / EC-01: normalise before any comparison or insert, so one
    # mailbox maps to exactly one account.
    email = user_repo.normalize_email(raw_email)

    existing = user_repo.get_by_email(db, email)

    # spec AC-02 / FR-04 / BR-02: an ACTIVE account blocks the invitation.
    #
    # DEACTIVATED is blocked too. That is NOT what BR-02 literally says — it
    # names only ACTIVE — but re-inviting a DEACTIVATED address would silently
    # resurrect a disabled account, a security decision no AC or EC authorises.
    # Blocking is the conservative reading; the error code is imprecise for that
    # case. Raised as finding F1 in plan.md for a ruling rather than settled
    # silently here.
    #
    # Checked outside the try below so this deliberate 409 can never be confused
    # with the incidental one an IntegrityError produces.
    if existing is not None and existing.status is not UserStatus.PENDING:
        raise UserEmailAlreadyActiveError(details={"email": email})

    # spec AC-06 / FR-08 / FR-09: 256-bit token, expiry exactly TTL hours out.
    raw_token = security.generate_invitation_token()
    expires_at = _expiry(settings.invitation_ttl_hours)

    try:
        if existing is None:
            # spec AC-07 / FR-05 / FR-06: no credentials, no name, role USER.
            user, reinvited = user_repo.add_pending_user(db, email), False
        else:
            # spec EC-02 / EC-03: the recovery path. Same account, fresh token.
            # Works identically whether the previous invitation expired or never
            # arrived — expiry is derived, so an expired invitation is still
            # PENDING and gets superseded just the same.
            user, reinvited = existing, True

        # spec FR-11 / BR-03: whatever was outstanding stops working the moment a
        # new invitation is issued. A no-op for a brand-new address, and cheaper
        # than reasoning about whether it is needed.
        invitation_repo.supersede_outstanding(db, email)

        invitation = invitation_repo.add(
            db,
            email=email,
            token_hash=security.hash_token(raw_token),
            expires_at=expires_at,
            invited_by_id=invited_by.id,
        )
    except IntegrityError as exc:
        # spec EC-05 / FR-18 / VL-05: the unique index is the second line of
        # defence behind the check above. A concurrent writer that wins the race
        # must produce a 409, never a 500. Covers both inserts — the users row is
        # where the race is actually lost.
        raise UserEmailAlreadyActiveError(details={"email": email}) from exc

    # spec AC-09 / FR-17, LA-02: actor, timestamp, action, target, result — and
    # no token. `audit.record` rejects any field whose name looks like a secret.
    audit.record(
        action="USER_INVITED",
        actor_id=invited_by.id,
        target=email,
        result="SUCCESS",
        invited_user_id=user.id,
        reinvited=reinvited,
    )

    return InvitationResult(
        user=user, invitation=invitation, raw_token=raw_token, reinvited=reinvited
    )


def _expiry(ttl_hours: int) -> datetime:
    """spec FR-09 / AC-06 / BR-04, plan.md A5.

    Computed from the clock seam so tests can freeze time, and derived on read
    rather than tracked by a sweeper.
    """
    return clock.utcnow() + timedelta(hours=ttl_hours)


def send_invitation_email(
    *,
    sender: EmailSender,
    settings: Settings,
    to_email: str,
    raw_token: str,
) -> None:
    """Dispatch the activation email (spec AC-01, FR-12).

    Raises `EmailDeliveryError` so a sync-mode caller can return 502 (spec EC-07,
    FR-20). Callers running this in the background must catch it and log —
    see `send_invitation_email_safely`.
    """
    message = build_invitation_email(
        to_email=to_email,
        raw_token=raw_token,
        activation_url_template=settings.activation_url_template,
        expires_in_hours=settings.invitation_ttl_hours,
    )
    try:
        sender.send(message)
    except EmailDeliveryFailed as exc:
        raise EmailDeliveryError(details={"email": to_email}) from exc


def send_invitation_email_safely(
    *,
    sender: EmailSender,
    settings: Settings,
    to_email: str,
    raw_token: str,
) -> None:
    """Background-mode dispatch (spec EC-06, FR-21).

    A failure here happens after the response has already been sent, so it
    cannot be surfaced to the caller. It is logged instead, and the invitation
    stays `PENDING` and re-invitable — which is the recovery EC-06 promises and
    test_cases TC-21 proves. What must never happen is the failure vanishing
    without a trace (SC-09).
    """
    try:
        send_invitation_email(
            sender=sender, settings=settings, to_email=to_email, raw_token=raw_token
        )
    except EmailDeliveryError as exc:
        logger.error(
            "invitation email delivery failed for %s: %s — invitation remains re-invitable",
            to_email,
            exc.message,
        )
        audit.record(
            action="INVITATION_EMAIL_FAILED",
            actor_id=None,
            target=to_email,
            result="FAILURE",
        )
