"""Invitation queries.

Constitution AR-03: queries only, no business rules, no commits.
"""

from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.models.invitation import InvitationModel, InvitationStatus


def add(
    db: Session,
    *,
    email: str,
    token_hash: str,
    expires_at: datetime,
    invited_by_id: str,
) -> InvitationModel:
    """Insert a fresh PENDING invitation.

    Flushed, not committed (AR-06). Only the hash is stored — the raw token
    never reaches this layer (spec BR-07, plan.md A2).
    """
    invitation = InvitationModel(
        email=email,
        token_hash=token_hash,
        expires_at=expires_at,
        status=InvitationStatus.PENDING,
        invited_by_id=invited_by_id,
    )
    db.add(invitation)
    db.flush()
    return invitation


def get_outstanding_for_email(db: Session, email: str) -> list[InvitationModel]:
    """Every still-PENDING invitation for a normalised address.

    Status only — expiry is deliberately not filtered here. An expired
    invitation is still `PENDING` in the database (`EXPIRED` is derived, never
    written — plan.md A5), and EC-03 requires that re-inviting supersedes it
    just the same. Filtering on `expires_at` would leave expired rows behind.
    """
    return list(
        db.scalars(
            select(InvitationModel).where(
                InvitationModel.email == email,
                InvitationModel.status == InvitationStatus.PENDING,
            )
        )
    )


def supersede_outstanding(db: Session, email: str) -> int:
    """Mark every outstanding invitation for this address SUPERSEDED.

    spec FR-11 / BR-03 / EC-02 / EC-03: at most one invitation per address is
    usable at any moment, so issuing a new one invalidates the previous
    immediately. Returns how many rows were superseded.

    plan.md A3: the old row is marked, not mutated in place or deleted —
    preserving invitation history is the reason the entity exists separately
    from the account.
    """
    # `Session.execute` is typed as returning `Result`, which has no `rowcount`;
    # a DML statement always yields a `CursorResult`, which does.
    result = cast(
        "CursorResult[Any]",
        db.execute(
            update(InvitationModel)
            .where(
                InvitationModel.email == email,
                InvitationModel.status == InvitationStatus.PENDING,
            )
            .values(status=InvitationStatus.SUPERSEDED)
        ),
    )
    db.flush()
    return int(result.rowcount or 0)


def get_by_token_hash(db: Session, token_hash: str) -> InvitationModel | None:
    """Look up by hashed token.

    Unused by UM-US-01, which only issues invitations. Consumption is UM-US-02's
    job; this exists because the hash lookup is the reason `token_hash` carries a
    unique index, and the repository is where that query belongs.
    """
    return db.scalars(
        select(InvitationModel).where(InvitationModel.token_hash == token_hash)
    ).one_or_none()
