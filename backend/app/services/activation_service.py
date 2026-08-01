"""Activation business rules (spec UM-US-02, SDS §5.2.2).

Constitution:
  AR-01  every business rule in this story lives here, not in the router
  AR-06  this module flushes; the router commits. One request, one transaction
  BR-02  fixed order of evaluation: outstanding state, then user state, then expiry last
"""

import logging

from sqlalchemy.orm import Session

from app.core import audit, security
from app.core.errors import (
    InvitationTokenExpiredError,
    InvitationTokenInvalidError,
)
from app.models.invitation import InvitationStatus
from app.models.user import UserStatus
from app.repositories import invitation_repo, user_repo
from app.schemas.activation import ActivationResult, TokenStateRead

logger = logging.getLogger(__name__)

ACTIVATION_SUCCESS_MESSAGE = "Account activated successfully. You may now log in."


def check_token_state(db: Session, raw_token: str) -> TokenStateRead:
    """Report a token's state without consuming it (spec AC-11, UXR-04).

    Evaluates checks in strict BR-02 order:
    1. Invitation exists and status == PENDING
    2. User status == PENDING
    3. Expiry (not expired)
    """
    token_hash = security.hash_token(raw_token)
    invitation = invitation_repo.get_by_token_hash(db, token_hash)

    if invitation is None or invitation.status is not InvitationStatus.PENDING:
        return TokenStateRead(state="not_usable")

    user = user_repo.get_by_email(db, invitation.email)
    if user is None or user.status is not UserStatus.PENDING:
        return TokenStateRead(state="not_usable")

    if invitation.is_expired():
        return TokenStateRead(state="expired")

    return TokenStateRead(state="usable")


def activate_account(
    db: Session,
    *,
    raw_token: str,
    full_name: str,
    password: str,
) -> ActivationResult:
    """Activate an account using a valid invitation token.

    Applies the fixed BR-02 check order and atomic invitation claim (A8).
    Flushes but does not commit — the router owns the transaction boundary (AR-06).
    """
    token_hash = security.hash_token(raw_token)
    invitation = invitation_repo.get_by_token_hash(db, token_hash)

    # BR-02 Check 1: Invitation must exist and be PENDING
    if invitation is None or invitation.status is not InvitationStatus.PENDING:
        # spec FR-17 / BR-07, constitution LA-01: no fragment of the raw token —
        # even a short prefix is still secret material, and `audit.record`'s
        # forbidden-key guard only scans `**extra` names, not this field's value.
        audit.record(
            action="USER_ACTIVATION_FAILED",
            actor_id=None,
            target="unknown",
            result="FAILURE",
            reason="invalid_token",
        )
        raise InvitationTokenInvalidError()

    user = user_repo.get_by_email(db, invitation.email)
    # BR-02 Check 2: User must exist and be PENDING
    if user is None or user.status is not UserStatus.PENDING:
        audit.record(
            action="USER_ACTIVATION_FAILED",
            actor_id=None,
            target=user.id if user else "unknown",
            result="FAILURE",
            reason="user_not_pending",
        )
        raise InvitationTokenInvalidError()

    # BR-02 Check 3: Token must not be expired
    if invitation.is_expired():
        audit.record(
            action="USER_ACTIVATION_FAILED",
            actor_id=user.id,
            target=user.email,
            result="FAILURE",
            reason="token_expired",
        )
        raise InvitationTokenExpiredError()

    # Claim the invitation first as the concurrency mutex (A8, EC-05)
    rows_claimed = invitation_repo.mark_accepted(db, invitation)
    if rows_claimed == 0:
        audit.record(
            action="USER_ACTIVATION_FAILED",
            actor_id=user.id,
            target=user.email,
            result="FAILURE",
            reason="concurrent_claim",
        )
        raise InvitationTokenInvalidError()

    # Hash password and update user
    password_hash = security.hash_password(password)
    user_repo.activate(db, user, full_name, password_hash)

    audit.record(
        action="USER_ACTIVATED",
        actor_id=user.id,
        target=user.email,
        result="SUCCESS",
    )

    return ActivationResult(
        status="SUCCESS",
        message=ACTIVATION_SUCCESS_MESSAGE,
    )